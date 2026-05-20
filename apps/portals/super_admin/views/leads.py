"""Super Admin leads management views.

The list/table is HTMX-friendly: the same view returns the full page on a
regular request, but if the request comes from HTMX (``HX-Request: true``),
only the inner table partial is rendered for an in-place swap.
"""

import json

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import super_admin_required
from apps.clients.models import Client
from apps.leads.models import Lead, LeadAllocation
from apps.leads.services.export import export_leads_to_csv
from apps.notifications.models import ActivityLog
from apps.portals.super_admin.filters import LeadFilter


PAGE_SIZE = 50

NICHE_CATEGORIES = {
    'sweepstakes': {
        'title': 'Sweepstakes Leads',
        'prefix': 'sweeps-',
        'icon': 'bi-gift',
        'url_name': 'leads_sweepstakes',
    },
    'solar': {
        'title': 'Solar Leads',
        'prefix': 'solar-',
        'icon': 'bi-sun',
        'url_name': 'leads_solar',
    },
    'homeowner': {
        'title': 'Homeowner Leads',
        'prefix': 'homeowner-',
        'icon': 'bi-house',
        'url_name': 'leads_homeowner',
    },
    'payday': {
        'title': 'Payday Leads',
        'prefix': 'payday-',
        'icon': 'bi-cash-coin',
        'url_name': 'leads_payday',
    },
}


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _base_qs():
    return Lead.objects.order_by('-created_at')


def _filtered_page(request, queryset=None):
    qs = queryset if queryset is not None else _base_qs()
    flt = LeadFilter(request.GET or None, queryset=qs)
    page = Paginator(flt.qs, PAGE_SIZE).get_page(request.GET.get('page'))
    return flt, page


@super_admin_required
def LeadListView(request):
    flt, page = _filtered_page(request)
    list_url = reverse('super_admin:leads_list')
    ctx = {
        'page_title': 'Leads',
        'filter': flt,
        'page_obj': page,
        'total_count': flt.qs.count(),
        'list_url': list_url,
        'niche_categories': NICHE_CATEGORIES,
    }
    if _is_htmx(request):
        return render(request, 'super_admin/leads/_table.html', ctx)
    ctx['clients'] = Client.objects.select_related('user').order_by('company_name')
    return render(request, 'super_admin/leads/list.html', ctx)


@super_admin_required
def niche_leads_view(request, category):
    from django.http import Http404
    cat = NICHE_CATEGORIES.get(category)
    if not cat:
        raise Http404
    base_qs = Lead.objects.filter(niche__startswith=cat['prefix']).order_by('-created_at')
    flt, page = _filtered_page(request, queryset=base_qs)
    list_url = reverse(f"super_admin:{cat['url_name']}")
    ctx = {
        'page_title': cat['title'],
        'filter': flt,
        'page_obj': page,
        'total_count': flt.qs.count(),
        'list_url': list_url,
        'niche_category': category,
        'niche_categories': NICHE_CATEGORIES,
    }
    if _is_htmx(request):
        return render(request, 'super_admin/leads/_table.html', ctx)
    ctx['clients'] = Client.objects.select_related('user').order_by('company_name')
    return render(request, 'super_admin/leads/niche_list.html', ctx)


