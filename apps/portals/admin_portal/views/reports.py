import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.billing.models import Order
from apps.leads.models import Lead, Niche


def _date_range(request, default_days=30):
    today = timezone.localdate()
    start = request.GET.get('start')
    end = request.GET.get('end')
    if not start:
        start = (today - timedelta(days=default_days)).isoformat()
    if not end:
        end = today.isoformat()
    return start, end


@role_required('SUPER_ADMIN', 'ADMIN')
def leads_report_view(request):
    start, end = _date_range(request)
    qs = Lead.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    niche = request.GET.get('niche')
    if niche:
        qs = qs.filter(niche=niche)

    rows = (
        qs.values('niche').annotate(count=Count('id')).order_by('-count')
    )
    total = qs.count()

    if request.GET.get('export') == 'csv':
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['niche', 'count'])
        for r in rows:
            w.writerow([r['niche'], r['count']])
        w.writerow(['__total__', total])
        response = HttpResponse(buf.getvalue().encode('utf-8'), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="leads-report-{start}-{end}.csv"'
        return response

    return render(request, 'admin_portal/reports/leads.html', {
        'page_title': 'Lead volume',
        'rows': rows,
        'total': total,
        'start': start, 'end': end,
        'niches': Niche.choices,
        'selected_niche': niche,
    })


@role_required('SUPER_ADMIN', 'ADMIN')
def revenue_report_view(request):
    start, end = _date_range(request)
    qs = Order.objects.filter(
        status='PAID',
        paid_at__date__gte=start,
        paid_at__date__lte=end,
    )
    niche = request.GET.get('niche')
    if niche:
        qs = qs.filter(niche=niche)

    rows = (
        qs.values('niche')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('-revenue')
    )
    total_revenue = qs.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    total_orders = qs.count()

    if request.GET.get('export') == 'csv':
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['niche', 'orders', 'revenue'])
        for r in rows:
            w.writerow([r['niche'], r['orders'], r['revenue']])
        w.writerow(['__total__', total_orders, total_revenue])
        response = HttpResponse(buf.getvalue().encode('utf-8'), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="revenue-report-{start}-{end}.csv"'
        return response

    return render(request, 'admin_portal/reports/revenue.html', {
        'page_title': 'Revenue',
        'rows': rows,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'start': start, 'end': end,
        'niches': Niche.choices,
        'selected_niche': niche,
    })
