import json
import secrets

from django.conf import settings as dj_settings
from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.decorators import super_admin_required
from apps.core.models import SystemSetting
from apps.notifications.models import ActivityLog


# Keys grouped per tab; everything else falls back to the System tab.
PRICING_KEY_PREFIX = 'price_default_'
SYSTEM_KEYS = [
    'replacement_window_days',
    'max_replacement_rate',
    'lead_dedup_window_days',
    'auto_distribute_enabled',
    'auto_distribute_schedule',
]
INGEST_KEY = 'lead_ingest_api_key'


def _mask(value, keep=6):
    if not value:
        return ''
    if len(value) <= keep * 2:
        return '•' * len(value)
    return value[:keep] + '…' + value[-keep:]


def _integrations_status():
    return [
        {
            'name': 'SendGrid (email)',
            'configured': bool(getattr(dj_settings, 'EMAIL_HOST_PASSWORD', '')),
            'detail': 'EMAIL_HOST_PASSWORD env var',
        },
        {
            'name': 'Stripe (billing)',
            'configured': bool(getattr(dj_settings, 'STRIPE_SECRET_KEY', '') or
                               getattr(dj_settings, 'STRIPE_API_KEY', '')),
            'detail': 'STRIPE_SECRET_KEY env var',
        },
        {
            'name': 'Twilio (SMS)',
            'configured': bool(getattr(dj_settings, 'TWILIO_AUTH_TOKEN', '')),
            'detail': 'TWILIO_AUTH_TOKEN env var',
        },
    ]


@super_admin_required
def settings_view(request):
    all_settings = {s.key: s for s in SystemSetting.objects.all()}
    pricing = sorted(
        [s for k, s in all_settings.items() if k.startswith(PRICING_KEY_PREFIX)],
        key=lambda s: s.key,
    )
    system = [all_settings[k] for k in SYSTEM_KEYS if k in all_settings]

    ingest = all_settings.get(INGEST_KEY)
    ingest_display = _mask(ingest.value) if ingest else ''

    return render(request, 'super_admin/settings/index.html', {
        'page_title': 'Settings',
        'pricing': pricing,
        'system': system,
        'ingest': ingest,
        'ingest_display': ingest_display,
        'integrations': _integrations_status(),
        'active_tab': request.GET.get('tab') or 'pricing',
    })


@super_admin_required
@require_POST
def update_setting_view(request):
    key = (request.POST.get('key') or '').strip()
    raw_value = request.POST.get('value', '')
    if not key:
        return HttpResponseBadRequest('Missing key')

    try:
        s = SystemSetting.objects.get(key=key)
    except SystemSetting.DoesNotExist:
        return HttpResponseBadRequest('Unknown key')

    # Validate by value_type
    try:
        if s.value_type == s.ValueType.INT:
            int(raw_value)
        elif s.value_type == s.ValueType.FLOAT:
            float(raw_value)
        elif s.value_type == s.ValueType.BOOL:
            if str(raw_value).lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                raise ValueError('boolean')
            raw_value = 'true' if str(raw_value).lower() in ('true', '1', 'yes') else 'false'
        elif s.value_type == s.ValueType.JSON:
            json.loads(raw_value)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return HttpResponseBadRequest(f'Invalid value for {s.value_type}: {exc}')

    s.value = raw_value
    s.save(update_fields=['value'])

    ActivityLog.objects.create(
        user=request.user, action='setting.updated',
        entity_type='SystemSetting', entity_id=key,
        metadata={'value': '***' if s.is_secret else raw_value},
    )
    messages.success(request, f'Updated {key}.')
    return redirect(f"{reverse('super_admin:settings')}?tab={request.POST.get('tab', 'pricing')}")


@super_admin_required
@require_POST
def regenerate_ingest_key_view(request):
    confirm = request.POST.get('confirm') == 'yes'
    if not confirm:
        return HttpResponseBadRequest('confirm=yes is required')

    try:
        s = SystemSetting.objects.get(key=INGEST_KEY)
    except SystemSetting.DoesNotExist:
        return HttpResponseBadRequest('Setting not present')

    old_masked = _mask(s.value)
    s.value = secrets.token_hex(32)
    s.save(update_fields=['value'])

    ActivityLog.objects.create(
        user=request.user, action='setting.api_key_regenerated',
        entity_type='SystemSetting', entity_id=INGEST_KEY,
        metadata={'old_masked': old_masked},
    )
    messages.success(request, 'Lead ingest API key regenerated. Update the WP plugin.')
    return redirect(f"{reverse('super_admin:settings')}?tab=api")
