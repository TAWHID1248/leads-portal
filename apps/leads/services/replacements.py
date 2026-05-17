"""Approve / deny ReplacementRequest. Shared between super_admin and
admin_portal so both portals route through the same business logic."""

from django.db import transaction
from django.utils import timezone

from apps.leads.models import Lead, LeadAllocation, ReplacementRequest
from apps.notifications.models import Notification
from apps.notifications.services import email as email_service


def _find_replacement_lead(original_lead):
    """Return the next AVAILABLE lead in the same niche, picking the highest
    quality first. Returns None if nothing matches."""
    return (
        Lead.objects
        .filter(niche=original_lead.niche, status=Lead.Status.AVAILABLE)
        .exclude(id=original_lead.id)
        .order_by('-quality_score', 'created_at')
        .first()
    )


class NoReplacementAvailable(Exception):
    pass


@transaction.atomic
def approve_replacement(replacement_request, reviewed_by):
    rr = (
        ReplacementRequest.objects
        .select_for_update()
        .select_related('allocation', 'lead', 'client', 'client__user')
        .get(pk=replacement_request.pk)
    )
    if rr.status != ReplacementRequest.Status.PENDING:
        return rr  # idempotent

    new_lead = _find_replacement_lead(rr.lead)
    if new_lead is None:
        raise NoReplacementAvailable(
            f'No AVAILABLE leads remaining in {rr.lead.niche}.'
        )

    # Mark the original allocation REPLACED and the original lead REPLACED.
    rr.allocation.status = LeadAllocation.Status.REPLACED
    rr.allocation.save(update_fields=['status'])

    rr.lead.status = Lead.Status.REPLACED
    rr.lead.save(update_fields=['status', 'updated_at'])

    # Create a fresh allocation for the replacement lead at the same price.
    new_alloc = LeadAllocation.objects.create(
        lead=new_lead,
        client=rr.client,
        price_per_lead=rr.allocation.price_per_lead,
        status=LeadAllocation.Status.ACTIVE,
        client_status=LeadAllocation.ClientStatus.NEW,
    )
    new_lead.status = Lead.Status.ALLOCATED
    new_lead.save(update_fields=['status', 'updated_at'])

    rr.status = ReplacementRequest.Status.APPROVED
    rr.reviewed_by = reviewed_by
    rr.reviewed_at = timezone.now()
    rr.replacement_lead = new_lead
    rr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'replacement_lead'])

    Notification.objects.create(
        user=rr.client.user,
        notification_type=Notification.NotificationType.REPLACEMENT,
        title='Replacement approved',
        message=f'Your replacement request for lead #{rr.lead_id} was approved.',
        link='/client/replacements/',
    )
    try:
        email_service.send_replacement_approved_email(rr)
    except Exception:
        pass

    return rr


@transaction.atomic
def deny_replacement(replacement_request, reviewed_by, reason_note=''):
    rr = (
        ReplacementRequest.objects
        .select_for_update()
        .select_related('client', 'client__user', 'lead')
        .get(pk=replacement_request.pk)
    )
    if rr.status != ReplacementRequest.Status.PENDING:
        return rr

    rr.status = ReplacementRequest.Status.DENIED
    rr.reviewed_by = reviewed_by
    rr.reviewed_at = timezone.now()
    if reason_note:
        rr.notes = (rr.notes + f'\n[Denied: {reason_note}]').strip() if rr.notes else f'Denied: {reason_note}'
    rr.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'notes'])

    Notification.objects.create(
        user=rr.client.user,
        notification_type=Notification.NotificationType.REPLACEMENT,
        title='Replacement denied',
        message=f'Your replacement request for lead #{rr.lead_id} was denied.',
        link='/client/replacements/',
    )
    try:
        email_service.send_replacement_denied_email(rr, reason_note=reason_note)
    except Exception:
        pass

    return rr
