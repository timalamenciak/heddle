import uuid

from django.db import models


class ImportSession(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        MAPPED = "mapped", "Mapped"
        PREVIEWED = "previewed", "Previewed"
        APPLIED = "applied", "Applied"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    raw_csv = models.TextField()
    file_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    original_filename = models.CharField(max_length=255, blank=True)
    column_mapping = models.JSONField(default=dict)
    preview_data = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_sessions",
    )
    source_label = models.CharField(max_length=100, blank=True)
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "import session"
        verbose_name_plural = "import sessions"

    def __str__(self) -> str:
        return f"Import {self.id} ({self.status}) — {self.row_count} rows"
