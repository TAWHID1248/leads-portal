from apps.notifications.models import Notification


def portal_context(request):
    portal = None
    unread_notification_count = 0

    if request.user.is_authenticated:
        path = request.path
        if path.startswith('/super'):
            portal = 'super'
        elif path.startswith('/admin'):
            portal = 'admin'
        elif path.startswith('/agent'):
            portal = 'agent'
        elif path.startswith('/client'):
            portal = 'client'

        try:
            unread_notification_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
        except Exception:
            unread_notification_count = 0

    return {
        'current_portal': portal,
        'unread_notification_count': unread_notification_count,
    }
