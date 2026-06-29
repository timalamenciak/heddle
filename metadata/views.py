import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.mixins import RoleRequiredMixin
from accounts.models import Role
from audit.services import record_audit
from config.security import safe_redirect_target
from core.models import Organization, Person

from .models import (
    IssueStatus,
    MetadataIssue,
    MetadataSuggestion,
    MetadataVerification,
    SuggestionStatus,
)
from .services import compute_org_quality, compute_person_quality, run_all_checks

logger = logging.getLogger("heddle.metadata")


class MetadataDashboardView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "metadata/dashboard.html"

    def get(self, request):
        people_qs = Person.objects.all()

        # Compute top-10 worst person scores for the dashboard table
        person_scores = []
        for person in people_qs.prefetch_related("metadata_issues__metadata_check")[:200]:
            score, breakdown = compute_person_quality(person)
            open_count = sum(1 for b in breakdown)
            critical = any(b["severity"] == "critical" for b in breakdown)
            person_scores.append(
                {
                    "person": person,
                    "score": score,
                    "open_issues": open_count,
                    "has_critical": critical,
                }
            )
        person_scores.sort(key=lambda x: x["score"])

        total_people = people_qs.count()
        people_with_open = (
            MetadataIssue.objects.filter(person__isnull=False, status=IssueStatus.OPEN)
            .values("person")
            .distinct()
            .count()
        )
        critical_count = (
            MetadataIssue.objects.filter(
                person__isnull=False,
                status=IssueStatus.OPEN,
                metadata_check__severity="critical",
            )
            .values("person")
            .distinct()
            .count()
        )
        total_open_issues = MetadataIssue.objects.filter(status=IssueStatus.OPEN).count()

        return render(
            request,
            self.template_name,
            {
                "person_scores": person_scores[:50],
                "total_people": total_people,
                "people_with_open": people_with_open,
                "critical_count": critical_count,
                "total_open_issues": total_open_issues,
            },
        )


class PersonIssuesPanelView(RoleRequiredMixin, View):
    """HTMX partial: issues panel for a Person's detail page."""

    required_role = Role.VIEWER
    template_name = "metadata/person_issues_panel.html"

    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        score, breakdown = compute_person_quality(person)
        open_issues = MetadataIssue.objects.filter(
            person=person, status=IssueStatus.OPEN
        ).select_related("metadata_check")
        ignored_issues = MetadataIssue.objects.filter(
            person=person, status=IssueStatus.IGNORED
        ).select_related("metadata_check")
        return render(
            request,
            self.template_name,
            {
                "person": person,
                "score": score,
                "breakdown": breakdown,
                "open_issues": open_issues,
                "ignored_issues": ignored_issues,
                "can_act": request.user.has_min_role(Role.CONTRIBUTOR),
            },
        )


class OrgIssuesPanelView(RoleRequiredMixin, View):
    """HTMX partial: issues panel for an Organization's detail page."""

    required_role = Role.VIEWER
    template_name = "metadata/org_issues_panel.html"

    def get(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)
        score, breakdown = compute_org_quality(org)
        open_issues = MetadataIssue.objects.filter(
            organization=org, status=IssueStatus.OPEN
        ).select_related("metadata_check")
        ignored_issues = MetadataIssue.objects.filter(
            organization=org, status=IssueStatus.IGNORED
        ).select_related("metadata_check")
        return render(
            request,
            self.template_name,
            {
                "org": org,
                "score": score,
                "breakdown": breakdown,
                "open_issues": open_issues,
                "ignored_issues": ignored_issues,
                "can_act": request.user.has_min_role(Role.CONTRIBUTOR),
            },
        )


class IssueResolveView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR

    def post(self, request, pk):
        issue = get_object_or_404(MetadataIssue, pk=pk)
        if issue.status == IssueStatus.OPEN:
            issue.status = IssueStatus.RESOLVED
            issue.resolved_at = timezone.now()
            issue.resolved_by = request.user
            issue.save(update_fields=["status", "resolved_at", "resolved_by"])
            record_audit(request, "metadata.issue.resolve", issue)
            messages.success(request, "Issue marked as resolved.")
        return redirect(safe_redirect_target(request, "/metadata/"))


class IssueIgnoreView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR

    def post(self, request, pk):
        issue = get_object_or_404(MetadataIssue, pk=pk)
        if issue.status == IssueStatus.OPEN:
            issue.status = IssueStatus.IGNORED
            issue.ignored_at = timezone.now()
            issue.ignored_by = request.user
            issue.ignore_reason = request.POST.get("reason", "")
            issue.save(update_fields=["status", "ignored_at", "ignored_by", "ignore_reason"])
            record_audit(
                request,
                "metadata.issue.ignore",
                issue,
                changes={"reason_recorded": bool(issue.ignore_reason)},
            )
            messages.success(request, "Issue ignored.")
        return redirect(safe_redirect_target(request, "/metadata/"))


class RunChecksView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR

    def post(self, request):
        counts = run_all_checks()
        record_audit(request, "metadata.checks.run", changes={"counts": counts})
        messages.success(
            request,
            f"Checks complete: {counts['people_checked']} people, "
            f"{counts['orgs_checked']} orgs, "
            f"{counts['pubs_checked']} publications. "
            f"{counts['opened']} issues opened, {counts['resolved']} resolved.",
        )
        return redirect("metadata:dashboard")


