from django.contrib import admin

from .models import ImportSession


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "status",
        "source_label",
        "row_count",
        "created_by",
        "created_at",
        "applied_at",
    ]  # noqa: E501
    list_filter = ["status"]
    readonly_fields = [  # noqa: E501
        "id",
        "created_at",
        "applied_at",
        "created_by",
        "raw_csv",
        "column_mapping",
        "preview_data",
    ]
    search_fields = ["source_label"]
