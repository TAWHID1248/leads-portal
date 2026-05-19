"""Production settings.

Designed for Railway, but portable to any platform that injects DATABASE_URL,
REDIS_URL, ALLOWED_HOSTS, and the Stripe / SendGrid / AWS env vars.

Everything that differs from base.py is wired here; we never override the
base middleware list silently — we splice WhiteNoise in.
"""

import os

import dj_database_url
from decouple import Csv, config

from .base import *  # noqa: F401,F403


DEBUG = False

# Railway injects RAILWAY_PUBLIC_DOMAIN automatically. Also allow
# healthcheck.railway.app which Railway's internal health checker uses.
_railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
_default_hosts = ','.join(filter(None, [_railway_domain, '.railway.app']))
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=_default_hosts, cast=Csv())

# ---------- Database ----------
DATABASES = {
    'default': dj_database_url.config(
        env='DATABASE_URL',
        conn_max_age=600,
        ssl_require=True,
    ),
}

# ---------- HTTPS / proxy ----------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
# Railway's internal healthcheck hits the container directly without the
# X-Forwarded-Proto header, so SECURE_SSL_REDIRECT would 301 it. Exempt /healthz/.
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
SECURE_HSTS_SECONDS = 31536000           # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = 'same-origin'

# ---------- CSRF / CORS trusted origins ----------
# CSRF_TRUSTED_ORIGINS=https://portal.example.com,https://leads.example.com
_railway_origin = f'https://{_railway_domain}' if _railway_domain else 'https://*.railway.app'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default=_railway_origin, cast=Csv())

# ---------- Static files (WhiteNoise) ----------
# Splice WhiteNoise immediately after SecurityMiddleware so it can serve
# compressed manifests on every request without touching auth/session.
MIDDLEWARE = list(MIDDLEWARE)
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    sec_idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(sec_idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')

USE_S3 = config('USE_S3', default=False, cast=bool)

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'private'                  # private bucket policy
    AWS_QUERYSTRING_AUTH = True                  # forces presigned URLs
    AWS_QUERYSTRING_EXPIRE = 60 * 15             # 15-minute presigned links
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_S3_SIGNATURE_VERSION = 's3v4'

    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
    }

# Older STATICFILES_STORAGE setting kept for tools that still read it.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------- Caches ----------
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        },
    }

# ---------- Celery ----------
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=REDIS_URL or '')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='')
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ---------- Logging (Railway captures stdout) ----------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[{asctime}] {levelname} {name} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# ---------- Portal base URL (used in emails) ----------
PORTAL_BASE_URL = config('PORTAL_BASE_URL', default='')
