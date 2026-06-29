import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from core.models import Person
from events.models import Event, SavedSegment
from importer.models import ImportSession
from metadata.models import IssueStatus, MetadataIssue, Severity


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        stale_threshold = timezone.now() - datetime.timedelta(days=365)

        people_stats = Person.objects.aggregate(
            total=Count("id"),
            with_orcid=Count("id", filter=Q(orcid__isnull=False) & ~Q(orcid="")),
            consent_contact=Count("id", filter=Q(consent_contact=True)),
            consent_public=Count("id", filter=Q(consent_public_profile=True)),
            stale_syncs=Count(
                "id",
                filter=(
                    Q(orcid__isnull=False)
                    & ~Q(orcid="")
                    & (
                        Q(metadata_last_checked_at__lt=stale_threshold)
                        | Q(metadata_last_checked_at__isnull=True)
                    )
                ),
            ),
            needs_review=Count("id", filter=Q(metadata_status="needs_review")),
        )

        issue_stats = MetadataIssue.objects.filter(status=IssueStatus.OPEN).aggregate(
            total=Count("id"),
            critical=Count("id", filter=Q(metadata_check__severity=Severity.CRITICAL)),
        )

        possible_dups = (
            MetadataIssue.objects.filter(
                status=IssueStatus.OPEN,
                metadata_check__code__in=["dup_orcid", "dup_email", "dup_name"],
                person__isnull=False,
            )
            .values("person")
            .distinct()
            .count()
        )

        upcoming_events = list(
            Event.objects.filter(start_date__gte=today).order_by("start_date")[:5]
        )
        total_events = Event.objects.count()
        total_segments = SavedSegment.objects.count()

        recent_imports = list(
            ImportSession.objects.filter(status=ImportSession.Status.APPLIED).order_by(
                "-applied_at"
            )[:5]
        )

        ctx.update(
            {
                "people": people_stats,
                "issues": issue_stats,
                "possible_dups": possible_dups,
                "upcoming_events": upcoming_events,
                "total_events": total_events,
                "total_segments": total_segments,
                "recent_imports": recent_imports,
            }
        )
        return ctx
