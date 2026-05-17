import logging

from celery import shared_task

log = logging.getLogger(__name__)


@shared_task(name='notifications.send_email')
def send_email_task(template_base, subject, recipient, ctx):
    """Generic email sender. `ctx` must be JSON-serialisable."""
    from apps.notifications.services.email import _send
    _send(template_base, subject, recipient, ctx)


@shared_task(name='notifications.notify_client_new_lead')
def notify_client_new_lead_task(allocation_id):
    from apps.leads.models import LeadAllocation
    from apps.leads.services.notifications import notify_client_new_lead
    try:
        allocation = LeadAllocation.objects.get(pk=allocation_id)
    except LeadAllocation.DoesNotExist:
        log.warning('notify_client_new_lead_task: allocation %s missing', allocation_id)
        return
    notify_client_new_lead(allocation)
