from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "object_repr", "user", "ip_address", "created_at")
    list_filter = ("action",)
    search_fields = ("object_repr", "user__email")
    readonly_fields = (
        "id",
        "user",
        "action",
        "content_type",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
