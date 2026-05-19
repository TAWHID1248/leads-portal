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
from apps.leads.models import Lead, ReplacementRequest
from apps.notifications.models import Notification


@super_admin_required
def dashboard(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_leads     = Lead.objects.count()
    leads_today     = Lead.objects.filter(created_at__gte=today_start).count()
    leads_this_week = Lead.objects.filter(created_at__gte=week_start).count()
    active_clients  = Client.objects.filter(user__status=User.Status.ACTIVE).count()
    active_agents   = Agent.objects.filter(user__status=User.Status.ACTIVE).count()
    revenue_month   = (
        Order.objects.filter(status='PAID', paid_at__gte=month_start)
        .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    )
    pending_replacements = ReplacementRequest.objects.filter(status='PENDING').count()
    unread_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    recent_leads = Lead.objects.order_by('-created_at')[:10]

    return render(request, 'super_admin/dashboard.html', {
        'page_title': 'Dashboard',
        'kpis': {
            'total_leads':           total_leads,
            'leads_today':           leads_today,
            'leads_this_week':       leads_this_week,
            'active_clients':        active_clients,
            'active_agents':         active_agents,
            'revenue_month':         revenue_month,
            'pending_replacements':  pending_replacements,
            'unread_notifications':  unread_notifications,
        },
        'recent_leads': recent_leads,
    })


@super_admin_required
def dashboard_chart_data(request):
    now  = timezone.now()
    days = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]

    lead_rows = (
        Lead.objects.filter(created_at__date__gte=days[0])
        .values('created_at__date').annotate(count=Count('id'))
    )
    by_day = {r['created_at__date']: r['count'] for r in lead_rows}

    rev_rows = (
        Order.objects.filter(status='PAID', paid_at__date__gte=days[0])
        .values('paid_at__date').annotate(total=Sum('total_amount'))
    )
    rev_by_day = {r['paid_at__date']: float(r['total'] or 0) for r in rev_rows}

    return JsonResponse({
        'labels':  [d.strftime('%b %d') for d in days],
        'leads':   [by_day.get(d, 0) for d in days],
        'revenue': [rev_by_day.get(d, 0) for d in days],
    })
