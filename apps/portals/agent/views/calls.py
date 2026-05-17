import csv
import io

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.agents.models import CallLog
from apps.leads.models import Niche
from apps.portals.agent.views._common import require_agent


def _filter_calls(agent, params):
    qs = CallLog.objects.filter(agent=agent).select_related('lead').order_by('-called_at')
    outcome = params.get('outcome') or ''
    niche = params.get('niche') or ''
    date_from = params.get('date_from') or ''
    date_to = params.get('date_to') or ''
    if outcome:
        qs = qs.filter(outcome=outcome)
    if niche:
        qs = qs.filter(lead__niche=niche)
    if date_from:
        qs = qs.filter(called_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(called_at__date__lte=date_to)
    return qs


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def calls_view(request):
    agent = require_agent(request)
    qs = _filter_calls(agent, request.GET)
    page = Paginator(qs, 50).get_page(request.GET.get('page'))
    return render(request, 'agent/calls.html', {
        'page_title': 'Call log',
        'page_obj': page,
        'total_count': qs.count(),
        'outcomes': CallLog.Outcome.choices,
        'niches': Niche.choices,
    })


@role_required('SUPER_ADMIN', 'ADMIN', 'AGENT')
def calls_export_view(request):
    agent = require_agent(request)
    qs = _filter_calls(agent, request.GET)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'id', 'called_at', 'outcome', 'duration_seconds', 'notes', 'next_follow_up',
        'lead_id', 'lead_name', 'lead_phone', 'lead_email', 'lead_niche',
    ])
    for c in qs.iterator(chunk_size=500):
        writer.writerow([
            c.id, c.called_at.isoformat(), c.outcome, c.duration_seconds,
            (c.notes or '').replace('\n', ' '),
            c.next_follow_up.isoformat() if c.next_follow_up else '',
            c.lead_id,
            f'{c.lead.first_name} {c.lead.last_name}'.strip(),
            c.lead.phone, c.lead.email, c.lead.niche,
        ])
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    response = HttpResponse(buf.getvalue().encode('utf-8'), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="calls-{timestamp}.csv"'
    return response
