from django.http import HttpResponseForbidden
from django.shortcuts import redirect


PORTAL_ACCESS = {
    'super': {'SUPER_ADMIN'},
    'admin': {'SUPER_ADMIN', 'ADMIN'},
    'agent': {'SUPER_ADMIN', 'ADMIN', 'AGENT'},
    'client': {'CLIENT'},
}

ROLE_DASHBOARD = {
    'SUPER_ADMIN': '/super/dashboard/',
    'ADMIN': '/admin/dashboard/',
    'AGENT': '/agent/dashboard/',
    'CLIENT': '/client/dashboard/',
}


class RoleRedirectMiddleware:
    """Redirect authenticated users from / to their role's dashboard, and
    forbid users from accessing portal sections that don't match their role."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path

            if path == '/':
                target = ROLE_DASHBOARD.get(getattr(request.user, 'role', None))
                if target:
                    return redirect(target)

            first_segment = path.strip('/').split('/', 1)[0] if path.strip('/') else ''
            allowed_roles = PORTAL_ACCESS.get(first_segment)
            if allowed_roles is not None and request.user.role not in allowed_roles:
                return HttpResponseForbidden(
                    'You do not have permission to access this portal.'
                )

        return self.get_response(request)
