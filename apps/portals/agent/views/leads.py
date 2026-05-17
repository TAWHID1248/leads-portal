from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.agents.models import CallLog, LeadAssignment
from apps.leads.models import Niche
from apps.notifications.models import ActivityLog
from apps.portals.agent.views._common import require_agent


PAGE_SIZE = 50


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _agent_assignments(agent):
    return LeadAssignment.objects.filter(agent=agent).select_related('lead')


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def LeadListView(request):
    agent = require_agent(request)
    qs = _agent_assignments(agent).order_by('-assigned_at')

    search = (request.GET.get('search') or '').strip()
    status = request.GET.get('status') or ''
    niche = request.GET.get('niche') or ''

    if search:
        qs = qs.filter(
            Q(lead__first_name__icontains=search)
            | Q(lead__last_name__icontains=search)
            | Q(lead__email__icontains=search)
            | Q(lead__phone__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if niche:
        qs = qs.filter(lead__niche=niche)

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
    ctx = {
        'page_title': 'My leads',
        'page_obj': page,
        'total_count': qs.count(),
        'niches': Niche.choices,
        'assignment_statuses': LeadAssignment.Status.choices,
        'call_outcomes': CallLog.Outcome.choices,
    }
    if _is_htmx(request):
        return render(request, 'agent/leads/_table.html', ctx)
    return render(request, 'agent/leads/list.html', ctx)


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def lead_drawer_view(request, pk):
    agent = require_agent(request)
    assignment = get_object_or_404(_agent_assignments(agent), pk=pk)
    calls = (
        CallLog.objects
        .filter(agent=agent, lead=assignment.lead)
        .order_by('-called_at')
    )
    return render(request, 'agent/leads/_drawer.html', {
        'a': assignment,
        'lead': assignment.lead,
        'calls': calls,
    })


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
@require_POST
def log_call_view(request, pk):
    agent = require_agent(request)
    assignment = get_object_or_404(_agent_assignments(agent), pk=pk)

    outcome = request.POST.get('outcome')
    if outcome not in dict(CallLog.Outcome.choices):
        return HttpResponseBadRequest('Invalid outcome')
    try:
        duration = int(request.POST.get('duration_seconds') or 0)
    except ValueError:
        duration = 0
    notes = (request.POST.get('notes') or '').strip()

    next_follow_up = request.POST.get('next_follow_up') or None

    CallLog.objects.create(
        lead=assignment.lead,
        agent=agent,
        outcome=outcome,
        duration_seconds=max(0, duration),
        notes=notes,
        next_follow_up=next_follow_up,
    )

    # Optional: bump the assignment status on certain outcomes.
    new_status = request.POST.get('assignment_status')
    if new_status and new_status in dict(LeadAssignment.Status.choices):
        assignment.status = new_status
        if notes:
            assignment.notes = (assignment.notes + '\n' + notes).strip() if assignment.notes else notes
        assignment.save(update_fields=['status', 'notes'])

    ActivityLog.objects.create(
        user=request.user, action='agent.call_logged',
        entity_type='LeadAssignment', entity_id=str(assignment.id),
        metadata={'outcome': outcome, 'duration_seconds': duration},
    )

    # Re-render this row with updated state (e.g. next-follow-up indicator)
    return render(request, 'agent/leads/_row.html', {
        'a': assignment,
        'call_outcomes': CallLog.Outcome.choices,
        'assignment_statuses': LeadAssignment.Status.choices,
    })
