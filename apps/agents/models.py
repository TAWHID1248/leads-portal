from django.db import models


class Agent(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='agent_profile')
    target_leads = models.PositiveIntegerField(default=20)
    target_revenue = models.DecimalField(max_digits=10, decimal_places=2, default='1000.00')
    commission = models.DecimalField(max_digits=5, decimal_places=3, default='0.100')


class LeadAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        SOLD = 'SOLD', 'Sold'
        LOST = 'LOST', 'Lost'
        FOLLOW_UP = 'FOLLOW_UP', 'Follow Up'

    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='assignments')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    notes = models.TextField(blank=True)


class CallLog(models.Model):
    class Outcome(models.TextChoices):
        ANSWERED = 'ANSWERED', 'Answered'
        NO_ANSWER = 'NO_ANSWER', 'No Answer'
        VOICEMAIL = 'VOICEMAIL', 'Voicemail'
        WRONG_NUMBER = 'WRONG_NUMBER', 'Wrong Number'
        CALLBACK = 'CALLBACK', 'Callback'
        SOLD = 'SOLD', 'Sold'

    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, related_name='call_logs')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='call_logs')
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    duration_seconds = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    next_follow_up = models.DateTimeField(null=True, blank=True)
    called_at = models.DateTimeField(auto_now_add=True)
