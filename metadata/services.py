"""High-level services: run all checks, compute quality scores."""

import datetime

from django.db.models import QuerySet
from django.utils import timezone

from core.models import Organization, Person, Publication

from .checks import ORG_CHECKS, PERSON_CHECKS, PUBLICATION_CHECKS
from .models import IssueStatus, MetadataIssue


def run_checks_for_person(person: Person) -> None:
    """Run all enabled person checks against a single Person."""
    for fn in PERSON_CHECKS:
        fn(person)


def run_checks_for_organization(org: Organization) -> None:
    """Run all enabled organization checks against a single Organization."""
    for fn in ORG_CHECKS:
        fn(org)


def run_checks_for_publication(pub: Publication) -> None:
    """Run all enabled publication checks against a single Publication."""
    for fn in PUBLICATION_CHECKS:
        fn(pub)


def run_all_checks() -> dict[str, int]:
    """Run every enabled check over all Person, Organization, and Publication records."""
    opened_before = MetadataIssue.objects.filter(status=IssueStatus.OPEN).count()
    run_started = timezone.now()

    people = list(
        Person.objects.prefetch_related("affiliations", "expertise", "metadata_issues").all()
    )
    for person in people:
        run_checks_for_person(person)

    orgs = list(Organization.objects.prefetch_related("affiliations", "metadata_issues").all())
    for org in orgs:
        run_checks_for_organization(org)

    pubs = list(Publication.objects.prefetch_related("authorships", "metadata_issues").all())
    for pub in pubs:
        run_checks_for_publication(pub)

    opened_after = MetadataIssue.objects.filter(status=IssueStatus.OPEN).count()
    total_resolved = MetadataIssue.objects.filter(
        status=IssueStatus.RESOLVED,
        resolved_at__gte=run_started - datetime.timedelta(seconds=10),
    ).count()

    return {
        "people_checked": len(people),
        "orgs_checked": len(orgs),
        "pubs_checked": len(pubs),
        "opened": max(0, opened_after - opened_before),
        "resolved": total_resolved,
    }


# ---------------------------------------------------------------------------
# Quality score
# ---------------------------------------------------------------------------


QualityBreakdownItem = dict  # {"check_code", "check_name", "severity", "weight", "detail"}


def compute_person_quality(person: Person) -> tuple[int, list[QualityBreakdownItem]]:
    """Return (score 0–100, breakdown list) for a Person."""
    open_issues = MetadataIssue.objects.filter(
        person=person, status=IssueStatus.OPEN
    ).select_related("metadata_check")
    return _score_from_issues(open_issues)


def compute_publication_quality(pub: Publication) -> tuple[int, list[QualityBreakdownItem]]:
    """Return (score 0–100, breakdown list) for a Publication."""
    open_issues = MetadataIssue.objects.filter(
        publication=pub, status=IssueStatus.OPEN
    ).select_related("metadata_check")
    return _score_from_issues(open_issues)


def compute_org_quality(org: Organization) -> tuple[int, list[QualityBreakdownItem]]:
    """Return (score 0–100, breakdown list) for an Organization."""
    open_issues = MetadataIssue.objects.filter(
        organization=org, status=IssueStatus.OPEN
    ).select_related("metadata_check")
    return _score_from_issues(open_issues)


def _score_from_issues(
    open_issues: "QuerySet[MetadataIssue]",
) -> tuple[int, list[QualityBreakdownItem]]:
    breakdown = []
    total_penalty = 0.0
    for issue in open_issues:
        mc = issue.metadata_check
        total_penalty += mc.weight
        breakdown.append(
            {
                "check_code": mc.code,
                "check_name": mc.name,
                "severity": mc.severity,
                "weight": mc.weight,
                "detail": issue.detail,
                "issue_pk": str(issue.pk),
            }
        )
    score = max(0, round(100 - total_penalty))
    return score, breakdown
