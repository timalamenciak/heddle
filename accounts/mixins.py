from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import Role


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict a view to users whose role is at least `required_role`."""

    required_role: str = Role.VIEWER

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_min_role(self.required_role):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
