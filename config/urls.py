from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path

from apps.accounts.models import User
from apps.core.views import healthz


def home_view(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    role_map = {
        'SUPER_ADMIN': '/super/dashboard/',
        'ADMIN': '/admin/dashboard/',
        'AGENT': '/agent/dashboard/',
        'CLIENT': '/client/dashboard/',
    }
    return redirect(role_map.get(request.user.role, '/login/'))


urlpatterns = [
    path('', home_view, name='home'),
    path('healthz/', healthz, name='healthz'),
    path('django-admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('super/', include('apps.portals.super_admin.urls')),
    path('admin/', include('apps.portals.admin_portal.urls')),
    path('agent/', include('apps.portals.agent.urls')),
    path('client/', include('apps.portals.client.urls')),
    path('api/v1/', include('apps.leads.api.urls')),
    path('api/', include('apps.notifications.urls')),
    path('', include('apps.billing.urls')),
]

handler404 = 'apps.core.views.not_found_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
