"""Export leads to CSV. For Phase 1 we return raw bytes; the caller wraps
that in an HttpResponse with the appropriate Content-Disposition header.
"""

import csv
import io

EXPORT_FIELDS = [
    'id', 'created_at', 'updated_at',
    'source_type', 'niche', 'campaign_id', 'ad_set_id', 'source_page',
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'first_name', 'last_name', 'email', 'phone',
    'address', 'city', 'state', 'zip_code', 'country', 'date_of_birth',
    'is_homeowner', 'monthly_bill', 'credit_score',
    'roof_type', 'roof_age', 'solar_timeline',
    'annual_income', 'currently_insured', 'vehicle_make', 'vehicle_year',
    'total_debt',
    'quality_score',
    'ip_address', 'user_agent', 'trusted_form_cert_url',
    'tcpa_consent_text', 'tcpa_consent_at',
    'is_duplicate', 'duplicate_of_id', 'is_on_dnc', 'dnc_checked_at',
    'status', 'sold_at', 'sold_price',
    'sweepstakes_id',
]


def export_leads_to_csv(queryset) -> bytes:
    """Render a queryset of Lead rows to CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_FIELDS)

    for row in queryset.values_list(*EXPORT_FIELDS).iterator(chunk_size=500):
        writer.writerow(['' if v is None else str(v) for v in row])

    return buf.getvalue().encode('utf-8')
