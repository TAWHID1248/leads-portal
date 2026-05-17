"""Lead quality scoring (1-10).

Score starts at 0; we add points for signals of intent and disqualifier-freeness.
Capped at 10 so the value fits in the existing PositiveIntegerField semantics.
"""

DISPOSABLE_EMAIL_DOMAINS = {
    'mailinator.com', 'tempmail.com', 'guerrillamail.com', '10minutemail.com',
    'throwaway.email', 'yopmail.com', 'trashmail.com', 'sharklasers.com',
    'getnada.com', 'maildrop.cc',
}

GOOD_CREDIT_TOKENS = {'good', 'excellent', '720+', '700+', '740+', '750+', '800+'}
URGENT_TIMELINE_TOKENS = {'immediately', 'asap', 'urgent', '0-3 months', 'this month',
                          'next month', 'soon', '1-3 months', '3 months'}


def _has_value(v):
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    return True


def _parse_monthly_bill(value):
    """Accept numeric, '$200', '$200-$300', etc. Return min dollar amount as int, or None."""
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value)
    digits = ''
    out = []
    for ch in s:
        if ch.isdigit():
            digits += ch
        elif digits:
            out.append(int(digits))
            digits = ''
    if digits:
        out.append(int(digits))
    return out[0] if out else None


def _age_from_dob(dob):
    if not dob:
        return None
    try:
        from datetime import date
        if isinstance(dob, str):
            from datetime import datetime
            dob = datetime.fromisoformat(dob).date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return None


def calculate(data: dict) -> int:
    score = 0

    core_fields = ('first_name', 'last_name', 'email', 'phone', 'state')
    if all(_has_value(data.get(f)) for f in core_fields):
        score += 2

    email = (data.get('email') or '').strip().lower()
    if '@' in email:
        domain = email.split('@', 1)[1]
        if domain and domain not in DISPOSABLE_EMAIL_DOMAINS:
            score += 1

    if data.get('is_homeowner') is True:
        score += 1

    bill_min = _parse_monthly_bill(data.get('monthly_bill'))
    if bill_min is not None and bill_min >= 200:
        score += 2

    credit = (data.get('credit_score') or '').strip().lower()
    if credit and any(tok in credit for tok in GOOD_CREDIT_TOKENS):
        score += 1

    timeline = (data.get('solar_timeline') or '').strip().lower()
    if timeline and any(tok in timeline for tok in URGENT_TIMELINE_TOKENS):
        score += 1

    if _has_value(data.get('trusted_form_cert_url')):
        score += 1

    age = _age_from_dob(data.get('date_of_birth'))
    if age is not None and 30 <= age <= 65:
        score += 1

    return min(score, 10)
