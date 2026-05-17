from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import super_admin_required
from apps.billing.models import Invoice, Order
from apps.clients.models import Wallet, WalletTransaction


@super_admin_required
def billing_overview(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    kpis = {
        'revenue_month': (
            Order.objects.filter(status='PAID', paid_at__gte=month_start)
            .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        ),
        'revenue_today': (
            Order.objects.filter(status='PAID', paid_at__gte=today_start)
            .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        ),
        'pending_orders': Order.objects.filter(status='PENDING').count(),
        'unpaid_invoices': Invoice.objects.filter(status__in=['UNPAID', 'OVERDUE']).count(),
        'total_wallet_balance': (
            Wallet.objects.aggregate(s=Sum('balance'))['s'] or Decimal('0.00')
        ),
    }

    recent_orders = (
        Order.objects.select_related('client').order_by('-id')[:15]
    )
    recent_invoices = (
        Invoice.objects.select_related('client', 'order').order_by('-id')[:15]
    )
    recent_wallet_txs = (
        WalletTransaction.objects
        .select_related('wallet', 'wallet__client').order_by('-id')[:15]
    )
    top_clients_month = (
        Order.objects.filter(status='PAID', paid_at__gte=month_start)
        .values('client_id', 'client__company_name')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('-revenue')[:5]
    )

    return render(request, 'super_admin/billing/overview.html', {
        'page_title': 'Billing',
        'kpis': kpis,
        'recent_orders': recent_orders,
        'recent_invoices': recent_invoices,
        'recent_wallet_txs': recent_wallet_txs,
        'top_clients_month': top_clients_month,
    })
