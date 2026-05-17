from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import client_required
from apps.billing.services import stripe_client
from apps.clients.models import Wallet, WalletTransaction


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


@client_required
def wallet_view(request):
    client = _client(request)
    wallet = getattr(client, 'wallet', None)
    transactions = (
        WalletTransaction.objects
        .filter(wallet=wallet) if wallet else WalletTransaction.objects.none()
    ).order_by('-created_at')[:200]
    return render(request, 'client/wallet.html', {
        'page_title': 'Wallet',
        'wallet': wallet,
        'transactions': transactions,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'stripe_configured': bool(settings.STRIPE_PUBLISHABLE_KEY and settings.STRIPE_SECRET_KEY),
    })


@client_required
@require_POST
def topup_intent_view(request):
    """Create a PaymentIntent for a wallet top-up and return its client_secret."""
    client = _client(request)
    try:
        amount = Decimal(request.POST.get('amount') or '0')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid amount'}, status=400)
    if amount <= 0:
        return JsonResponse({'error': 'amount must be positive'}, status=400)

    try:
        customer = stripe_client.create_or_get_customer(client)
        intent = stripe_client.create_payment_intent(
            amount,
            customer_id=customer['id'],
            metadata={'kind': 'topup', 'client_id': client.id},
        )
    except stripe_client.StripeNotConfigured as exc:
        return JsonResponse({'error': str(exc)}, status=503)

    return JsonResponse({
        'ok': True,
        'client_secret': intent['client_secret'],
        'amount': str(amount),
    })
