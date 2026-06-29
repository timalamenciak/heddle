"""Seed MetadataCheck definitions and MetadataFreshnessRule thresholds."""

from django.db import migrations

CHECKS = [
    # Person checks
    {
        "code": "person_missing_orcid",
        "name": "Missing ORCID",
        "description": "Person has no ORCID iD recorded.",
        "severity": "warning",
        "weight": 15.0,
        "target": "person",
    },
    {
        "code": "person_invalid_orcid",
        "name": "ORCID format issue",
        "description": "Person has an ORCID value that does not match the standard format.",
        "severity": "warning",
        "weight": 15.0,
        "target": "person",
    },
    {
        "code": "person_missing_email",
        "name": "No email recorded",
        "description": "Person has no email address on file.",
        "severity": "info",
        "weight": 5.0,
        "target": "person",
    },
    {
        "code": "person_missing_country",
        "name": "Country not set",
        "description": "Person's country of affiliation is not recorded.",
        "severity": "info",
        "weight": 5.0,
        "target": "person",
    },
    {
        "code": "person_missing_continent",
        "name": "Continent not set",
        "description": "Person has a country but no continent derived from it.",
        "severity": "info",
        "weight": 3.0,
        "target": "person",
    },
    {
        "code": "person_missing_org",
        "name": "No organization linked",
        "description": "Person has no affiliation recorded.",
        "severity": "warning",
        "weight": 10.0,
        "target": "person",
    },
    {
        "code": "person_no_expertise",
        "name": "No expertise terms",
        "description": "Person has no expertise terms tagged.",
        "severity": "info",
        "weight": 5.0,
        "target": "person",
    },
    {
        "code": "person_no_consent",
        "name": "Contact consent not recorded",
        "description": "Person's consent to be contacted has not been recorded as given.",
        "severity": "info",
        "weight": 5.0,
        "target": "person",
    },
    {
        "code": "person_stale_profile",
        "name": "Profile not recently updated",
        "description": "Person's record has not been reviewed or updated within the freshness threshold.",
        "severity": "info",
        "weight": 10.0,
        "target": "person",
        "freshness_days": 365,
    },
    {
        "code": "person_dup_email",
        "name": "Possible duplicate — same email",
        "description": "Another person in the system shares this email address.",
        "severity": "warning",
        "weight": 20.0,
        "target": "person",
    },
    {
        "code": "person_dup_name",
        "name": "Possible duplicate — same name",
        "description": "Another person shares the same normalized name with no ORCID to distinguish them.",
        "severity": "warning",
        "weight": 15.0,
        "target": "person",
    },
    # Organization checks
    {
        "code": "org_missing_country",
        "name": "Country not set",
        "description": "Organization's country is not recorded.",
        "severity": "info",
        "weight": 5.0,
        "target": "organization",
    },
    {
        "code": "org_missing_continent",
        "name": "Continent not set",
        "description": "Organization has a country but no continent derived from it.",
        "severity": "info",
        "weight": 3.0,
        "target": "organization",
    },
    {
        "code": "org_missing_website",
        "name": "No website",
        "description": "Organization has no website recorded.",
        "severity": "info",
        "weight": 3.0,
        "target": "organization",
    },
    {
        "code": "org_missing_ror",
        "name": "No ROR ID",
        "description": "Organization has no Research Organization Registry (ROR) identifier.",
        "severity": "info",
        "weight": 3.0,
        "target": "organization",
    },
    {
        "code": "org_no_people",
        "name": "No people linked",
        "description": "Organization has no affiliated people in the system.",
        "severity": "info",
        "weight": 5.0,
        "target": "organization",
    },
    {
        "code": "org_dup_name",
        "name": "Possible duplicate — same name",
        "description": "Another organization shares the same normalized name.",
        "severity": "warning",
        "weight": 15.0,
        "target": "organization",
    },
    {
        "code": "org_stale",
        "name": "Record not recently updated",
        "description": "Organization record has not been reviewed or updated within the freshness threshold.",
        "severity": "info",
        "weight": 10.0,
        "target": "organization",
        "freshness_days": 365,
    },
]


def seed_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataFreshnessRule = apps.get_model("metadata", "MetadataFreshnessRule")

    for raw in CHECKS:
        spec = dict(raw)  # don't mutate the module-level constant
        freshness_days = spec.pop("freshness_days", None)
        mc, _ = MetadataCheck.objects.update_or_create(
            code=spec["code"],
            defaults={k: v for k, v in spec.items() if k != "code"},
        )
        if freshness_days is not None:
            MetadataFreshnessRule.objects.update_or_create(
                metadata_check=mc, defaults={"max_age_days": freshness_days}
            )


def unseed_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataCheck.objects.filter(code__in=[s["code"] for s in CHECKS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_checks, unseed_checks),
    ]
