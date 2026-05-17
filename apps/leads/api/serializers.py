"""Inbound lead serializer for the WordPress / external ingest endpoint.

The WP plugin posts camelCase JSON; we accept both camelCase and snake_case
by normalizing keys in `to_internal_value`. Phone is normalized to 10 digits,
monthlyBill string ranges like "$200-$300" are parsed to a Decimal, and the
sourceType / niche choices are validated explicitly.
"""

import re
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from apps.leads.models import Lead, Niche

ALLOWED_SOURCE_TYPES = {'SOLAR', 'SWEEPSTAKES'}
ALLOWED_NICHES = {value for value, _ in Niche.choices}

_CAMEL_RE = re.compile(r'(?<!^)(?=[A-Z])')


def _camel_to_snake(name):
    return _CAMEL_RE.sub('_', name).lower()


def _coerce_monthly_bill(value):
    """Accept '$200', '$200-$300', '200.50', 200, etc. Return Decimal or None."""
    if value in (None, ''):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    s = str(value)
    digits = ''
    out = []
    for ch in s + ' ':
        if ch.isdigit() or ch == '.':
            digits += ch
        elif digits:
            out.append(digits)
            digits = ''
    if not out:
        return None
    try:
        return Decimal(out[0])
    except InvalidOperation:
        return None


class LeadIngestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = (
            'source_type', 'niche', 'campaign_id', 'ad_set_id', 'source_page',
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'state', 'zip_code', 'country', 'date_of_birth',
            'is_homeowner', 'monthly_bill', 'credit_score',
            'roof_type', 'roof_age', 'solar_timeline',
            'annual_income', 'currently_insured', 'vehicle_make', 'vehicle_year',
            'total_debt',
            'ip_address', 'user_agent', 'trusted_form_cert_url',
            'tcpa_consent_text', 'tcpa_consent_at',
        )
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
            'niche': {'required': True},
            'source_type': {'required': True, 'allow_blank': False},
        }

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = {_camel_to_snake(k): v for k, v in data.items()}
            if 'monthly_bill' in data:
                data['monthly_bill'] = _coerce_monthly_bill(data['monthly_bill'])
        return super().to_internal_value(data)

    def validate_source_type(self, value):
        v = (value or '').strip().upper()
        if v not in ALLOWED_SOURCE_TYPES:
            raise serializers.ValidationError(
                f"sourceType must be one of: {sorted(ALLOWED_SOURCE_TYPES)}"
            )
        return v

    def validate_niche(self, value):
        if value not in ALLOWED_NICHES:
            raise serializers.ValidationError(
                f"niche must be one of: {sorted(ALLOWED_NICHES)}"
            )
        return value

    def validate_phone(self, value):
        if not value:
            return ''
        digits = re.sub(r'\D+', '', str(value))
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        if len(digits) != 10:
            raise serializers.ValidationError(
                'phone must contain 10 digits after stripping non-digits.'
            )
        return digits

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError(
                'At least one of email or phone is required.'
            )
        return attrs
