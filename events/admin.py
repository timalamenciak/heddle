from django.contrib import admin

from .models import Event, Participation, SavedSegment, Session


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "event_type", "start_date", "location", "country"]
    list_filter = ["event_type", "country"]
    search_fields = ["name", "location"]
    date_hierarchy = "start_date"


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["name", "event", "start_dt", "location"]
    list_filter = ["event"]
    search_fields = ["name", "event__name"]


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ["person", "event", "role", "status"]
    list_filter = ["event", "role", "status"]
    search_fields = ["person__given_name", "person__family_name", "event__name"]
    autocomplete_fields = ["person"]


@admin.register(SavedSegment)
class SavedSegmentAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    search_fields = ["name", "description"]
