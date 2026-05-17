from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import client_required
from apps.billing.services import orders as orders_service
from apps.billing.services import wallet as wallet_service
from apps.billing.services.wallet import InsufficientFunds
from apps.core.models import SystemSetting
from apps.leads.models import Niche
from apps.notifications.services.email import send_order_confirmation_email


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


def _price(niche, exclusive):
    slug = niche.replace('-', '_')
    suffix = 'exclusive' if exclusive else 'shared'
    try:
        return Decimal(SystemSetting.objects.get(key=f'price_default_{slug}_{suffix}').value)
    except SystemSetting.DoesNotExist:
        return None


@client_required
def pricing_view(request):
    cards = []
    for niche_value, niche_label in Niche.choices:
        cards.append({
            'value': niche_value,
            'label': niche_label,
            'shared': _price(niche_value, exclusive=False),
            'exclusive': _price(niche_value, exclusive=True),
        })
    client = _client(request)
    wallet_balance = wallet_service.get_balance(client)
    return render(request, 'client/pricing.html', {
        'page_title': 'Pricing',
        'cards': cards,
        'wallet_balance': wallet_balance,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@client_required
@require_POST
def buy_leads_view(request):
    client = _client(request)
    niche = request.POST.get('niche')
    quantity = int(request.POST.get('quantity') or 0)
    exclusive = request.POST.get('exclusive') == 'true'
    payment_method = request.POST.get('payment_method') or 'wallet'

    if niche not in dict(Niche.choices):
        return JsonResponse({'error': 'Invalid niche'}, status=400)
    if quantity <= 0:
        return JsonResponse({'error': 'Quantity must be positive'}, status=400)

    price = _price(niche, exclusive)
    if price is None:
        return JsonResponse({'error': f'No pricing configured for {niche}'}, status=400)

    try:
        order, allocations, client_secret = orders_service.create_order(
            client=client, niche=niche, quantity=quantity,
            price_per_lead=price, exclusive=exclusive,
            payment_method=payment_method,
        )
    except InsufficientFunds as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if order.status == 'PAID':
        try:
            send_order_confirmation_email(order)
        except Exception:
            pass

    return JsonResponse({
        'ok': True,
        'order_id': order.id,
        'status': order.status,
        'allocations': len(allocations),
        'client_secret': client_secret,
    })
