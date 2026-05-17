from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import super_admin_required
from apps.leads.models import Lead, Niche
from apps.notifications.models import ActivityLog
from apps.notifications.services.email import send_sweepstakes_winner_email
from apps.sweepstakes.models import Sweepstakes
from apps.sweepstakes.services.winner_draw import draw_winner


_EDITABLE_FIELDS = [
    'title', 'niche', 'prize_title', 'prize_value', 'official_rules_url',
    'start_date', 'end_date', 'draw_date', 'status',
    'target_state', 'min_age',
]


def _apply_form(sweepstakes, post, files):
    for f in _EDITABLE_FIELDS:
        if f in post:
            value = post.get(f)
            if value == '':
                value = None
            setattr(sweepstakes, f, value)
    if 'prize_image' in files:
        sweepstakes.prize_image = files['prize_image']


@super_admin_required
def SweepstakesListView(request):
    qs = Sweepstakes.objects.order_by('-id')
    today = timezone.localdate()
    return render(request, 'super_admin/sweepstakes/list.html', {
        'page_title': 'Sweepstakes',
        'sweepstakes': qs,
        'today': today,
    })


@super_admin_required
def SweepstakesCreateView(request):
    if request.method == 'POST':
        sw = Sweepstakes(status=Sweepstakes.Status.DRAFT)
        _apply_form(sw, request.POST, request.FILES)
        try:
            sw.full_clean()
        except Exception as exc:
            messages.error(request, f'Validation failed: {exc}')
            return render(request, 'super_admin/sweepstakes/create.html', {
                'page_title': 'New sweepstakes',
                'sweepstakes': sw,
                'niches': Niche.choices,
                'statuses': Sweepstakes.Status.choices,
            })
        sw.save()
        ActivityLog.objects.create(
            user=request.user, action='sweepstakes.created',
            entity_type='Sweepstakes', entity_id=str(sw.id),
            metadata={'title': sw.title, 'niche': sw.niche},
        )
        messages.success(request, f'Created sweepstakes {sw.title}.')
        return redirect('super_admin:sweepstakes_detail', pk=sw.id)
    return render(request, 'super_admin/sweepstakes/create.html', {
        'page_title': 'New sweepstakes',
        'sweepstakes': Sweepstakes(),
        'niches': Niche.choices,
        'statuses': Sweepstakes.Status.choices,
    })


@super_admin_required
def SweepstakesDetailView(request, pk):
    sweepstakes = get_object_or_404(Sweepstakes, pk=pk)
    entries = Lead.objects.filter(sweepstakes=sweepstakes).order_by('-id')[:50]
    return render(request, 'super_admin/sweepstakes/detail.html', {
        'page_title': sweepstakes.title,
        'sweepstakes': sweepstakes,
        'entries': entries,
        'entries_total': Lead.objects.filter(sweepstakes=sweepstakes).count(),
        'niches': Niche.choices,
        'statuses': Sweepstakes.Status.choices,
        'today': timezone.localdate(),
    })


@super_admin_required
def SweepstakesUpdateView(request, pk):
    sweepstakes = get_object_or_404(Sweepstakes, pk=pk)
    if sweepstakes.status not in (Sweepstakes.Status.DRAFT, Sweepstakes.Status.ACTIVE):
        messages.error(request, 'Only draft or active sweepstakes can be edited.')
        return redirect('super_admin:sweepstakes_detail', pk=pk)

    if request.method == 'POST':
        _apply_form(sweepstakes, request.POST, request.FILES)
        sweepstakes.save()
        ActivityLog.objects.create(
            user=request.user, action='sweepstakes.updated',
            entity_type='Sweepstakes', entity_id=str(sweepstakes.id),
            metadata={'fields': [f for f in _EDITABLE_FIELDS if f in request.POST]},
        )
        messages.success(request, 'Sweepstakes updated.')
        return redirect('super_admin:sweepstakes_detail', pk=sweepstakes.id)

    return render(request, 'super_admin/sweepstakes/create.html', {
        'page_title': f'Edit {sweepstakes.title}',
        'sweepstakes': sweepstakes,
        'niches': Niche.choices,
        'statuses': Sweepstakes.Status.choices,
        'is_edit': True,
    })


@super_admin_required
@require_POST
def draw_winner_view(request, pk):
    sweepstakes = get_object_or_404(Sweepstakes, pk=pk)
    winner = draw_winner(sweepstakes.id)
    if winner is None:
        messages.error(request, 'No eligible entries to pick from.')
    else:
        ActivityLog.objects.create(
            user=request.user, action='sweepstakes.winner_drawn',
            entity_type='Sweepstakes', entity_id=str(sweepstakes.id),
            metadata={'winner_lead': winner.id},
        )
        messages.success(request, f'Winner drawn: {winner.full_name or winner.email or winner.id}.')
    return redirect('super_admin:sweepstakes_detail', pk=sweepstakes.id)


@super_admin_required
@require_POST
def notify_winner_view(request, pk):
    sweepstakes = get_object_or_404(Sweepstakes, pk=pk)
    if not sweepstakes.winner_lead:
        messages.error(request, 'No winner drawn yet.')
        return redirect('super_admin:sweepstakes_detail', pk=sweepstakes.id)
    try:
        send_sweepstakes_winner_email(sweepstakes, sweepstakes.winner_lead)
        messages.success(request, f'Winner notified at {sweepstakes.winner_lead.email}.')
    except Exception as exc:
        messages.warning(request, f'Notification failed: {exc}')
    return redirect('super_admin:sweepstakes_detail', pk=sweepstakes.id)
