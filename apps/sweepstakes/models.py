from django.db import models
from apps.leads.models import Niche


class Sweepstakes(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
        DRAWN = 'DRAWN', 'Drawn'

    title = models.CharField(max_length=255)
    niche = models.CharField(max_length=20, choices=Niche.choices)
    prize_title = models.CharField(max_length=255)
    prize_value = models.DecimalField(max_digits=10, decimal_places=2)
    prize_image = models.ImageField(upload_to='sweepstakes/', blank=True)
    official_rules_url = models.URLField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    draw_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    total_entries = models.PositiveIntegerField(default=0)
    winner_lead = models.ForeignKey(
        'leads.Lead', null=True, blank=True, on_delete=models.SET_NULL, related_name='won_sweepstakes'
    )
    winner_drawn_at = models.DateTimeField(null=True, blank=True)
    prize_delivered_at = models.DateTimeField(null=True, blank=True)
    target_state = models.CharField(max_length=100, blank=True)
    min_age = models.PositiveIntegerField(default=18)
