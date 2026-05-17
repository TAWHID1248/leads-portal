from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.billing.models import Order
from apps.clients.models import Client
from apps.leads.models import Lead, ReplacementRequest


@role_required('SUPER_ADMIN', 'ADMIN')
def dashboard(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    kpis = {
        'leads_today': Lead.objects.filter(created_at__gte=today_start).count(),
        'leads_week': Lead.objects.filter(created_at__gte=week_start).count(),
        'active_clients': Client.objects.filter(user__status='ACTIVE').count(),
        'revenue_month': (
            Order.objects.filter(status='PAID', paid_at__gte=month_start)
            .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        ),
    }

    recent_leads = (
        Lead.objects.order_by('-created_at')[:10]
    )
    pending_replacements = (
        ReplacementRequest.objects.filter(status='PENDING')
        .select_related('lead', 'client', 'client__user').order_by('-id')[:10]
    )
    top_clients = (
        Order.objects.filter(status='PAID', paid_at__gte=month_start)
        .values('client_id', 'client__company_name')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('-revenue')[:5]
    )

    return render(request, 'admin_portal/dashboard.html', {
        'page_title': 'Dashboard',
        'portal_name': 'Admin',
        'kpis': kpis,
        'recent_leads': recent_leads,
        'pending_replacements': pending_replacements,
        'top_clients': top_clients,
    })


@role_required('SUPER_ADMIN', 'ADMIN')
def dashboard_chart_data(request):
    now = timezone.now()
    days = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]

    leads_rows = (
        Lead.objects.filter(created_at__date__gte=days[0])
        .values('created_at__date').annotate(count=Count('id'))
    )
    leads_by_day = {r['created_at__date']: r['count'] for r in leads_rows}

    rev_rows = (
        Order.objects.filter(status='PAID', paid_at__date__gte=days[0])
        .values('paid_at__date').annotate(total=Sum('total_amount'))
    )
    rev_by_day = {r['paid_at__date']: float(r['total'] or 0) for r in rev_rows}

    return JsonResponse({
        'labels': [d.isoformat() for d in days],
        'leads': [leads_by_day.get(d, 0) for d in days],
        'revenue': [rev_by_day.get(d, 0) for d in days],
    })
