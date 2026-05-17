"""Stripe webhook handler.

Configure in Stripe dashboard:
    URL:    https://<host>/webhooks/stripe/
    Events: payment_intent.succeeded, customer.subscription.created,
            customer.subscription.updated, customer.subscription.deleted,
            invoice.paid
Copy the signing secret to STRIPE_WEBHOOK_SECRET.

Idempotency: every received event ID is recorded in StripeEvent; we no-op
when we see a duplicate so retries are safe.
"""

import json
import logging
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing.models import Invoice, Order, StripeEvent
from apps.billing.services import orders as orders_service
from apps.billing.services.wallet import credit_wallet
from apps.clients.models import Client, Subscription, WalletTransaction
from apps.leads.models import Niche
from apps.notifications.models import ActivityLog

log = logging.getLogger(__name__)


def _verify_event(payload, sig_header):
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '') or ''
    if not secret:
        # Tolerate missing secret in dev — caller still gets a parsed event,
        # but flag it so the response can mention.
        return json.loads(payload), True
    event = stripe.Webhook.construct_event(payload, sig_header, secret)
    return event, False


def _mark_processed(event_id, event_type, payload):
    try:
        StripeEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
        return True
    except IntegrityError:
        return False  # already processed


def _from_unix(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=dt_tz.utc)


def _handle_payment_intent_succeeded(intent):
    metadata = intent.get('metadata') or {}
    kind = metadata.get('kind')

    if kind == 'order':
        order_id = int(metadata['order_id'])
        order, allocations = orders_service.confirm_paid_order(order_id)
        ActivityLog.objects.create(
            action='order.paid_via_stripe',
            entity_type='Order', entity_id=str(order.id),
            metadata={'pi': intent['id'], 'allocations': len(allocations)},
        )
        return

    if kind == 'topup':
        client_id = int(metadata['client_id'])
        client = Client.objects.get(pk=client_id)
        amount = Decimal(intent['amount']) / Decimal('100')
        credit_wallet(
            client, amount,
            WalletTransaction.TxType.TOP_UP,
            description=f'Top-up via Stripe ({intent["id"]})',
            reference=intent['id'],
        )
        ActivityLog.objects.create(
            action='wallet.topup_via_stripe',
            entity_type='Client', entity_id=str(client.id),
            metadata={'pi': intent['id'], 'amount': str(amount)},
        )
        return

    log.info('Unhandled payment_intent.succeeded metadata: %s', metadata)


def _handle_subscription_event(sub_obj, deleted=False):
    sub_id = sub_obj['id']
    customer_id = sub_obj.get('customer')
    client = Client.objects.filter(stripe_customer_id=customer_id).first()
    if not client:
        log.warning('Stripe customer %s has no matching Client', customer_id)
        return

    # Extract first line item for niche/price
    items = (sub_obj.get('items') or {}).get('data') or []
    metadata = sub_obj.get('metadata') or {}
    niche = metadata.get('niche')
    if niche not in dict(Niche.choices):
        return  # niche metadata required

    price = items[0]['price']['unit_amount'] / 100 if items else None

    if deleted:
        Subscription.objects.filter(stripe_subscription_id=sub_id).update(
            status=Subscription.Status.CANCELLED,
            cancelled_at=timezone.now(),
        )
        return

    Subscription.objects.update_or_create(
        stripe_subscription_id=sub_id,
        defaults={
            'client': client,
            'niche': niche,
            'leads_per_period': int(metadata.get('leads_per_period') or 0),
            'price_per_lead': Decimal(metadata.get('price_per_lead') or price or 0),
            'billing_period': metadata.get('billing_period') or 'MONTHLY',
            'is_exclusive': metadata.get('is_exclusive', '').lower() == 'true',
            'status': (
                Subscription.Status.ACTIVE if sub_obj.get('status') == 'active'
                else Subscription.Status.PAUSED
            ),
            'current_period_start': _from_unix(sub_obj.get('current_period_start')),
            'current_period_end': _from_unix(sub_obj.get('current_period_end')),
        },
    )


def _handle_invoice_paid(inv_obj):
    pi = inv_obj.get('payment_intent') or ''
    if not pi:
        return
    # Match by stripe_payment_intent_id; mark the local invoice paid.
    order = Order.objects.filter(stripe_payment_intent_id=pi).first()
    if not order:
        return
    Invoice.objects.filter(order=order).update(
        status=Invoice.Status.PAID,
        paid_at=timezone.now(),
    )


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event, signature_skipped = _verify_event(payload, sig_header)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        return HttpResponse(f'Bad signature: {exc}', status=400)

    event_id = event['id']
    event_type = event['type']

    # Stripe SDK returns an Event object; store the raw parsed body so the
    # StripeEvent payload column stays JSON-serialisable.
    try:
        event_payload = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        event_payload = {}
    inserted = _mark_processed(event_id, event_type, event_payload)
    if not inserted:
        return JsonResponse({'ok': True, 'idempotent': True, 'event_id': event_id})

    # Use the plain JSON copy for handler logic — stripe.StripeObject shadows
    # `.get` etc. as dict-key lookups, which breaks idiomatic dict access.
    obj = (event_payload.get('data') or {}).get('object') or {}
    try:
        if event_type == 'payment_intent.succeeded':
            _handle_payment_intent_succeeded(obj)
        elif event_type in ('customer.subscription.created', 'customer.subscription.updated'):
            _handle_subscription_event(obj, deleted=False)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_event(obj, deleted=True)
        elif event_type == 'invoice.paid':
            _handle_invoice_paid(obj)
        else:
            log.info('Unhandled Stripe event type: %s', event_type)
    except Exception as exc:
        log.exception('Stripe webhook handler failed for %s', event_id)
        # Delete the StripeEvent row so a retry can re-attempt.
        StripeEvent.objects.filter(event_id=event_id).delete()
        return HttpResponse(f'handler error: {exc}', status=500)

    return JsonResponse({'ok': True, 'event_id': event_id, 'signature_skipped': signature_skipped})
