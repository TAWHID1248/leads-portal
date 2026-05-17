from django.db import models
from apps.core.models import TimeStampedModel


class Niche(models.TextChoices):
    SOLAR_USA = 'solar-usa', 'Solar USA'
    SOLAR_UK = 'solar-uk', 'Solar UK'
    SOLAR_CA = 'solar-ca', 'Solar Canada'
    SOLAR_AU = 'solar-au', 'Solar Australia'
    SWEEPS_AUTO = 'sweeps-auto', 'Sweepstakes Auto'
    SWEEPS_HEALTH = 'sweeps-health', 'Sweepstakes Health'
    SWEEPS_MEDICARE = 'sweeps-medicare', 'Sweepstakes Medicare'
    SWEEPS_HOME = 'sweeps-home', 'Sweepstakes Home'
    SWEEPS_LIFE = 'sweeps-life', 'Sweepstakes Life'
    SWEEPS_DEBT = 'sweeps-debt', 'Sweepstakes Debt'
    SWEEPS_GENERIC = 'sweeps-generic', 'Sweepstakes Generic'


class Lead(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = 'NEW', 'New'
        AVAILABLE = 'AVAILABLE', 'Available'
        ALLOCATED = 'ALLOCATED', 'Allocated'
        SOLD = 'SOLD', 'Sold'
        REPLACED = 'REPLACED', 'Replaced'
        DUPLICATE = 'DUPLICATE', 'Duplicate'
        REJECTED = 'REJECTED', 'Rejected'

    # Source tracking
    source_type = models.CharField(max_length=50, blank=True)
    niche = models.CharField(max_length=20, choices=Niche.choices)
    campaign_id = models.CharField(max_length=255, blank=True)
    ad_set_id = models.CharField(max_length=255, blank=True)
    source_page = models.URLField(blank=True)
    utm_source = models.CharField(max_length=255, blank=True)
    utm_medium = models.CharField(max_length=255, blank=True)
    utm_campaign = models.CharField(max_length=255, blank=True)
    utm_content = models.CharField(max_length=255, blank=True)
    utm_term = models.CharField(max_length=255, blank=True)

    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default='US')
    date_of_birth = models.DateField(null=True, blank=True)

    # Solar-specific fields
    is_homeowner = models.BooleanField(null=True, blank=True)
    monthly_bill = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    credit_score = models.CharField(max_length=20, blank=True)
    roof_type = models.CharField(max_length=50, blank=True)
    roof_age = models.PositiveIntegerField(null=True, blank=True)
    solar_timeline = models.CharField(max_length=50, blank=True)

    # Sweepstakes-specific fields
    annual_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currently_insured = models.BooleanField(null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, blank=True)
    vehicle_year = models.PositiveIntegerField(null=True, blank=True)
    total_debt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Quality
    quality_score = models.PositiveIntegerField(default=5)
    notes = models.TextField(blank=True)

    # Compliance / TCPA
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    trusted_form_cert_url = models.URLField(blank=True)
    tcpa_consent_text = models.TextField(blank=True)
    tcpa_consent_at = models.DateTimeField(null=True, blank=True)

    # Duplicate / DNC
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='duplicates'
    )
    is_on_dnc = models.BooleanField(default=False)
    dnc_checked_at = models.DateTimeField(null=True, blank=True)

    # Status / Sale
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    sold_at = models.DateTimeField(null=True, blank=True)
    sold_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Relations
    sweepstakes = models.ForeignKey(
        'sweepstakes.Sweepstakes', null=True, blank=True, on_delete=models.SET_NULL, related_name='leads'
    )

    class Meta:
        indexes = [
            models.Index(fields=['niche', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email', 'niche']),
            models.Index(fields=['phone', 'niche']),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def quality_band(self):
        if self.quality_score >= 8:
            return 'high'
        elif self.quality_score >= 5:
            return 'medium'
        return 'low'


class LeadAllocation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        REPLACED = 'REPLACED', 'Replaced'
        REFUNDED = 'REFUNDED', 'Refunded'

    class ClientStatus(models.TextChoices):
        NEW = 'NEW', 'New'
        CONTACTED = 'CONTACTED', 'Contacted'
        CONVERTED = 'CONVERTED', 'Converted'
        BAD = 'BAD', 'Bad'

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='allocations')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='allocations')
    order = models.ForeignKey(
        'billing.Order', null=True, blank=True, on_delete=models.SET_NULL, related_name='allocations'
    )
    price_per_lead = models.DecimalField(max_digits=8, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    client_status = models.CharField(max_length=20, choices=ClientStatus.choices, default=ClientStatus.NEW)

    class Meta:
        unique_together = ('lead', 'client')


class ReplacementRequest(models.Model):
    class Reason(models.TextChoices):
        WRONG_NUMBER = 'WRONG_NUMBER', 'Wrong Number'
        DUPLICATE = 'DUPLICATE', 'Duplicate'
        UNREACHABLE = 'UNREACHABLE', 'Unreachable'
        UNDER_AGE = 'UNDER_AGE', 'Under Age'
        OUT_OF_AREA = 'OUT_OF_AREA', 'Out of Area'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        DENIED = 'DENIED', 'Denied'

    allocation = models.OneToOneField(
        LeadAllocation, on_delete=models.CASCADE, related_name='replacement_request'
    )
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='replacement_requests')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='replacement_requests')
    reason = models.CharField(max_length=20, choices=Reason.choices)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_replacements'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    replacement_lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name='replacement_for'
    )
