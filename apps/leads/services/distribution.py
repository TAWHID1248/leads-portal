"""Match a newly-saved lead against active client subscriptions and create
LeadAllocation rows. Exclusive subscriptions stop further fan-out for that lead.
Celery wiring lands in a later prompt — for now this is just a callable.
"""

from django.db import transaction
from django.utils import timezone

from apps.clients.models import Subscription
from apps.leads.models import Lead, LeadAllocation


def auto_distribute_lead(lead_id):
    try:
        lead = Lead.objects.get(pk=lead_id)
    except Lead.DoesNotExist:
        return []

    if lead.status not in (Lead.Status.AVAILABLE, Lead.Status.NEW):
        return []

    now = timezone.now()
    subs = (
        Subscription.objects
        .select_related('client')
        .filter(
            niche=lead.niche,
            status=Subscription.Status.ACTIVE,
            current_period_end__gt=now,
        )
        .order_by('id')
    )

    created = []
    with transaction.atomic():
        for sub in subs:
            allocation, was_created = LeadAllocation.objects.get_or_create(
                lead=lead,
                client=sub.client,
                defaults={
                    'price_per_lead': sub.price_per_lead,
                    'status': LeadAllocation.Status.ACTIVE,
                    'client_status': LeadAllocation.ClientStatus.NEW,
                },
            )
            if was_created:
                created.append(allocation)
            if sub.is_exclusive:
                break

        if created:
            lead.status = Lead.Status.ALLOCATED
            lead.save(update_fields=['status', 'updated_at'])

    for allocation in created:
        try:
            from apps.notifications.tasks import notify_client_new_lead_task
            notify_client_new_lead_task.delay(allocation.id)
        except Exception:
            # Notification failures must not abort distribution
            pass

    return created
