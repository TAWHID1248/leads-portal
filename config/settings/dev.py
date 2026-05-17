from .base import *
import dj_database_url

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
    )
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Run Celery tasks inline in dev so we don't need a running broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
