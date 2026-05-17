from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.agents.models import CallLog, LeadAssignment
from apps.portals.agent.views._common import month_bounds, require_agent, week_bounds


def _gauge_arc(percent):
    """Return SVG path data for a half-circle gauge filled to `percent` (0-1).
    The arc spans from (10, 100) sweeping clockwise to (190, 100) on a 200x100
    viewbox; we cut the stroke-dasharray to the right percent."""
    p = max(0.0, min(1.0, percent))
    # Half-circle arc length on a 90-radius arc = pi * 90 ≈ 282.74
    total = 282.74
    return {
        'dash': round(total * p, 2),
        'gap': round(total * (1 - p), 2),
        'percent_label': f'{int(p * 100)}%',
    }


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def targets_view(request):
    agent = require_agent(request)
    now = timezone.now()
    week_start, week_end = week_bounds(now)
    month_start, _ = month_bounds(now)

    assignments_week = LeadAssignment.objects.filter(
        agent=agent, assigned_at__gte=week_start, assigned_at__lt=week_end,
    )

    leads_done = assignments_week.count()
    leads_target = agent.target_leads or 0
    leads_pct = (leads_done / leads_target) if leads_target else 0.0

    revenue_done = (
        assignments_week.filter(status='SOLD')
        .aggregate(s=Sum('lead__sold_price'))['s']
        or Decimal('0.00')
    )
    revenue_target = agent.target_revenue or Decimal('0.00')
    revenue_pct = float(revenue_done / revenue_target) if revenue_target else 0.0

    # Day-by-day breakdown for the current week.
    days = []
    for offset in range(7):
        day_start = week_start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        outcome_rows = (
            CallLog.objects
            .filter(agent=agent, called_at__gte=day_start, called_at__lt=day_end)
            .values('outcome')
            .annotate(count=Count('id'))
        )
        outcomes = OrderedDict()
        for o in outcome_rows:
            outcomes[o['outcome']] = o['count']
        days.append({
            'date': day_start.date(),
            'total': sum(outcomes.values()),
            'outcomes': outcomes,
        })

    # Monthly summary.
    monthly_assignments = LeadAssignment.objects.filter(
        agent=agent, assigned_at__gte=month_start,
    )
    monthly_calls = CallLog.objects.filter(agent=agent, called_at__gte=month_start)
    monthly_outcomes = (
        monthly_calls.values('outcome').annotate(count=Count('id')).order_by('outcome')
    )
    monthly_sold = monthly_assignments.filter(status='SOLD')
    monthly_revenue = monthly_sold.aggregate(s=Sum('lead__sold_price'))['s'] or Decimal('0.00')
    monthly_commission = monthly_revenue * (agent.commission or Decimal('0.00'))

    return render(request, 'agent/targets.html', {
        'page_title': 'Targets',
        'agent': agent,
        'leads_gauge': _gauge_arc(leads_pct),
        'leads_done': leads_done,
        'leads_target': leads_target,
        'revenue_gauge': _gauge_arc(revenue_pct),
        'revenue_done': revenue_done,
        'revenue_target': revenue_target,
        'days': days,
        'outcomes_in_order': [code for code, _ in CallLog.Outcome.choices],
        'outcome_labels': dict(CallLog.Outcome.choices),
        'monthly_calls_total': monthly_calls.count(),
        'monthly_outcomes': list(monthly_outcomes),
        'monthly_sold_count': monthly_sold.count(),
        'monthly_revenue': monthly_revenue,
        'monthly_commission': monthly_commission,
    })