@super_admin_required
def LeadDetailView(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    allocations = lead.allocations.select_related('client', 'client__user').order_by('-allocated_at')
    activity = ActivityLog.objects.filter(
        entity_type='Lead', entity_id=str(lead.id)
    ).order_by('-created_at')[:50]
    return render(request, 'super_admin/leads/detail.html', {
        'page_title': f'Lead #{lead.id}',
        'lead': lead,
        'allocations': allocations,
        'activity': activity,
        'clients': Client.objects.select_related('user').order_by('company_name'),
    })


@super_admin_required
def lead_drawer_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    allocations = lead.allocations.select_related('client', 'client__user').order_by('-allocated_at')
    activity = ActivityLog.objects.filter(
        entity_type='Lead', entity_id=str(lead.id)
    ).order_by('-created_at')[:25]
    return render(request, 'super_admin/leads/_detail_drawer.html', {
        'lead': lead,
        'allocations': allocations,
        'activity': activity,
        'clients': Client.objects.select_related('user').order_by('company_name'),
    })


def _hx_trigger_toast(response, message, level='success'):
    payload = {'showToast': {'message': message, 'level': level}}
    response['HX-Trigger'] = json.dumps(payload)
    return response


@super_admin_required
@require_POST
def assign_lead_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    client_id = request.POST.get('client_id')
    price_raw = request.POST.get('price_per_lead')

    if not client_id or not price_raw:
        return HttpResponseBadRequest('client_id and price_per_lead are required')

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return HttpResponseBadRequest('Unknown client')

    try:
        price = float(price_raw)
    except ValueError:
        return HttpResponseBadRequest('Invalid price')

    allocation, created = LeadAllocation.objects.get_or_create(
        lead=lead,
        client=client,
        defaults={
            'price_per_lead': price,
            'status': LeadAllocation.Status.ACTIVE,
            'client_status': LeadAllocation.ClientStatus.NEW,
        },
    )
    if lead.status in (Lead.Status.NEW, Lead.Status.AVAILABLE):
        lead.status = Lead.Status.ALLOCATED
        lead.save(update_fields=['status', 'updated_at'])

    ActivityLog.objects.create(
        user=request.user,
        action='lead.assigned',
        entity_type='Lead',
        entity_id=str(lead.id),
        metadata={'client_id': client.id, 'price': float(price), 'created': created},
    )

    msg = f'Lead assigned to {client.company_name}' if created \
        else f'{client.company_name} already had this lead'
    response = render(request, 'super_admin/leads/_row.html', {'lead': lead})
    return _hx_trigger_toast(response, msg, 'success' if created else 'info')


@super_admin_required
@require_POST
def update_lead_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    changed = []

    if 'status' in request.POST:
        new_status = request.POST['status']
        if new_status in dict(Lead.Status.choices):
            lead.status = new_status
            changed.append('status')

    if 'quality_score' in request.POST:
        try:
            score = int(request.POST['quality_score'])
            if 1 <= score <= 10:
                lead.quality_score = score
                changed.append('quality_score')
        except ValueError:
            pass

    if not changed:
        return HttpResponseBadRequest('Nothing to update')

    lead.save(update_fields=changed + ['updated_at'])
    ActivityLog.objects.create(
        user=request.user,
        action='lead.updated',
        entity_type='Lead',
        entity_id=str(lead.id),
        metadata={'fields': changed, 'status': lead.status, 'quality_score': lead.quality_score},
    )

    response = render(request, 'super_admin/leads/_row.html', {'lead': lead})
    return _hx_trigger_toast(response, 'Lead updated', 'success')


def _ids_from_post(request):
    ids = request.POST.getlist('ids') or request.POST.getlist('ids[]')
    out = []
    for raw in ids:
        for part in str(raw).split(','):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
    return out


@super_admin_required
@require_POST
def bulk_assign_view(request):
    ids = _ids_from_post(request)
    if not ids:
        return HttpResponseBadRequest('No leads selected')

    client_id = request.POST.get('client_id')
    price_raw = request.POST.get('price_per_lead')
    if not client_id or not price_raw:
        return HttpResponseBadRequest('client_id and price_per_lead are required')

    try:
        client = Client.objects.get(pk=client_id)
        price = float(price_raw)
    except (Client.DoesNotExist, ValueError):
        return HttpResponseBadRequest('Invalid client or price')

    created_count = 0
    leads = Lead.objects.filter(id__in=ids)
    for lead in leads:
        _, created = LeadAllocation.objects.get_or_create(
            lead=lead,
            client=client,
            defaults={
                'price_per_lead': price,
                'status': LeadAllocation.Status.ACTIVE,
                'client_status': LeadAllocation.ClientStatus.NEW,
            },
        )
        if created:
            created_count += 1
        if lead.status in (Lead.Status.NEW, Lead.Status.AVAILABLE):
            lead.status = Lead.Status.ALLOCATED
            lead.save(update_fields=['status', 'updated_at'])

    ActivityLog.objects.create(
        user=request.user,
        action='lead.bulk_assigned',
        entity_type='Lead',
        entity_id=','.join(str(i) for i in ids[:50]),
        metadata={'client_id': client.id, 'price': price, 'created': created_count, 'total': len(ids)},
    )

    return JsonResponse({
        'ok': True,
        'created': created_count,
        'total': len(ids),
        'redirect': reverse('super_admin:leads_list'),
    })


@super_admin_required
@require_POST
def bulk_export_view(request):
    ids = _ids_from_post(request)
    if ids:
        qs = Lead.objects.filter(id__in=ids).order_by('-created_at')
    else:
        flt = LeadFilter(request.POST or None, queryset=_base_qs())
        qs = flt.qs

    csv_bytes = export_leads_to_csv(qs)
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response = HttpResponse(csv_bytes, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="leads-{timestamp}.csv"'

    ActivityLog.objects.create(
        user=request.user,
        action='lead.bulk_exported',
        entity_type='Lead',
        entity_id=','.join(str(i) for i in ids[:50]),
        metadata={'count': qs.count()},
    )
    return response


@super_admin_required
@require_POST
def bulk_reject_view(request):
    ids = _ids_from_post(request)
    if not ids:
        return HttpResponseBadRequest('No leads selected')

    updated = Lead.objects.filter(id__in=ids).update(
        status=Lead.Status.REJECTED,
        updated_at=timezone.now(),
    )
    ActivityLog.objects.create(
        user=request.user,
        action='lead.bulk_rejected',
        entity_type='Lead',
        entity_id=','.join(str(i) for i in ids[:50]),
        metadata={'count': updated},
    )
    return JsonResponse({'ok': True, 'count': updated})
