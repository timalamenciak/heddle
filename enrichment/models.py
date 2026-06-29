import uuid

from django.db import models


class EnrichmentSource(models.TextChoices):
    CROSSREF = "crossref", "Crossref"
    OPENALEX = "openalex", "OpenAlex"
    WIKIDATA = "wikidata", "Wikidata"


class EnrichmentStatus(models.TextChoices):
    OK = "ok", "OK"
    ERROR = "error", "Error"
    SKIPPED = "skipped", "Skipped"


class TargetType(models.TextChoices):
    PERSON = "person", "Person"
    ORGANIZATION = "organization", "Organization"
    PUBLICATION = "publication", "Publication"


class EnrichmentLog(models.Model):
    """One record per enrichment fetch attempt — whether it succeeded, failed, or was skipped."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=20, choices=EnrichmentSource.choices)
    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.UUIDField()
    status = models.CharField(max_length=20, choices=EnrichmentStatus.choices)
    http_status = models.IntegerField(null=True, blank=True)
    suggestions_created = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]
        verbose_name = "enrichment log"
        verbose_name_plural = "enrichment logs"

    def __str__(self) -> str:
        return f"{self.source} → {self.target_type}/{self.target_id} [{self.status}]"
