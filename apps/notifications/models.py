from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LEAD = 'LEAD', 'Lead'
        REPLACEMENT = 'REPLACEMENT', 'Replacement'
        INVOICE = 'INVOICE', 'Invoice'
        SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
        SYSTEM = 'SYSTEM', 'System'

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]


class ActivityLog(models.Model):
    user = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='activity_logs'
    )
    action = models.CharField(max_length=255, db_index=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
