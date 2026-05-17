"""Helpers shared by the agent portal views."""

from datetime import timedelta

from django.http import Http404
from django.utils import timezone

from apps.agents.models import Agent


def get_agent(request):
    """Return the Agent profile for the current user, 404 if absent.

    SUPER_ADMIN / ADMIN users without an Agent profile fall back to None;
    the caller decides whether that's acceptable.
    """
    return Agent.objects.filter(user=request.user).first()


def require_agent(request):
    agent = get_agent(request)
    if agent is None:
        raise Http404('No agent profile for this user.')
    return agent


def week_bounds(now=None):
    """Return (start, end) covering the current ISO week starting Monday."""
    now = now or timezone.now()
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def month_bounds(now=None):
    now = now or timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def today_bounds(now=None):
    now = now or timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)
