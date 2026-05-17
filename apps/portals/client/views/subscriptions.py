from decimal import Decimal

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import client_required
from apps.billing.services import stripe_client
from apps.clients.models import Subscription
from apps.leads.models import Niche
from apps.notifications.models import ActivityLog


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


@client_required
def subscriptions_view(request):
    client = _client(request)
    subs = client.subscriptions.all().order_by('-id')
    return render(request, 'client/subscriptions.html', {
        'page_title': 'Subscriptions',
        'subscriptions': subs,
        'niches': Niche.choices,
        'billing_periods': Subscription.BillingPeriod.choices,
    })


@client_required
@require_POST
def create_subscription_view(request):
    client = _client(request)
    niche = request.POST.get('niche')
    leads_per_period = int(request.POST.get('leads_per_period') or 0)
    price_per_lead = Decimal(request.POST.get('price_per_lead') or '0')
    billing_period = request.POST.get('billing_period') or Subscription.BillingPeriod.MONTHLY
    is_exclusive = request.POST.get('is_exclusive') == 'on'

    if niche not in dict(Niche.choices) or leads_per_period <= 0 or price_per_lead <= 0:
        messages.error(request, 'Invalid subscription parameters.')
        return redirect('client:subscriptions')

    sub = Subscription.objects.create(
        client=client, niche=niche,
        leads_per_period=leads_per_period,
        price_per_lead=price_per_lead,
        billing_period=billing_period,
        is_exclusive=is_exclusive,
        status=Subscription.Status.ACTIVE,
    )
    ActivityLog.objects.create(
        user=request.user, action='client.subscription_created',
        entity_type='Subscription', entity_id=str(sub.id),
        metadata={'niche': niche, 'qty': leads_per_period, 'price': str(price_per_lead)},
    )
    messages.success(request, 'Subscription created.')
    return redirect('client:subscriptions')


@client_required
@require_POST
def cancel_subscription_view(request, pk):
    client = _client(request)
    sub = get_object_or_404(Subscription, pk=pk, client=client)
    if sub.stripe_subscription_id:
        try:
            stripe_client.cancel_subscription(sub.stripe_subscription_id)
        except Exception as exc:
            messages.warning(request, f'Stripe cancel failed: {exc}')

    from django.utils import timezone
    sub.status = Subscription.Status.CANCELLED
    sub.cancelled_at = timezone.now()
    sub.save(update_fields=['status', 'cancelled_at'])

    ActivityLog.objects.create(
        user=request.user, action='client.subscription_cancelled',
        entity_type='Subscription', entity_id=str(sub.id),
        metadata={},
    )
    messages.success(request, 'Subscription cancelled.')
    return redirect('client:subscriptions')
