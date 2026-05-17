from decimal import Decimal, InvalidOperation

from django import template
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.safestring import mark_safe

register = template.Library()


NICHE_COLORS = {
    'solar-usa': ('#FFEFD5', '#92400E'),
    'solar-uk':  ('#FEF3C7', '#92400E'),
    'solar-ca':  ('#FDE68A', '#92400E'),
    'solar-au':  ('#FCD34D', '#78350F'),
    'sweeps-auto':     ('#DBEAFE', '#1E3A8A'),
    'sweeps-health':   ('#D1FAE5', '#065F46'),
    'sweeps-medicare': ('#CFFAFE', '#155E75'),
    'sweeps-home':     ('#E0E7FF', '#3730A3'),
    'sweeps-life':     ('#FCE7F3', '#9D174D'),
    'sweeps-debt':     ('#FEE2E2', '#991B1B'),
    'sweeps-generic':  ('#E5E7EB', '#374151'),
}

STATUS_COLORS = {
    'NEW':       ('#E0E7FF', '#3730A3'),
    'AVAILABLE': ('#DBEAFE', '#1E3A8A'),
    'ALLOCATED': ('#D1FAE5', '#065F46'),
    'SOLD':      ('#BBF7D0', '#14532D'),
    'REPLACED':  ('#FEF3C7', '#92400E'),
    'DUPLICATE': ('#E5E7EB', '#374151'),
    'REJECTED':  ('#FEE2E2', '#991B1B'),
}


def _badge(label, colors):
    bg, fg = colors
    return mark_safe(
        f'<span class="badge rounded-pill" '
        f'style="background:{bg};color:{fg};font-weight:600;padding:0.35em 0.7em;">{label}</span>'
    )


@register.simple_tag
def niche_badge(niche):
    if not niche:
        return ''
    colors = NICHE_COLORS.get(niche, ('#E5E7EB', '#374151'))
    return _badge(niche, colors)


@register.simple_tag
def status_badge(status):
    if not status:
        return ''
    colors = STATUS_COLORS.get(status, ('#E5E7EB', '#374151'))
    return _badge(status.title(), colors)


@register.simple_tag
def quality_badge(score):
    try:
        s = int(score)
    except (TypeError, ValueError):
        return ''
    if s >= 8:
        colors = ('#D1FAE5', '#065F46')
    elif s >= 5:
        colors = ('#FEF3C7', '#92400E')
    else:
        colors = ('#FEE2E2', '#991B1B')
    return _badge(str(s), colors)


@register.filter
def time_ago(value):
    if not value:
        return ''
    return naturaltime(value)


@register.filter
def get_item(obj, key):
    """Dict / OrderedDict lookup that's safe in templates."""
    if obj is None:
        return ''
    try:
        return obj.get(key, '')
    except AttributeError:
        try:
            return obj[key]
        except (KeyError, TypeError, IndexError):
            return ''


@register.filter
def money(value):
    if value is None or value == '':
        return ''
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return ''
    sign = '-' if d < 0 else ''
    d = abs(d)
    return f'{sign}${d:,.2f}'
