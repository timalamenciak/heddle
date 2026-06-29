import uuid

from django.conf import settings
from django.db import models

from core.models import Continent


class EventType(models.TextChoices):
    WORKSHOP = "workshop", "Workshop"
    HACKATHON = "hackathon", "Hackathon"
    CONFERENCE = "conference", "Conference"
    WEBINAR = "webinar", "Webinar"
    OTHER = "other", "Other"


class ParticipationRole(models.TextChoices):
    ATTENDEE = "attendee", "Attendee"
    SPEAKER = "speaker", "Speaker"
    ORGANIZER_ROLE = "organizer", "Organizer"
    FACILITATOR = "facilitator", "Facilitator"
    REVIEWER = "reviewer", "Reviewer"
    PANELIST = "panelist", "Panelist"
    OBSERVER = "observer", "Observer"


class ParticipationStatus(models.TextChoices):
    INVITED = "invited", "Invited"
    CONFIRMED = "confirmed", "Confirmed"
    DECLINED = "declined", "Declined"
    WAITLISTED = "waitlisted", "Waitlisted"
    ATTENDED = "attended", "Attended"
    NO_SHOW = "no_show", "No-show"
    CANCELLED = "cancelled", "Cancelled"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.OTHER)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2, blank=True)
    continent = models.CharField(max_length=20, blank=True, choices=Continent.choices)
    website = models.URLField(blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "event"
        verbose_name_plural = "events"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="event_end_not_before_start",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sessions")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_dt = models.DateTimeField(null=True, blank=True)
    end_dt = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_dt", "name"]
        verbose_name = "session"
        verbose_name_plural = "sessions"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_dt__isnull=True)
                | models.Q(start_dt__isnull=True)
                | models.Q(end_dt__gte=models.F("start_dt")),
                name="session_end_not_before_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.event.name} — {self.name}"


class Participation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        "core.Person", on_delete=models.CASCADE, related_name="participations"
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participations")
    role = models.CharField(
        max_length=20, choices=ParticipationRole.choices, default=ParticipationRole.ATTENDEE
    )
    status = models.CharField(
        max_length=20, choices=ParticipationStatus.choices, default=ParticipationStatus.INVITED
    )
    session = models.ForeignKey(
        Session,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="participations",
    )
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_participations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["person__family_name", "person__given_name"]
        verbose_name = "participation"
        verbose_name_plural = "participations"
        constraints = [
            models.UniqueConstraint(fields=["person", "event"], name="unique_person_event")
        ]

    def __str__(self) -> str:
        return f"{self.person} @ {self.event} [{self.status}]"


class SavedSegment(models.Model):
    """A named, reusable filter set for building invite lists."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    filters = models.JSONField(
        default=dict,
        help_text="JSON dict of filter criteria applied to the Person table.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="saved_segments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "saved segment"
        verbose_name_plural = "saved segments"

    def __str__(self) -> str:
        return self.name
