from django.apps import AppConfig


class SuperAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portals.super_admin'
    label = 'portals_super_admin'
    verbose_name = 'Super Admin Portal'
