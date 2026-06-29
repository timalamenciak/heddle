"""Seed MetadataCheck records for Phase 5 publication quality checks."""

from django.db import migrations


def seed_publication_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataFreshnessRule = apps.get_model("metadata", "MetadataFreshnessRule")

    checks = [
        {
            "code": "pub_missing_doi",
            "name": "Missing DOI",
            "description": "Publication has no DOI recorded.",
            "severity": "warning",
            "weight": 5.0,
            "target": "publication",
        },
        {
            "code": "pub_invalid_doi",
            "name": "Invalid DOI format",
            "description": "DOI does not match the 10.XXXX/... format.",
            "severity": "warning",
            "weight": 8.0,
            "target": "publication",
        },
        {
            "code": "pub_duplicate_doi",
            "name": "Duplicate DOI",
            "description": "Another publication record shares the same DOI.",
            "severity": "critical",
            "weight": 20.0,
            "target": "publication",
        },
        {
            "code": "pub_unlinked_authors",
            "name": "Unlinked authors",
            "description": "One or more authors are not linked to a Person record.",
            "severity": "info",
            "weight": 3.0,
            "target": "publication",
        },
        {
            "code": "pub_unreviewed_import",
            "name": "Unreviewed ORCID import",
            "description": "Publication was imported from ORCID and has not been reviewed within the freshness window.",
            "severity": "info",
            "weight": 3.0,
            "target": "publication",
        },
    ]

    for data in checks:
        mc, _ = MetadataCheck.objects.update_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "description": data["description"],
                "severity": data["severity"],
                "weight": data["weight"],
                "target": data["target"],
                "is_enabled": True,
            },
        )
        if data["code"] == "pub_unreviewed_import":
            MetadataFreshnessRule.objects.get_or_create(
                metadata_check=mc,
                defaults={"max_age_days": 365},
            )


def remove_publication_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataCheck.objects.filter(
        code__in=[
            "pub_missing_doi",
            "pub_invalid_doi",
            "pub_duplicate_doi",
            "pub_unlinked_authors",
            "pub_unreviewed_import",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0005_publication_issue_field"),
    ]

    operations = [
        migrations.RunPython(seed_publication_checks, remove_publication_checks),
    ]
