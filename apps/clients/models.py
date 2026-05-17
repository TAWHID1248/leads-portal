import secrets
from django.db import models
from apps.leads.models import Niche


def _generate_api_key():
    return 'clx_' + secrets.token_urlsafe(32)


class Client(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=2, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    billing_address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    stripe_customer_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    webhook_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=64, unique=True, default=_generate_api_key)
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)


class Wallet(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default='0.00')
    currency = models.CharField(max_length=3, default='USD')


class WalletTransaction(models.Model):
    class TxType(models.TextChoices):
        TOP_UP = 'TOP_UP', 'Top Up'
        LEAD_PURCHASE = 'LEAD_PURCHASE', 'Lead Purchase'
        REFUND = 'REFUND', 'Refund'
        CREDIT_ADJUSTMENT = 'CREDIT_ADJUSTMENT', 'Credit Adjustment'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tx_type = models.CharField(max_length=20, choices=TxType.choices)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    class BillingPeriod(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PAUSED = 'PAUSED', 'Paused'
        CANCELLED = 'CANCELLED', 'Cancelled'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    niche = models.CharField(max_length=20, choices=Niche.choices)
    leads_per_period = models.PositiveIntegerField()
    price_per_lead = models.DecimalField(max_digits=8, decimal_places=2)
    billing_period = models.CharField(max_length=10, choices=BillingPeriod.choices)
    is_exclusive = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
