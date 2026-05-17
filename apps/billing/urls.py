from django.urls import path

from apps.billing import webhooks

app_name = 'billing'

urlpatterns = [
    path('webhooks/stripe/', webhooks.stripe_webhook_view, name='stripe_webhook'),
]
