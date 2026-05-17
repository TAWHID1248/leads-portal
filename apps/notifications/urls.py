from django.urls import path

from apps.notifications import views

app_name = 'notifications'

urlpatterns = [
    path('notifications/unread-count/', views.unread_count_view, name='unread_count'),
]
