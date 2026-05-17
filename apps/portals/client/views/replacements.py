"""Client-facing replacement request flow.

The /client/replacements/ page combines the static policy box, a history of
past requests, and a 3-step modal for creating a new request.

Validation: 7-day window, valid reason, max replacement-rate per order
(default 10%, configurable via SystemSetting('max_replacement_rate')).
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import (
    Http404,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import client_required
from apps.core.models import SystemSetting
from apps.leads.models import LeadAllocation, ReplacementRequest
from apps.notifications.models import ActivityLog, Notification
from apps.notifications.services.email import send_replacement_request_email

User = get_user_model()


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


def _window_days():
    try:
        return SystemSetting.objects.get(key='replacement_window_days').get_value()
    except SystemSetting.DoesNotExist:
        return 7


def _max_rate():
    try:
        return Decimal(str(SystemSetting.objects.get(key='max_replacement_rate').get_value()))
    except SystemSetting.DoesNotExist:
        return Decimal('0.10')


def _eligible_allocations(client):
    cutoff = timezone.now() - timedelta(days=_window_days())
    return (
        LeadAllocation.objects
        .filter(
            client=client,
            allocated_at__gte=cutoff,
            status=LeadAllocation.Status.ACTIVE,
            replacement_request__isnull=True,
        )
        .select_related('lead', 'order')
    )


def _rate_ok(allocation, max_rate):
    """If this allocation has an order, ensure approving one more replacement
    won't push the order over the per-order cap."""
    order = allocation.order
    if order is None:
        return True, ''
    qty = order.quantity or 0
    if qty <= 0:
        return True, ''
    used = (
        ReplacementRequest.objects
        .filter(
            allocation__order=order,
            status__in=[ReplacementRequest.Status.PENDING, ReplacementRequest.Status.APPROVED],
        )
        .count()
    )
    new_total = used + 1
    new_rate = Decimal(new_total) / Decimal(qty)
    if new_rate > max_rate:
        return False, (
            f'Replacement cap reached for order #{order.id} '
            f'({used} of {qty} already requested; cap is {int(max_rate * 100)}%).'
        )
    return True, ''


@client_required
def replacements_view(request):
    client = _client(request)
    history = (
        ReplacementRequest.objects
        .filter(client=client)
        .select_related('lead', 'replacement_lead', 'allocation', 'reviewed_by')
        .order_by('-id')
    )
    eligible_count = _eligible_allocations(client).count()
    return render(request, 'client/replacements/list.html', {
        'page_title': 'Replacements',
        'history': history,
        'eligible_count': eligible_count,
        'window_days': _window_days(),
        'max_rate_percent': int(_max_rate() * 100),
        'reasons': ReplacementRequest.Reason.choices,
    })


@client_required
def eligible_leads_view(request):
    """HTMX search endpoint for the step-1 combobox: filters the client's
    in-window allocations by the user's query string."""
    client = _client(request)
    q = (request.GET.get('q') or '').strip()
    qs = _eligible_allocations(client)
    if q:
        qs = qs.filter(
            Q(lead__first_name__icontains=q)
            | Q(lead__last_name__icontains=q)
            | Q(lead__email__icontains=q)
            | Q(lead__phone__icontains=q)
        )
    qs = qs.order_by('-allocated_at')[:20]
    return render(request, 'client/replacements/_eligible_options.html', {'allocations': qs})


@client_required
@require_POST
def submit_replacement_view(request):
    client = _client(request)
    try:
        allocation_id = int(request.POST.get('allocation_id') or 0)
    except ValueError:
        return JsonResponse({'error': 'invalid allocation_id'}, status=400)
    reason = request.POST.get('reason') or ''
    notes = (request.POST.get('notes') or '').strip()

    if reason not in dict(ReplacementRequest.Reason.choices):
        return JsonResponse({'error': 'Invalid reason'}, status=400)

    try:
        allocation = (
            LeadAllocation.objects
            .select_related('lead', 'order')
            .get(pk=allocation_id, client=client)
        )
    except LeadAllocation.DoesNotExist:
        return JsonResponse({'error': 'Allocation not found'}, status=404)

    if hasattr(allocation, 'replacement_request'):
        return JsonResponse({'error': 'A request already exists for this lead.'}, status=400)

    cutoff = timezone.now() - timedelta(days=_window_days())
    if allocation.allocated_at < cutoff:
        return JsonResponse({'error': 'The 7-day replacement window has expired.'}, status=400)

    ok, msg = _rate_ok(allocation, _max_rate())
    if not ok:
        return JsonResponse({'error': msg}, status=400)

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

    # Notify all super admins + admins (in-app + email best-effort).
    admins = User.objects.filter(
        role__in=[User.Role.SUPER_ADMIN, User.Role.ADMIN],
        status=User.Status.ACTIVE,
    )
    for admin in admins:
        Notification.objects.create(
            user=admin,
            notification_type=Notification.NotificationType.REPLACEMENT,
            title='Replacement requested',
            message=f'{client.company_name} requested replacement for lead #{allocation.lead_id}',
            link='/super/replacements/',
        )
        try:
            send_replacement_request_email(rr, admin.email)
        except Exception:
            pass

    return JsonResponse({'ok': True, 'id': rr.id})