# ---------------------------------------------------------------------------
# Suggestion views
# ---------------------------------------------------------------------------

_SAFE_PERSON_FIELDS = {"given_name", "family_name", "country", "continent", "website"}
_SAFE_ORG_FIELDS = {"country", "continent", "website", "org_type", "wikidata_qid", "ror_id"}
_SAFE_PUB_FIELDS = {"title", "year", "venue", "publication_type"}


@transaction.atomic
def _accept_suggestion(suggestion: MetadataSuggestion, user) -> None:
    """Write the suggested value to the target field and record a MetadataVerification."""
    source_label = suggestion.source or "enrichment"

    if suggestion.person and suggestion.field_name in _SAFE_PERSON_FIELDS:
        setattr(suggestion.person, suggestion.field_name, suggestion.suggested_value)
        suggestion.person.full_clean()
        suggestion.person.save()
        MetadataVerification.objects.create(
            person=suggestion.person,
            verified_by=user,
            verified_at=timezone.now(),
            notes=(
                f"Accepted {source_label} suggestion: {suggestion.field_name}"
                f" = {suggestion.suggested_value!r}"
            ),
        )
    elif suggestion.organization and suggestion.field_name in _SAFE_ORG_FIELDS:
        setattr(suggestion.organization, suggestion.field_name, suggestion.suggested_value)
        suggestion.organization.full_clean()
        suggestion.organization.save()
        MetadataVerification.objects.create(
            organization=suggestion.organization,
            verified_by=user,
            verified_at=timezone.now(),
            notes=(
                f"Accepted {source_label} suggestion: {suggestion.field_name}"
                f" = {suggestion.suggested_value!r}"
            ),
        )
    elif suggestion.publication and suggestion.field_name in _SAFE_PUB_FIELDS:
        if suggestion.field_name == "year":
            try:
                suggestion.publication.year = int(suggestion.suggested_value)
            except (ValueError, TypeError) as exc:
                raise ValidationError("Suggested year is not an integer.") from exc
        else:
            setattr(suggestion.publication, suggestion.field_name, suggestion.suggested_value)
        suggestion.publication.full_clean()
        suggestion.publication.save()
    else:
        raise ValidationError("Suggestion has no supported target field.")

    suggestion.status = SuggestionStatus.ACCEPTED
    suggestion.reviewed_by = user
    suggestion.reviewed_at = timezone.now()
    suggestion.save(update_fields=["status", "reviewed_by", "reviewed_at"])


class SuggestionListView(RoleRequiredMixin, View):
    required_role = Role.CONTRIBUTOR
    template_name = "metadata/suggestion_list.html"

    def get(self, request):
        suggestions = MetadataSuggestion.objects.filter(
            status=SuggestionStatus.OPEN
        ).select_related("person", "organization", "publication", "reviewed_by")
        open_count = suggestions.count()
        high_confidence = suggestions.filter(confidence_score__gte=0.9).count()
        return render(
            request,
            self.template_name,
            {
                "suggestions": suggestions,
                "open_count": open_count,
                "high_confidence": high_confidence,
                "can_act": request.user.has_min_role(Role.ORGANIZER),
            },
        )


class SuggestionAcceptView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def post(self, request, pk):
        suggestion = get_object_or_404(MetadataSuggestion, pk=pk)
        if suggestion.status == SuggestionStatus.OPEN:
            try:
                _accept_suggestion(suggestion, request.user)
            except ValidationError:
                logger.warning("Rejected invalid metadata suggestion %s", suggestion.pk)
                messages.error(request, "This suggestion is invalid and was not applied.")
            else:
                record_audit(request, "metadata.suggestion.accept", suggestion)
                messages.success(request, f"Accepted: {suggestion.field_name} updated.")
        return redirect(safe_redirect_target(request, "/metadata/suggestions/"))


class SuggestionRejectView(RoleRequiredMixin, View):
    required_role = Role.ORGANIZER

    def post(self, request, pk):
        suggestion = get_object_or_404(MetadataSuggestion, pk=pk)
        if suggestion.status == SuggestionStatus.OPEN:
            suggestion.status = SuggestionStatus.REJECTED
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            record_audit(request, "metadata.suggestion.reject", suggestion)
            messages.success(request, "Suggestion rejected.")
        return redirect(safe_redirect_target(request, "/metadata/suggestions/"))


class SuggestionBulkAcceptView(RoleRequiredMixin, View):
    """Bulk-accept all open suggestions with confidence >= 0.9."""

    required_role = Role.ORGANIZER

    def post(self, request):
        pending = MetadataSuggestion.objects.filter(
            status=SuggestionStatus.OPEN,
            confidence_score__gte=0.9,
        ).select_related("person", "organization", "publication")
        count = 0
        failed = 0
        for sug in pending:
            try:
                _accept_suggestion(sug, request.user)
            except ValidationError:
                failed += 1
                logger.warning("Skipped invalid metadata suggestion %s", sug.pk)
            else:
                count += 1
        record_audit(
            request,
            "metadata.suggestion.bulk_accept",
            changes={"accepted": count, "skipped_invalid": failed},
        )
        messages.success(request, f"Bulk accepted {count} low-risk suggestion(s).")
        if failed:
            messages.warning(request, f"Skipped {failed} invalid suggestion(s).")
        return redirect("metadata:suggestions")
