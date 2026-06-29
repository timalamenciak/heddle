import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="EnrichmentLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("crossref", "Crossref"),
                            ("openalex", "OpenAlex"),
                            ("wikidata", "Wikidata"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("person", "Person"),
                            ("organization", "Organization"),
                            ("publication", "Publication"),
                        ],
                        max_length=20,
                    ),
                ),
                ("target_id", models.UUIDField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "OK"),
                            ("error", "Error"),
                            ("skipped", "Skipped"),
                        ],
                        max_length=20,
                    ),
                ),
                ("http_status", models.IntegerField(blank=True, null=True)),
                ("suggestions_created", models.IntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("fetched_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "enrichment log",
                "verbose_name_plural": "enrichment logs",
                "ordering": ["-fetched_at"],
            },
        ),
    ]
