"""Seed MetadataCheck entries for ORCID sync checks."""

from django.db import migrations

ORCID_CHECKS = [
    {
        "code": "person_orcid_sync_stale",
        "name": "ORCID record not recently synced",
        "description": (
            "Person has an ORCID iD but it has not been synced with the ORCID registry "
            "within the freshness threshold."
        ),
        "severity": "warning",
        "weight": 10.0,
        "target": "person",
        "freshness_days": 90,
    },
    {
        "code": "person_orcid_name_divergence",
        "name": "Name differs from ORCID record",
        "description": (
            "The name stored in heddle does not match the name on the ORCID public record."
        ),
        "severity": "warning",
        "weight": 10.0,
        "target": "person",
    },
]


def seed_orcid_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataFreshnessRule = apps.get_model("metadata", "MetadataFreshnessRule")

    for raw in ORCID_CHECKS:
        spec = dict(raw)
        freshness_days = spec.pop("freshness_days", None)
        mc, _ = MetadataCheck.objects.update_or_create(
            code=spec["code"],
            defaults={k: v for k, v in spec.items() if k != "code"},
        )
        if freshness_days is not None:
            MetadataFreshnessRule.objects.update_or_create(
                metadata_check=mc, defaults={"max_age_days": freshness_days}
            )


def unseed_orcid_checks(apps, schema_editor):
    MetadataCheck = apps.get_model("metadata", "MetadataCheck")
    MetadataCheck.objects.filter(code__in=[s["code"] for s in ORCID_CHECKS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("metadata", "0003_metadatasuggestion"),
    ]

    operations = [
        migrations.RunPython(seed_orcid_checks, unseed_orcid_checks),
    ]
