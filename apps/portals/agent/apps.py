from django.apps import AppConfig


class AgentPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.portals.agent'
    label = 'portals_agent'
    verbose_name = 'Agent Portal'
