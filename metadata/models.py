import uuid

from django.conf import settings
from django.db import models


class Severity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class IssueStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    IGNORED = "ignored", "Ignored"


class CheckTarget(models.TextChoices):
    PERSON = "person", "Person"
    ORGANIZATION = "organization", "Organization"
    PUBLICATION = "publication", "Publication"


class MetadataCheck(models.Model):
    """Defines one type of quality check (a rubric entry)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    weight = models.FloatField(
        default=5.0,
        help_text="Points deducted from quality score (0–100) per open issue.",
    )
    target = models.CharField(max_length=20, choices=CheckTarget.choices)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["target", "severity", "code"]
        verbose_name = "metadata check"
        verbose_name_plural = "metadata checks"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight__gte=0) & models.Q(weight__lte=100),
                name="metadata_check_weight_0_100",
            )
        ]

    def __str__(self) -> str:
        return f"[{self.target}] {self.name}"


class MetadataIssue(models.Model):
    """A specific instance of a check failing on a person or organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata_check = models.ForeignKey(
        MetadataCheck, on_delete=models.PROTECT, related_name="issues"
    )
    person = models.ForeignKey(
        "core.Person",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="metadata_issues",
    )
    organization = models.ForeignKey(
        "core.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="metadata_issues",
    )
    publication = models.ForeignKey(
        "core.Publication",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="metadata_issues",
    )
    status = models.CharField(
        max_length=20, choices=IssueStatus.choices, default=IssueStatus.OPEN, db_index=True
    )
    detail = models.TextField(
        blank=True, help_text="Human-readable explanation of why this was flagged."
    )
    suggested_fix = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_issues",
    )
    ignored_at = models.DateTimeField(null=True, blank=True)
    ignored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ignored_issues",
    )
    ignore_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "metadata issue"
        verbose_name_plural = "metadata issues"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        person__isnull=False, organization__isnull=True, publication__isnull=True
                    )
                    | models.Q(
                        person__isnull=True, organization__isnull=False, publication__isnull=True
                    )
                    | models.Q(
                        person__isnull=True, organization__isnull=True, publication__isnull=False
                    )
                ),
                name="metadata_issue_exactly_one_target",
            )
        ]

    def __str__(self) -> str:
        target = self.person or self.organization or "unknown"
        return f"{self.metadata_check.code} on {target} [{self.status}]"


class MetadataVerification(models.Model):
    """Records a human verification event for a person or organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        "core.Person",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    organization = models.ForeignKey(
        "core.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verifications_performed",
    )
    verified_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-verified_at"]
        verbose_name = "metadata verification"
        verbose_name_plural = "metadata verifications"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(person__isnull=False, organization__isnull=True)
                    | models.Q(person__isnull=True, organization__isnull=False)
                ),
                name="metadata_verification_exactly_one_target",
            )
        ]

    def __str__(self) -> str:
        target = self.person or self.organization or "unknown"
        return f"Verified {target} at {self.verified_at}"


class SuggestionStatus(models.TextChoices):
    OPEN = "open", "Open"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class MetadataSuggestion(models.Model):
    """A suggested field change derived from ORCID sync or import. Never auto-applied."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        "core.Person",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )
    organization = models.ForeignKey(
        "core.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )
    publication = models.ForeignKey(
        "core.Publication",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )
    field_name = models.CharField(max_length=100)
    current_value = models.TextField(blank=True)
    suggested_value = models.TextField()
    source = models.CharField(max_length=100, default="orcid_sync")
    confidence_score = models.FloatField(
        default=1.0, help_text="0.0–1.0 confidence in this suggestion."
    )
    status = models.CharField(
        max_length=20,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.OPEN,
        db_index=True,
    )
    detail = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_suggestions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "metadata suggestion"
        verbose_name_plural = "metadata suggestions"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence_score__gte=0) & models.Q(confidence_score__lte=1),
                name="metadata_suggestion_confidence_0_1",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        person__isnull=False, organization__isnull=True, publication__isnull=True
                    )
                    | models.Q(
                        person__isnull=True, organization__isnull=False, publication__isnull=True
                    )
                    | models.Q(
                        person__isnull=True, organization__isnull=True, publication__isnull=False
                    )
                ),
                name="metadata_suggestion_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        target = self.person or self.organization or "unknown"
        return f"Suggest {self.field_name}={self.suggested_value!r} for {target}"


class MetadataFreshnessRule(models.Model):
    """Tunable staleness threshold for freshness-based checks."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata_check = models.OneToOneField(
        MetadataCheck,
        on_delete=models.CASCADE,
        related_name="freshness_rule",
    )
    max_age_days = models.PositiveIntegerField(
        default=365,
        help_text="Flag the record stale if not updated within this many days.",
    )

    class Meta:
        verbose_name = "freshness rule"
        verbose_name_plural = "freshness rules"

    def __str__(self) -> str:
        return f"{self.metadata_check.code}: {self.max_age_days} days"
