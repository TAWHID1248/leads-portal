from functools import wraps
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.role not in roles:
                return HttpResponseForbidden('You do not have permission to access this page.')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


super_admin_required = role_required('SUPER_ADMIN')
admin_required = role_required('ADMIN')
agent_required = role_required('AGENT')
client_required = role_required('CLIENT')
