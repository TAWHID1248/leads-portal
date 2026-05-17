from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import client_required
from apps.clients.models import Subscription
from apps.leads.models import LeadAllocation, Niche, ReplacementRequest


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile for this user.')
    return profile


@client_required
def dashboard(request):
    client = _client(request)
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    allocations = LeadAllocation.objects.filter(client=client)
    total_leads = allocations.count()
    new_this_week = allocations.filter(allocated_at__gte=week_ago).count()

    active_subs = Subscription.objects.filter(client=client, status='ACTIVE').count()

    replacement_credits = ReplacementRequest.objects.filter(
        client=client, status='APPROVED', replacement_lead__isnull=True,
    ).count()

    wallet = getattr(client, 'wallet', None)
    wallet_balance = wallet.balance if wallet else Decimal('0.00')

    recent = (
        allocations.select_related('lead')
        .order_by('-allocated_at')[:5]
    )

    return render(request, 'client/dashboard.html', {
        'page_title': 'Dashboard',
        'kpis': {
            'total_leads': total_leads,
            'new_this_week': new_this_week,
            'active_subs': active_subs,
            'replacement_credits': replacement_credits,
            'wallet_balance': wallet_balance,
        },
        'recent_allocations': recent,
    })


@client_required
def chart_data_view(request):
    client = _client(request)
    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]

    rows = (
        LeadAllocation.objects
        .filter(client=client, allocated_at__date__gte=days[0])
        .values('lead__niche', 'allocated_at__date')
        .annotate(count=Count('id'))
    )

    by_niche = defaultdict(lambda: {d.isoformat(): 0 for d in days})
    niches_seen = set()
    for row in rows:
        n = row['lead__niche']
        niches_seen.add(n)
        d = row['allocated_at__date'].isoformat()
        if d in by_niche[n]:
            by_niche[n][d] = row['count']

    NICHE_COLORS = {
        'solar-usa': '#F59E0B', 'solar-uk': '#FBBF24', 'solar-ca': '#FCD34D', 'solar-au': '#FDE68A',
        'sweeps-auto': '#3B82F6', 'sweeps-health': '#10B981', 'sweeps-medicare': '#06B6D4',
        'sweeps-home': '#6366F1', 'sweeps-life': '#EC4899', 'sweeps-debt': '#EF4444',
        'sweeps-generic': '#9CA3AF',
    }
    niche_labels = dict(Niche.choices)

    datasets = []
    for n in sorted(niches_seen):
        datasets.append({
            'label': niche_labels.get(n, n),
            'data': [by_niche[n][d.isoformat()] for d in days],
            'backgroundColor': NICHE_COLORS.get(n, '#9CA3AF'),
        })

    return JsonResponse({
        'labels': [d.isoformat() for d in days],
        'datasets': datasets,
    })
