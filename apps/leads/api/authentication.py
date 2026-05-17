"""DRF authentication for the inbound lead ingest endpoint.

A constant-time compare against the value of the `lead_ingest_api_key`
SystemSetting. Returns an AnonymousUser on success so DRF treats the
caller as authenticated for permission checks, without owning a user row.
"""

import hmac

from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication, exceptions

from apps.core.models import SystemSetting

API_KEY_HEADER = 'HTTP_X_API_KEY'
SETTING_KEY = 'lead_ingest_api_key'


def _expected_key():
    try:
        return SystemSetting.objects.get(key=SETTING_KEY).value
    except SystemSetting.DoesNotExist:
        return None


class IngestApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        provided = request.META.get(API_KEY_HEADER, '')
        if not provided:
            raise exceptions.AuthenticationFailed('Missing X-API-KEY header.')

        expected = _expected_key()
        if not expected:
            raise exceptions.AuthenticationFailed('Lead ingest API key is not configured.')

        if not hmac.compare_digest(provided, expected):
            raise exceptions.AuthenticationFailed('Invalid API key.')

        return (AnonymousUser(), None)

    def authenticate_header(self, request):
        return 'X-API-KEY'
