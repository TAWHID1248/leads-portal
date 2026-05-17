"""Client-facing leads pages. The client only sees their own allocations
(via LeadAllocation.client = request.user.client_profile)."""

import csv
import io
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import client_required
from apps.core.models import SystemSetting
from apps.leads.models import LeadAllocation, Niche, ReplacementRequest
from apps.notifications.models import ActivityLog


PAGE_SIZE = 50


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile for this user.')
    return profile


def _replacement_window_days():
    try:
        return SystemSetting.objects.get(key='replacement_window_days').get_value()
    except SystemSetting.DoesNotExist:
        return 7


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _client_allocations(client):
    return (
        LeadAllocation.objects
        .filter(client=client)
        .select_related('lead')
    )


def _apply_filters(qs, params):
    search = (params.get('search') or '').strip()
    niche = params.get('niche')
    state = (params.get('state') or '').strip()
    my_status = params.get('my_status')
    date_from = params.get('date_from')
    date_to = params.get('date_to')

    if search:
        qs = qs.filter(
            Q(lead__first_name__icontains=search)
            | Q(lead__last_name__icontains=search)
            | Q(lead__email__icontains=search)
            | Q(lead__phone__icontains=search)
        )
    if niche:
        qs = qs.filter(lead__niche=niche)
    if state:
        qs = qs.filter(lead__state__iexact=state)
    if my_status:
        qs = qs.filter(client_status=my_status)
    if date_from:
        qs = qs.filter(allocated_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(allocated_at__date__lte=date_to)
    return qs


def _decorate(allocations, window_days, now):
    new_cutoff = now - timedelta(hours=48)
    win_cutoff = now - timedelta(days=window_days)
    items = list(allocations)
    for a in items:
        a.is_new_within_48h = a.allocated_at >= new_cutoff
        a.replacement_eligible = (
            a.allocated_at >= win_cutoff
            and a.status == LeadAllocation.Status.ACTIVE
            and not hasattr(a, 'replacement_request')
        )
    return items


@client_required
def LeadListView(request):
    client = _client(request)
    qs = _apply_filters(_client_allocations(client), request.GET).order_by('-allocated_at')

    window_days = _replacement_window_days()
    now = timezone.now()
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
    page.object_list = _decorate(page.object_list, window_days, now)
    ctx = {
        'page_title': 'My Leads',
        'page_obj': page,
        'total_count': qs.count(),
        'niches': Niche.choices,
        'client_statuses': LeadAllocation.ClientStatus.choices,
        'replacement_window_days': window_days,
        'now': now,
    }
    if _is_htmx(request):
        return render(request, 'client/leads/_table.html', ctx)
    return render(request, 'client/leads/list.html', ctx)


@client_required
@require_POST
def update_status_view(request, pk):
    client = _client(request)
    allocation = get_object_or_404(
        _client_allocations(client),
        pk=pk,
    )
    new_status = request.POST.get('client_status')
    if new_status not in dict(LeadAllocation.ClientStatus.choices):
        return HttpResponseBadRequest('Invalid status')
    allocation.client_status = new_status
    allocation.save(update_fields=['client_status'])

    ActivityLog.objects.create(
        user=request.user, action='client.lead_status_changed',
        entity_type='LeadAllocation', entity_id=str(allocation.id),
        metadata={'client_status': new_status},
    )

    window_days = _replacement_window_days()
    now = timezone.now()
    _decorate([allocation], window_days, now)
    response = render(request, 'client/leads/_row.html', {
        'a': allocation,
        'now': now,
        'replacement_window_days': window_days,
        'client_statuses': LeadAllocation.ClientStatus.choices,
    })
    response['HX-Trigger'] = (
        '{"showToast": {"message": "Status updated", "level": "success"}}'
    )
    return response


@client_required
def LeadDetailDrawerView(request, pk):
    client = _client(request)
    allocation = get_object_or_404(_client_allocations(client), pk=pk)
    if allocation.viewed_at is None:
        allocation.viewed_at = timezone.now()
        allocation.save(update_fields=['viewed_at'])
    window_days = _replacement_window_days()
    within_window = (timezone.now() - allocation.allocated_at) <= timedelta(days=window_days)
    return render(request, 'client/leads/_detail_drawer.html', {
        'a': allocation,
        'lead': allocation.lead,
        'within_replacement_window': within_window,
    })


@client_required
def export_view(request):
    client = _client(request)
    qs = _apply_filters(_client_allocations(client), request.GET).order_by('-allocated_at')

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'allocation_id', 'lead_id', 'allocated_at', 'viewed_at', 'my_status',
        'first_name', 'last_name', 'email', 'phone',
        'address', 'city', 'state', 'zip_code',
        'niche', 'quality_score',
        'is_homeowner', 'monthly_bill', 'credit_score', 'roof_type', 'solar_timeline',
        'annual_income', 'currently_insured',
        'price_per_lead',
    ])
    for a in qs.iterator(chunk_size=500):
        L = a.lead
        writer.writerow([
            a.id, L.id, a.allocated_at.isoformat(),
            a.viewed_at.isoformat() if a.viewed_at else '',
            a.client_status,
            L.first_name, L.last_name, L.email, L.phone,
            L.address, L.city, L.state, L.zip_code,
            L.niche, L.quality_score,
            L.is_homeowner if L.is_homeowner is not None else '',
            L.monthly_bill if L.monthly_bill is not None else '',
            L.credit_score, L.roof_type, L.solar_timeline,
            L.annual_income if L.annual_income is not None else '',
            L.currently_insured if L.currently_insured is not None else '',
            a.price_per_lead,
        ])

    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response = HttpResponse(buf.getvalue().encode('utf-8'), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="my-leads-{timestamp}.csv"'
    return response


@client_required
@require_POST
def request_replacement_view(request, pk):
    client = _client(request)
    allocation = get_object_or_404(_client_allocations(client), pk=pk)
    window_days = _replacement_window_days()
    if (timezone.now() - allocation.allocated_at) > timedelta(days=window_days):
        return HttpResponseBadRequest('Replacement window has expired.')

    reason = request.POST.get('reason', '')
    notes = request.POST.get('notes', '')
    if reason not in dict(ReplacementRequest.Reason.choices):
        return HttpResponseBadRequest('Invalid reason')

    if hasattr(allocation, 'replacement_request'):
        return HttpResponseBadRequest('A replacement request already exists for this lead.')

    rr = ReplacementRequest.objects.create(
        allocation=allocation,
        lead=allocation.lead,
        client=client,
        reason=reason,
        notes=notes,
        status=ReplacementRequest.Status.PENDING,
    )
    ActivityLog.objects.create(
        user=request.user, action='client.replacement_requested',
        entity_type='ReplacementRequest', entity_id=str(rr.id),
        metadata={'allocation_id': allocation.id, 'reason': reason},
    )
    return JsonResponse({'ok': True, 'id': rr.id})
