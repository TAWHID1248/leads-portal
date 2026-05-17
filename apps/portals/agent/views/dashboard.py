from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.agents.models import CallLog, LeadAssignment
from apps.portals.agent.views._common import (
    month_bounds,
    require_agent,
    today_bounds,
    week_bounds,
)


CALL_OUTCOME_COLORS = {
    'ANSWERED':     '#10B981',
    'SOLD':         '#3B82F6',
    'CALLBACK':     '#8B5CF6',
    'VOICEMAIL':    '#F59E0B',
    'NO_ANSWER':    '#9CA3AF',
    'WRONG_NUMBER': '#EF4444',
}


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def dashboard(request):
    agent = require_agent(request)
    today_start, today_end = today_bounds()
    week_start, week_end = week_bounds()
    month_start, _ = month_bounds()

    assignments = LeadAssignment.objects.filter(agent=agent)
    calls = CallLog.objects.filter(agent=agent)

    kpis = {
        'leads_assigned': assignments.count(),
        'calls_today': calls.filter(called_at__gte=today_start, called_at__lt=today_end).count(),
        'sold_this_week': assignments.filter(
            status='SOLD', assigned_at__gte=week_start, assigned_at__lt=week_end,
        ).count(),
        'commission_month': (
            assignments.filter(
                status='SOLD', assigned_at__gte=month_start,
            ).aggregate(s=Sum('lead__sold_price'))['s'] or Decimal('0.00')
        ) * (agent.commission or Decimal('0.00')),
    }

    target_progress = {
        'leads_done': assignments.filter(assigned_at__gte=week_start).count(),
        'leads_target': agent.target_leads or 0,
        'revenue_done': assignments.filter(
            status='SOLD', assigned_at__gte=week_start,
        ).aggregate(s=Sum('lead__sold_price'))['s'] or Decimal('0.00'),
        'revenue_target': agent.target_revenue or Decimal('0.00'),
        'days_remaining_in_week': max(0, 6 - timezone.now().weekday()),
    }

    # Activity feed: union of recent CallLogs + LeadAssignment changes.
    recent_calls = (
        calls.select_related('lead')
        .order_by('-called_at')[:10]
    )
    recent_assignments = (
        assignments.select_related('lead')
        .order_by('-assigned_at')[:10]
    )
    activity = sorted(
        (
            *[
                {'when': c.called_at, 'kind': 'call', 'verb': 'Logged call',
                 'detail': c.get_outcome_display(), 'lead': c.lead}
                for c in recent_calls
            ],
            *[
                {'when': a.assigned_at, 'kind': 'assigned', 'verb': 'Lead assigned',
                 'detail': a.get_status_display(), 'lead': a.lead}
                for a in recent_assignments
            ],
        ),
        key=lambda x: x['when'],
        reverse=True,
    )[:10]

    return render(request, 'agent/dashboard.html', {
        'page_title': 'Dashboard',
        'agent': agent,
        'kpis': kpis,
        'target_progress': target_progress,
        'activity': activity,
    })


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def chart_data_view(request):
    """Pie chart payload for calls-by-outcome today."""
    agent = require_agent(request)
    today_start, today_end = today_bounds()
    rows = (
        CallLog.objects
        .filter(agent=agent, called_at__gte=today_start, called_at__lt=today_end)
        .values('outcome')
        .annotate(count=Count('id'))
    )
    by_outcome = OrderedDict()
    for r in rows:
        by_outcome[r['outcome']] = r['count']

    # Always return all outcome buckets so the chart legend is stable.
    labels = [code for code, _ in CallLog.Outcome.choices]
    return JsonResponse({
        'labels': [dict(CallLog.Outcome.choices)[code] for code in labels],
        'datasets': [{
            'data': [by_outcome.get(code, 0) for code in labels],
            'backgroundColor': [CALL_OUTCOME_COLORS.get(code, '#CBD5E1') for code in labels],
        }],
    })
