from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def _login_url():
    base = getattr(settings, 'PORTAL_BASE_URL', '') or 'http://localhost:8000'
    return base.rstrip('/') + '/login/'


def _send(template_base, subject, recipient, ctx):
    text_body = render_to_string(f'emails/{template_base}.txt', ctx)
    html_body = render_to_string(f'emails/{template_base}.html', ctx)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


def send_client_welcome_email(client, temp_password):
    ctx = {
        'client': client,
        'user': client.user,
        'temp_password': temp_password,
        'login_url': _login_url(),
    }
    _send('client_welcome', 'Welcome to LeadPortal', client.user.email, ctx)


def send_agent_welcome_email(agent, temp_password):
    ctx = {
        'agent': agent,
        'user': agent.user,
        'temp_password': temp_password,
        'login_url': _login_url(),
    }
    _send('agent_welcome', 'Welcome to LeadPortal — Agent access', agent.user.email, ctx)


def send_order_confirmation_email(order):
    ctx = {'order': order, 'client': order.client, 'user': order.client.user}
    _send('order_confirmation',
          f'Order #{order.id} confirmed — {order.quantity} {order.niche} leads',
          order.client.user.email, ctx)


def send_topup_receipt_email(client, amount):
    ctx = {'client': client, 'user': client.user, 'amount': amount}
    _send('topup_receipt', f'LeadPortal — wallet top-up ${amount}',
          client.user.email, ctx)


def send_replacement_approved_email(replacement_request):
    rr = replacement_request
    ctx = {
        'request': rr,
        'client': rr.client,
        'user': rr.client.user,
        'original_lead': rr.lead,
        'replacement_lead': rr.replacement_lead,
    }
    _send('replacement_approved',
          f'Replacement approved for lead #{rr.lead_id}',
          rr.client.user.email, ctx)


def send_replacement_denied_email(replacement_request, reason_note=''):
    rr = replacement_request
    ctx = {
        'request': rr,
        'client': rr.client,
        'user': rr.client.user,
        'original_lead': rr.lead,
        'reason_note': reason_note,
    }
    _send('replacement_denied',
          f'Replacement denied for lead #{rr.lead_id}',
          rr.client.user.email, ctx)


def send_replacement_request_email(replacement_request, recipient_email):
    rr = replacement_request
    ctx = {'request': rr, 'client': rr.client, 'lead': rr.lead}
    _send('replacement_request',
          f'Replacement request from {rr.client.company_name}',
          recipient_email, ctx)


def send_sweepstakes_winner_email(sweepstakes, winner_lead):
    ctx = {'sweepstakes': sweepstakes, 'winner': winner_lead}
    if not winner_lead.email:
        return
    _send('sweepstakes_winner',
          f"You've won: {sweepstakes.prize_title}",
          winner_lead.email, ctx)
