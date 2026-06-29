from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import Role, User

_ADMIN_FIELDSETS = (
    (None, {"fields": ("id", "email", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name")}),
    ("Permissions", {"fields": ("role", "is_active")}),
    ("Important dates", {"fields": ("last_login", "date_joined")}),
)

_SUPERADMIN_FIELDSETS = (
    (None, {"fields": ("id", "email", "password")}),
    ("Personal info", {"fields": ("first_name", "last_name")}),
    (
        "Permissions",
        {"fields": ("role", "is_active", "is_superuser", "groups", "user_permissions")},
    ),
    ("Important dates", {"fields": ("last_login", "date_joined")}),
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ("email", "full_name", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("id", "date_joined", "last_login")
    filter_horizontal = ("groups", "user_permissions")

    # Override AbstractUser defaults; our model has no username field
    fieldsets = _SUPERADMIN_FIELDSETS  # type: ignore[assignment]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "is_active"),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # Add form — same fields for all staff roles
            return self.add_fieldsets
        if not request.user.is_superuser:
            return _ADMIN_FIELDSETS
        return _SUPERADMIN_FIELDSETS

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        # Prevent non-superadmins from granting the SUPERADMIN role.
        if not request.user.is_superuser and obj.role == Role.SUPERADMIN:
            obj.role = Role.ADMIN
        super().save_model(request, obj, form, change)
