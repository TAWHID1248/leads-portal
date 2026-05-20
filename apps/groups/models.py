from django.conf import settings
from django.db import models


class FacebookGroup(models.Model):
    class GroupType(models.TextChoices):
        DATA_LEADS     = 'data_leads',     'Data and leads'
        CPA_AFFILIATE  = 'cpa_affiliate',  'CPA/Affiliate Database'
        HOMEOWNER_DB   = 'homeowner_db',   'Homeowner database'
        TELEMARKETING  = 'telemarketing',  'Telemarketing or Number leads'
        EMAIL_TECH     = 'email_tech',     'Email or Tech support'
        OTHER_BUSINESS = 'other_business', 'Other business group'
        REVIEW         = 'review',         'Review Group'

    class Quality(models.TextChoices):
        VERY_GOOD     = 'very_good',     'Very good'
        GOOD          = 'good',          'Good'
        AVERAGE       = 'average',       'Average'
        BELOW_AVERAGE = 'below_average', 'Below Average'
        BAD           = 'bad',           'Bad'
        WORST         = 'worst',         'Worst'

    name        = models.CharField(max_length=512)
    group_url   = models.URLField(blank=True, max_length=1000)
    group_type  = models.CharField(max_length=30, choices=GroupType.choices, default=GroupType.DATA_LEADS)
    members     = models.PositiveIntegerField(default=0)
    quality     = models.CharField(max_length=20, choices=Quality.choices, default=Quality.AVERAGE)
    is_active   = models.BooleanField(default=True)
    owner_name  = models.CharField(max_length=255, blank=True)
    owner_url   = models.URLField(blank=True, max_length=1000)
    admin_1     = models.CharField(max_length=255, blank=True)
    admin_2     = models.CharField(max_length=255, blank=True)
    admin_3     = models.CharField(max_length=255, blank=True)
    agent_name  = models.CharField(max_length=255, blank=True)
    backup_url  = models.URLField(blank=True, max_length=1000)
    added_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_fb_groups')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-members']
        verbose_name = 'Facebook Group'
        verbose_name_plural = 'Facebook Groups'

    def __str__(self):
        return self.name
