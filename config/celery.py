"""Celery application bootstrap.

Worker startup (prod):
    celery -A config worker -l info
    celery -A config beat -l info     # if periodic tasks are configured

In dev we typically run with CELERY_TASK_ALWAYS_EAGER=true so tasks fire
synchronously in the request thread — no broker required.
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('leadportal')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
