from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import role_required
from apps.leads.models import ReplacementRequest
from apps.leads.services.replacements import (
    NoReplacementAvailable,
    approve_replacement,
    deny_replacement,
)
from apps.notifications.models import ActivityLog


@role_required('SUPER_ADMIN', 'ADMIN')
def replacements_view(request):
    base = (
        ReplacementRequest.objects
        .select_related('lead', 'client', 'client__user', 'allocation',
                        'replacement_lead', 'reviewed_by')
    )
    pending = base.filter(status=ReplacementRequest.Status.PENDING).order_by('-id')
    decided = base.exclude(status=ReplacementRequest.Status.PENDING).order_by('-id')[:200]
    return render(request, 'admin_portal/replacements.html', {
        'page_title': 'Replacements',
        'pending': pending,
        'decided': decided,
    })


@role_required('SUPER_ADMIN', 'ADMIN')
@require_POST
def approve_replacement_view(request, pk):
    rr = get_object_or_404(ReplacementRequest, pk=pk)
    try:
        approve_replacement(rr, reviewed_by=request.user)
    except NoReplacementAvailable as exc:
        messages.error(request, str(exc))
        return redirect('admin_portal:replacements')
    ActivityLog.objects.create(
        user=request.user, action='replacement.approved',
        entity_type='ReplacementRequest', entity_id=str(rr.id),
        metadata={'via': 'admin_portal'},
    )
    messages.success(request, f'Replacement #{rr.id} approved.')
    return redirect('admin_portal:replacements')


@role_required('SUPER_ADMIN', 'ADMIN')
@require_POST
def deny_replacement_view(request, pk):
    rr = get_object_or_404(ReplacementRequest, pk=pk)
    note = (request.POST.get('reason_note') or '').strip()
    deny_replacement(rr, reviewed_by=request.user, reason_note=note)
    ActivityLog.objects.create(
        user=request.user, action='replacement.denied',
        entity_type='ReplacementRequest', entity_id=str(rr.id),
        metadata={'via': 'admin_portal', 'note': note},
    )
    messages.info(request, f'Replacement #{rr.id} denied.')
    return redirect('admin_portal:replacements')
