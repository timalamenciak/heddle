from django.contrib import admin

from .models import (
    MetadataCheck,
    MetadataFreshnessRule,
    MetadataIssue,
    MetadataSuggestion,
    MetadataVerification,
)


@admin.register(MetadataCheck)
class MetadataCheckAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "target", "severity", "weight", "is_enabled"]
    list_filter = ["target", "severity", "is_enabled"]
    search_fields = ["code", "name"]
    list_editable = ["weight", "is_enabled"]


@admin.register(MetadataFreshnessRule)
class MetadataFreshnessRuleAdmin(admin.ModelAdmin):
    list_display = ["metadata_check", "max_age_days"]


@admin.register(MetadataIssue)
class MetadataIssueAdmin(admin.ModelAdmin):
    list_display = [
        "metadata_check",
        "person",
        "organization",
        "status",
        "created_at",
        "resolved_at",
    ]
    list_filter = ["status", "metadata_check__severity", "metadata_check__target"]
    search_fields = ["person__given_name", "person__family_name", "organization__name"]
    readonly_fields = ["created_at", "resolved_at", "resolved_by", "ignored_at", "ignored_by"]
    raw_id_fields = ["person", "organization"]


@admin.register(MetadataVerification)
class MetadataVerificationAdmin(admin.ModelAdmin):
    list_display = ["person", "organization", "verified_by", "verified_at"]
    readonly_fields = ["created_at"]


@admin.register(MetadataSuggestion)
class MetadataSuggestionAdmin(admin.ModelAdmin):
    list_display = [
        "person",
        "organization",
        "field_name",
        "current_value",
        "suggested_value",
        "source",
        "confidence_score",
        "status",
        "created_at",
    ]
    list_filter = ["status", "source", "field_name"]
    search_fields = ["person__given_name", "person__family_name", "field_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["person", "organization"]
