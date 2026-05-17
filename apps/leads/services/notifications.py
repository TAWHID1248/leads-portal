"""Per-allocation notification fanout. Email/SMS/webhook delivery is TODO —
for now we always create a Notification row so it appears in the bell."""

from apps.notifications.models import Notification


def notify_client_new_lead(allocation):
    client = allocation.client
    lead = allocation.lead

    Notification.objects.create(
        user=client.user,
        notification_type=Notification.NotificationType.LEAD,
        title='New lead allocated',
        message=(
            f'A new lead has been allocated to you: {lead.full_name} '
            f'({lead.email or lead.phone or "no contact"})'
        ),
        link=f'/client/leads/{lead.id}/',
    )

    # TODO: webhook delivery if client.webhook_url
    # TODO: email if client.notify_email
    # TODO: SMS if client.notify_sms
