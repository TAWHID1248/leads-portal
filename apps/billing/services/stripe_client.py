"""Thin wrapper around the Stripe SDK. All side effects funnel through here
so a missing key surfaces one clear error instead of cryptic SDK exceptions.
"""

from decimal import Decimal

import stripe
from django.conf import settings


class StripeNotConfigured(RuntimeError):
    pass


def _client():
    key = getattr(settings, 'STRIPE_SECRET_KEY', '') or ''
    if not key:
        raise StripeNotConfigured('STRIPE_SECRET_KEY is not set.')
    stripe.api_key = key
    return stripe


def create_or_get_customer(client):
    """Return a Stripe Customer for this client, creating one if needed."""
    s = _client()
    if client.stripe_customer_id:
        try:
            return s.Customer.retrieve(client.stripe_customer_id)
        except s.error.StripeError:
            pass

    customer = s.Customer.create(
        email=client.user.email,
        name=client.company_name,
        metadata={'client_id': client.id, 'user_id': client.user_id},
    )
    client.stripe_customer_id = customer['id']
    client.save(update_fields=['stripe_customer_id'])
    return customer


def create_payment_intent(amount, customer_id, metadata=None, currency='usd'):
    """Create a PaymentIntent. `amount` is in dollars (Decimal/float); we
    convert to the Stripe minor-unit integer here."""
    s = _client()
    cents = int(Decimal(str(amount)) * 100)
    return s.PaymentIntent.create(
        amount=cents,
        currency=currency,
        customer=customer_id,
        metadata=metadata or {},
        automatic_payment_methods={'enabled': True},
    )


def create_subscription(customer_id, price_id, metadata=None):
    s = _client()
    return s.Subscription.create(
        customer=customer_id,
        items=[{'price': price_id}],
        payment_behavior='default_incomplete',
        expand=['latest_invoice.payment_intent'],
        metadata=metadata or {},
    )


def cancel_subscription(stripe_sub_id):
    s = _client()
    return s.Subscription.delete(stripe_sub_id)
