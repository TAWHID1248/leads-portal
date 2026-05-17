from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import super_admin_required
from apps.accounts.models import User
from apps.agents.models import Agent
from apps.billing.models import Order
from apps.clients.models import Client
from apps.leads.models import Lead, Niche, ReplacementRequest
from apps.notifications.models import ActivityLog, Notification


# Same niche colour map the client dashboard uses, so the charts feel familiar.
NICHE_COLORS = {
    'solar-usa': '#F59E0B', 'solar-uk': '#FBBF24', 'solar-ca': '#FCD34D', 'solar-au': '#FDE68A',
    'sweeps-auto': '#3B82F6', 'sweeps-health': '#10B981', 'sweeps-medicare': '#06B6D4',
    'sweeps-home': '#6366F1', 'sweeps-life': '#EC4899', 'sweeps-debt': '#EF4444',
    'sweeps-generic': '#9CA3AF',
}


@super_admin_required
def dashboard(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    kpis = {
        'leads_today': Lead.objects.filter(created_at__gte=today_start).count(),
        'leads_week': Lead.objects.filter(created_at__gte=week_start).count(),
        'active_clients': Client.objects.filter(user__status=User.Status.ACTIVE).count(),
        'active_agents': Agent.objects.filter(user__status=User.Status.ACTIVE).count(),
        'revenue_month': (
            Order.objects.filter(status='PAID', paid_at__gte=month_start)
            .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        ),
        'pending_replacements': ReplacementRequest.objects.filter(status='PENDING').count(),
        'unread_notifications': (
            Notification.objects.filter(user=request.user, is_read=False).count()
        ),
    }

    recent_leads = (
        Lead.objects.order_by('-created_at')[:10]
    )
    pending_replacements = (
        ReplacementRequest.objects
        .filter(status='PENDING')
        .select_related('lead', 'client', 'client__user')
        .order_by('-id')[:10]
    )
    top_clients_month = (
        Order.objects.filter(status='PAID', paid_at__gte=month_start)
        .values('client_id', 'client__company_name')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('-revenue')[:5]
    )
    recent_ingests = (
        ActivityLog.objects
        .filter(action='lead.ingested')
        .order_by('-created_at')[:10]
    )

    return render(request, 'super_admin/dashboard.html', {
        'page_title': 'Dashboard',
        'portal_name': 'Super Admin',
        'kpis': kpis,
        'recent_leads': recent_leads,
        'pending_replacements': pending_replacements,
        'top_clients_month': top_clients_month,
        'recent_ingests': recent_ingests,
    })


@super_admin_required
def dashboard_chart_data(request):
    """JSON for both dashboard charts: leads-by-day (stacked by niche) and
    revenue-by-day, each covering the last 30 days."""
    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    day_iso = [d.isoformat() for d in days]
    niche_labels = dict(Niche.choices)

    # Leads grouped by niche × day.
    lead_rows = (
        Lead.objects
        .filter(created_at__date__gte=days[0])
        .values('niche', 'created_at__date')
        .annotate(count=Count('id'))
    )
    by_niche = defaultdict(lambda: {d.isoformat(): 0 for d in days})
    niches_seen = set()
    for r in lead_rows:
        n = r['niche']
        niches_seen.add(n)
        d = r['created_at__date'].isoformat()
        if d in by_niche[n]:
            by_niche[n][d] = r['count']

    lead_datasets = []
    for n in sorted(niches_seen):
        lead_datasets.append({
            'label': niche_labels.get(n, n),
            'data': [by_niche[n][d] for d in day_iso],
            'backgroundColor': NICHE_COLORS.get(n, '#9CA3AF'),
        })

    # Revenue per day from PAID orders.
    rev_rows = (
        Order.objects.filter(status='PAID', paid_at__date__gte=days[0])
        .values('paid_at__date')
        .annotate(total=Sum('total_amount'))
    )
    rev_by_day = {r['paid_at__date']: float(r['total'] or 0) for r in rev_rows}

    return JsonResponse({
        'labels': day_iso,
        'leads_datasets': lead_datasets,
        'revenue': [rev_by_day.get(d, 0) for d in days],
    })
