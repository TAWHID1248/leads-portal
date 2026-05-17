import logging

from celery import shared_task

log = logging.getLogger(__name__)


@shared_task(name='leads.auto_distribute_lead')
def auto_distribute_lead_task(lead_id):
    from apps.leads.services.distribution import auto_distribute_lead
    msg = f'[celery] leads.auto_distribute_lead lead_id={lead_id}'
    log.info(msg); print(msg, flush=True)
    allocations = auto_distribute_lead(lead_id)
    summary = f'[celery] lead_id={lead_id} -> {len(allocations)} allocations'
    log.info(summary); print(summary, flush=True)
    return [a.id for a in allocations]


@shared_task(name='leads.generate_csv_export')
def generate_csv_export_task(lead_ids):
    """Materialise a CSV in memory. Returning bytes makes this directly
    usable inside the same process when CELERY_TASK_ALWAYS_EAGER=True;
    for prod we'd write to S3 and return the key."""
    from apps.leads.models import Lead
    from apps.leads.services.export import export_leads_to_csv
    qs = Lead.objects.filter(id__in=lead_ids).order_by('-created_at')
    return export_leads_to_csv(qs)
