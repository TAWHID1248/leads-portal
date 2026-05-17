from django.apps import AppConfig


class AdminPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portals.admin_portal'
    label = 'portals_admin_portal'
    verbose_name = 'Admin Portal'
