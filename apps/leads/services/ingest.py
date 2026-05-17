"""Single entry point for inbound lead data. Handles normalization,
dedupe, DNC stub, quality scoring, persistence, and post-save fan-out."""

import re
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import SystemSetting
from apps.leads.models import Lead
from apps.leads.services import quality_score
from apps.leads.tasks import auto_distribute_lead_task


_PHONE_DIGITS_RE = re.compile(r'\D+')
_DEFAULT_DEDUP_WINDOW_DAYS = 30


def _normalize_phone(raw):
    if not raw:
        return ''
    digits = _PHONE_DIGITS_RE.sub('', str(raw))
    # Strip a leading country code if it leaves a 10-digit US number behind.
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits


def _dedup_window_days():
    try:
        return SystemSetting.objects.get(key='lead_dedup_window_days').get_value()
    except SystemSetting.DoesNotExist:
        return _DEFAULT_DEDUP_WINDOW_DAYS


def _check_dnc(_phone):
    # Real DNC lookup is a later prompt. Always False for now.
    return False


def _find_duplicate(email, phone, niche, window_days):
    if not (email or phone):
        return None
    cutoff = timezone.now() - timedelta(days=window_days)
    q = Q()
    if email:
        q |= Q(email__iexact=email)
    if phone:
        q |= Q(phone=phone)
    return (
        Lead.objects
        .filter(niche=niche, created_at__gte=cutoff)
        .filter(q)
        .order_by('id')
        .first()
    )


def ingest_lead(data: dict) -> Lead:
    """Persist a single inbound lead and trigger downstream distribution."""

    payload = dict(data)
    payload['phone'] = _normalize_phone(payload.get('phone'))
    if payload.get('email'):
        payload['email'] = payload['email'].strip().lower()

    niche = payload.get('niche')
    duplicate_of = _find_duplicate(
        payload.get('email'),
        payload.get('phone'),
        niche,
        _dedup_window_days(),
    )

    if duplicate_of is not None:
        # Persist the duplicate row so audit/replacement workflows can see it,
        # but skip DNC checking, scoring, and distribution.
        dup = Lead.objects.create(
            **payload,
            is_duplicate=True,
            duplicate_of=duplicate_of,
            status=Lead.Status.DUPLICATE,
            dnc_checked_at=timezone.now(),
        )
        return dup

    now = timezone.now()
    is_on_dnc = _check_dnc(payload.get('phone'))
    score = quality_score.calculate(payload)

    lead = Lead.objects.create(
        **payload,
        is_on_dnc=is_on_dnc,
        dnc_checked_at=now,
        quality_score=score,
        status=Lead.Status.AVAILABLE,
    )

    # Bind sweeps-* leads to an active sweepstakes campaign, if one matches.
    _maybe_bind_sweepstakes(lead)

    # Fan out via Celery. In dev CELERY_TASK_ALWAYS_EAGER=True runs the task
    # synchronously in this thread; in prod it queues on Redis.
    try:
        auto_distribute_lead_task.delay(lead.id)
    except Exception:
        # Distribution failures must not undo the ingest — the lead is saved.
        pass

    return lead


def _maybe_bind_sweepstakes(lead):
    if not lead.niche or not lead.niche.startswith('sweeps-'):
        return
    # Local import keeps the lead app independent of the sweepstakes app at
    # import time (apps.sweepstakes can be removed from INSTALLED_APPS).
    from apps.sweepstakes.models import Sweepstakes

    today = timezone.localdate()
    campaign = (
        Sweepstakes.objects
        .filter(
            niche=lead.niche,
            status=Sweepstakes.Status.ACTIVE,
            start_date__lte=today,
            end_date__gte=today,
        )
        .order_by('-id')
        .first()
    )
    if campaign is None:
        return
    if campaign.target_state and lead.state and lead.state.upper() != campaign.target_state.upper():
        return
    lead.sweepstakes = campaign
    lead.save(update_fields=['sweepstakes'])
    Sweepstakes.objects.filter(pk=campaign.id).update(total_entries=F('total_entries') + 1)
