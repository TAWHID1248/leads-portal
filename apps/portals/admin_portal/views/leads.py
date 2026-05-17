from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.leads.models import Lead
from apps.leads.services.export import export_leads_to_csv
from apps.notifications.models import ActivityLog
from apps.portals.super_admin.filters import LeadFilter


PAGE_SIZE = 50


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


@role_required('SUPER_ADMIN', 'ADMIN')
def leads_list(request):
    flt = LeadFilter(request.GET or None, queryset=Lead.objects.order_by('-created_at'))
    page = Paginator(flt.qs, PAGE_SIZE).get_page(request.GET.get('page'))
    ctx = {
        'page_title': 'Leads',
        'filter': flt,
        'page_obj': page,
        'total_count': flt.qs.count(),
    }
    if _is_htmx(request):
        return render(request, 'admin_portal/leads/_table.html', ctx)
    return render(request, 'admin_portal/leads/list.html', ctx)


@role_required('SUPER_ADMIN', 'ADMIN')
@require_POST
def lead_update_view(request, pk):
    """Admins can adjust quality_score and notes (no assign / no reject)."""
    lead = get_object_or_404(Lead, pk=pk)
    changed = []
    if 'quality_score' in request.POST:
        try:
            score = int(request.POST['quality_score'])
            if 1 <= score <= 10:
                lead.quality_score = score
                changed.append('quality_score')
        except ValueError:
            pass
    if 'notes' in request.POST:
        lead.notes = (request.POST.get('notes') or '').strip()
        changed.append('notes')
    if not changed:
        return HttpResponseBadRequest('Nothing to update')
    lead.save(update_fields=changed + ['updated_at'])
    ActivityLog.objects.create(
        user=request.user, action='admin.lead_updated',
        entity_type='Lead', entity_id=str(lead.id),
        metadata={'fields': changed, 'quality_score': lead.quality_score},
    )
    response = render(request, 'admin_portal/leads/_row.html', {'lead': lead})
    response['HX-Trigger'] = '{"showToast": {"message": "Lead updated", "level": "success"}}'
    return response


@role_required('SUPER_ADMIN', 'ADMIN')
def leads_export_view(request):
    flt = LeadFilter(request.GET or None, queryset=Lead.objects.order_by('-created_at'))
    csv_bytes = export_leads_to_csv(flt.qs)
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response = HttpResponse(csv_bytes, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="admin-leads-{timestamp}.csv"'
    return response
