from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseForbidden


class RoleRequiredMixin(AccessMixin):
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.required_roles and request.user.role not in self.required_roles:
            return HttpResponseForbidden('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)
