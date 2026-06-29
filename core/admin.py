from django.contrib import admin

from .models import (
    Affiliation,
    Authorship,
    Collaboration,
    ExpertiseTerm,
    ORCIDProfile,
    ORCIDWork,
    Organization,
    Person,
    PersonExpertise,
    Publication,
)


class AffiliationInline(admin.TabularInline):
    model = Affiliation
    extra = 0
    fields = ("organization", "role", "is_primary", "start_date", "end_date")


class PersonExpertiseInline(admin.TabularInline):
    model = PersonExpertise
    extra = 0
    fields = ("term", "source")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "orcid",
        "country",
        "metadata_status",
        "consent_contact",
        "source",
    )
    list_filter = ("metadata_status", "consent_contact", "continent", "country")
    search_fields = ("given_name", "family_name", "email", "orcid")
    readonly_fields = ("id", "name_normalized", "created_at", "updated_at")
    inlines = [AffiliationInline, PersonExpertiseInline]
    fieldsets = (
        (None, {"fields": ("id", "given_name", "family_name", "name_normalized")}),
        ("Contact", {"fields": ("email", "orcid", "website")}),
        ("Location", {"fields": ("country", "continent")}),
        (
            "Consent",
            {"fields": ("consent_contact", "consent_public_profile")},
        ),
        (
            "Metadata",
            {
                "fields": (
                    "metadata_status",
                    "metadata_last_checked_at",
                    "metadata_last_verified_at",
                    "verified_by",
                    "source",
                )
            },
        ),
        ("Notes", {"fields": ("notes", "notes_private")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "org_type", "metadata_status", "source")
    list_filter = ("org_type", "metadata_status", "continent")
    search_fields = ("name", "ror_id")
    readonly_fields = ("id", "name_normalized", "created_at", "updated_at")


@admin.register(ExpertiseTerm)
class ExpertiseTermAdmin(admin.ModelAdmin):
    list_display = ("term", "source_vocabulary", "external_id")
    list_filter = ("source_vocabulary",)
    search_fields = ("term", "external_id")
    readonly_fields = ("id", "created_at")


@admin.register(PersonExpertise)
class PersonExpertiseAdmin(admin.ModelAdmin):
    list_display = ("person", "term", "source")
    search_fields = ("person__given_name", "person__family_name", "term__term")
    readonly_fields = ("id", "created_at")


@admin.register(ORCIDProfile)
class ORCIDProfileAdmin(admin.ModelAdmin):
    list_display = ("person", "fetched_at", "given_name_remote", "family_name_remote")
    search_fields = ("person__given_name", "person__family_name")
    readonly_fields = ("id", "created_at", "updated_at", "raw_record")


@admin.register(ORCIDWork)
class ORCIDWorkAdmin(admin.ModelAdmin):
    list_display = ("person", "title", "work_type", "publication_year", "doi", "put_code")
    search_fields = ("person__given_name", "person__family_name", "title", "doi")
    readonly_fields = ("id", "created_at", "updated_at", "raw_work")


class AuthorshipInline(admin.TabularInline):
    model = Authorship
    extra = 0
    fields = ("person", "author_name", "position", "source")
    raw_id_fields = ("person",)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "doi", "publication_type", "source", "is_reviewed")
    list_filter = ("source", "is_reviewed", "publication_type")
    search_fields = ("title", "doi")
    readonly_fields = ("id", "title_normalized", "doi_normalized", "created_at", "updated_at")
    list_editable = ("is_reviewed",)
    inlines = [AuthorshipInline]


@admin.register(Collaboration)
class CollaborationAdmin(admin.ModelAdmin):
    list_display = ("person_a", "person_b", "publication_count", "first_year", "last_year")
    search_fields = (
        "person_a__given_name",
        "person_a__family_name",
        "person_b__given_name",
        "person_b__family_name",
    )
    raw_id_fields = ("person_a", "person_b")
