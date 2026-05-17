from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.notifications.models import Notification


@login_required
@require_GET
def unread_count_view(request):
    count = (
        Notification.objects
        .filter(user=request.user, is_read=False)
        .count()
    )
    return render(request, 'partials/_notification_badge.html', {
        'unread_notification_count': count,
    })
