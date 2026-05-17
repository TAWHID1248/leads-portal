from django.apps import AppConfig


class ClientPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portals.client'
    label = 'portals_client'
    verbose_name = 'Client Portal'
