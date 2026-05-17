"""Order lifecycle: create, allocate leads, invoice. Stripe path leaves the
order PENDING until the webhook calls confirm_paid_order."""

import secrets
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import Invoice, Order
from apps.billing.services import stripe_client, wallet
from apps.clients.models import WalletTransaction
from apps.leads.models import Lead, LeadAllocation


def _next_invoice_number(order):
    return f"INV-{order.id:06d}-{uuid.uuid4().hex[:6].upper()}"


def _allocate_leads(order):
    """Grab N AVAILABLE leads in this niche and create LeadAllocations.
    Returns the list of leads we managed to claim."""
    qs = (
        Lead.objects
        .filter(niche=order.niche, status=Lead.Status.AVAILABLE)
        .order_by('-quality_score', 'created_at')[:order.quantity]
    )
    leads = list(qs)
    allocations = []
    for lead in leads:
        alloc, created = LeadAllocation.objects.get_or_create(
            lead=lead,
            client=order.client,
            defaults={
                'order': order,
                'price_per_lead': order.price_per_lead,
                'status': LeadAllocation.Status.ACTIVE,
                'client_status': LeadAllocation.ClientStatus.NEW,
            },
        )
        if created:
            allocations.append(alloc)
            lead.status = Lead.Status.ALLOCATED
            lead.save(update_fields=['status', 'updated_at'])
    return allocations


def _create_invoice(order):
    return Invoice.objects.create(
        client=order.client,
        order=order,
        invoice_number=_next_invoice_number(order),
        amount=order.total_amount,
        currency=order.currency,
        status=(
            Invoice.Status.PAID if order.status == Order.Status.PAID
            else Invoice.Status.UNPAID
        ),
        issued_at=timezone.now(),
        paid_at=order.paid_at,
    )


@transaction.atomic
def create_order(client, niche, quantity, price_per_lead, exclusive=False,
                 payment_method='wallet'):
    quantity = int(quantity)
    price_per_lead = Decimal(str(price_per_lead))
    total = (price_per_lead * quantity).quantize(Decimal('0.01'))

    order = Order.objects.create(
        client=client,
        order_type=Order.OrderType.ONE_TIME,
        niche=niche,
        quantity=quantity,
        price_per_lead=price_per_lead,
        total_amount=total,
        status=Order.Status.PENDING,
    )

    if payment_method == 'wallet':
        # Charge the wallet up-front; if balance insufficient this raises and
        # the atomic block rolls back the Order row.
        wallet.debit_wallet(
            client,
            total,
            WalletTransaction.TxType.LEAD_PURCHASE,
            description=f'Order #{order.id} — {quantity} × {niche}',
            reference=f'order:{order.id}',
        )
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=['status', 'paid_at'])
        allocations = _allocate_leads(order)
        _create_invoice(order)
        return order, allocations, None

    if payment_method == 'stripe':
        # Create the PaymentIntent and return the client_secret so the
        # frontend can confirm. The order is allocated by the webhook.
        customer = stripe_client.create_or_get_customer(client)
        intent = stripe_client.create_payment_intent(
            total,
            customer_id=customer['id'],
            metadata={'order_id': order.id, 'kind': 'order'},
        )
        order.stripe_payment_intent_id = intent['id']
        order.save(update_fields=['stripe_payment_intent_id'])
        return order, [], intent['client_secret']

    raise ValueError(f'Unknown payment_method: {payment_method!r}')


@transaction.atomic
def confirm_paid_order(order_id):
    """Called by the Stripe webhook when a PaymentIntent succeeds."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.PAID:
        return order, []
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    allocations = _allocate_leads(order)
    # If an Invoice already exists (shouldn't, but be defensive), update it.
    inv = Invoice.objects.filter(order=order).first()
    if inv is None:
        _create_invoice(order)
    else:
        inv.status = Invoice.Status.PAID
        inv.paid_at = order.paid_at
        inv.save(update_fields=['status', 'paid_at'])
    return order, allocations
