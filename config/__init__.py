"""Ensure Celery is imported when Django boots, so @shared_task picks it up."""

from .celery import app as celery_app

__all__ = ('celery_app',)
