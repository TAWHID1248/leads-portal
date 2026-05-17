from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from apps.accounts.decorators import client_required
from apps.billing.models import Invoice


def _client(request):
    profile = getattr(request.user, 'client_profile', None)
    if profile is None:
        raise Http404('No client profile')
    return profile


@client_required
def invoices_view(request):
    client = _client(request)
    qs = Invoice.objects.filter(client=client).select_related('order').order_by('-id')
    return render(request, 'client/invoices.html', {
        'page_title': 'Invoices',
        'invoices': qs,
    })


@client_required
def invoice_pdf_view(request, pk):
    client = _client(request)
    inv = get_object_or_404(Invoice, pk=pk, client=client)
    # PDF generation is a future deliverable; redirect to the existing url if set.
    if inv.pdf_url:
        return HttpResponseRedirect(inv.pdf_url)
    # Fallback: render an HTML view (basic).
    return render(request, 'client/invoice_html.html', {'invoice': inv})
