from django.http import Http404
from django.shortcuts import render

from apps.accounts.decorators import client_required
from apps.billing.models import Order


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


@client_required
def orders_view(request):
    client = _client(request)
    qs = Order.objects.filter(client=client).order_by('-id')
    return render(request, 'client/orders.html', {
        'page_title': 'Orders',
        'orders': qs,
    })
