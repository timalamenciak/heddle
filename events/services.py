"""Segment filtering, match-reason generation, and invite-list export."""

import csv
import io
import json
import zipfile
from typing import TYPE_CHECKING, Any

from django.db.models import Q, QuerySet

from config.version import __version__
from core.models import Person
from metadata.models import IssueStatus, MetadataIssue

from .models import Participation, ParticipationStatus

if TYPE_CHECKING:
    from .models import SavedSegment

_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@", "\t"})


def _escape(value: str) -> str:
    s = str(value)
    if s and s[0] in _FORMULA_PREFIXES:
        return f"'{s}"
    return s


# ---------------------------------------------------------------------------
# Segment filtering
# ---------------------------------------------------------------------------


def apply_segment_filters(filters: dict[str, Any]) -> QuerySet[Person]:
    """Return a QuerySet of Person matching all filter criteria (AND between fields,
    OR within each list-type field)."""
    qs = Person.objects.all()

    if countries := filters.get("countries"):
        qs = qs.filter(country__in=countries)

    if continents := filters.get("continents"):
        qs = qs.filter(continent__in=continents)

    if org_types := filters.get("org_types"):
        qs = qs.filter(affiliations__organization__org_type__in=org_types)

    if expertise_ids := filters.get("expertise_term_ids"):
        qs = qs.filter(expertise__term_id__in=expertise_ids)

    if free_text := (filters.get("free_text") or "").strip():
        qs = qs.filter(
            Q(given_name__icontains=free_text)
            | Q(family_name__icontains=free_text)
            | Q(notes__icontains=free_text)
            | Q(email__icontains=free_text)
        )

    if filters.get("consent_contact"):
        qs = qs.filter(consent_contact=True)

    if filters.get("consent_public_profile"):
        qs = qs.filter(consent_public_profile=True)

    if filters.get("has_orcid"):
        qs = qs.filter(orcid__isnull=False).exclude(orcid="")

    if filters.get("no_critical_issues"):
        critical_person_ids = MetadataIssue.objects.filter(
            status=IssueStatus.OPEN,
            metadata_check__severity="critical",
            person__isnull=False,
        ).values_list("person_id", flat=True)
        qs = qs.exclude(id__in=critical_person_ids)

    if event_id := filters.get("prior_participation_event_id"):
        qs = qs.filter(
            participations__event_id=event_id,
            participations__status__in=[
                ParticipationStatus.ATTENDED,
                ParticipationStatus.CONFIRMED,
            ],
        )

    if event_id := filters.get("not_invited_to_event_id"):
        already_in = Participation.objects.filter(
            event_id=event_id,
            status__in=[
                ParticipationStatus.INVITED,
                ParticipationStatus.CONFIRMED,
                ParticipationStatus.ATTENDED,
                ParticipationStatus.WAITLISTED,
            ],
        ).values_list("person_id", flat=True)
        qs = qs.exclude(id__in=already_in)

    if statuses := filters.get("metadata_status"):
        qs = qs.filter(metadata_status__in=statuses)

    return qs.distinct()


def get_match_reasons(person: Person, filters: dict[str, Any]) -> list[str]:
    """Return human-readable reasons why this person matched the segment."""
    reasons = []

    if filters.get("countries") and person.country:
        reasons.append(f"Country: {person.country}")

    if filters.get("continents") and person.continent:
        reasons.append(f"Continent: {person.continent}")

    if filters.get("consent_contact") and person.consent_contact:
        reasons.append("Contact consent recorded")

    if filters.get("consent_public_profile") and person.consent_public_profile:
        reasons.append("Public profile consent recorded")

    if filters.get("has_orcid") and person.orcid:
        reasons.append(f"Has ORCID: {person.orcid}")

    if filters.get("no_critical_issues"):
        reasons.append("No critical metadata issues")

    if ft := filters.get("free_text"):
        reasons.append(f'Matched text: "{ft}"')

    if expertise_ids := filters.get("expertise_term_ids"):
        matching = list(
            person.expertise.filter(term_id__in=expertise_ids).values_list("term__term", flat=True)
        )
        for t in matching:
            reasons.append(f"Expertise: {t}")

    if filters.get("prior_participation_event_id"):
        reasons.append("Prior event participant")

    if not reasons:
        reasons.append("Matched all criteria")

    return reasons


# ---------------------------------------------------------------------------
# Invite-list export
# ---------------------------------------------------------------------------

_INVITE_COLUMNS = [
    "person_id",
    "given_name",
    "family_name",
    "email",
    "organization",
    "country",
    "orcid",
    "consent_contact",
]

_MANIFEST_EXTRA_COLUMNS = ["match_reasons", "included_in_export", "exclusion_reason"]


def export_invite_list(segment: "SavedSegment") -> tuple[str, str]:
    """Return (invite_csv, manifest_csv).

    The invite CSV contains only included people.
    The manifest CSV contains all candidates with include/exclude disposition and reason.

    Auto-exclusion rules (applied after segment filters):
    - No contact consent → excluded
    - Open critical metadata issue → excluded
    """
    candidates = apply_segment_filters(segment.filters).prefetch_related(
        "affiliations__organization", "metadata_issues__metadata_check"
    )

    critical_ids: set = set(
        MetadataIssue.objects.filter(
            status=IssueStatus.OPEN,
            metadata_check__severity="critical",
            person__isnull=False,
        ).values_list("person_id", flat=True)
    )

    invite_rows: list[dict] = []
    manifest_rows: list[dict] = []

    for person in candidates:
        org = person.primary_organization
        base: dict = {
            "person_id": str(person.pk),
            "given_name": person.given_name,
            "family_name": person.family_name,
            "email": person.email or "",
            "organization": str(org) if org else "",
            "country": person.country,
            "orcid": person.orcid or "",
            "consent_contact": "yes" if person.consent_contact else "no",
            "match_reasons": "; ".join(get_match_reasons(person, segment.filters)),
        }

        exclusion = ""
        if not person.consent_contact:
            exclusion = "No contact consent"
        elif person.pk in critical_ids:
            exclusion = "Has open critical metadata issue"

        if not exclusion:
            invite_rows.append(base)

        manifest_rows.append(
            {
                **base,
                "included_in_export": "no" if exclusion else "yes",
                "exclusion_reason": exclusion,
            }
        )

    invite_csv = _build_csv(invite_rows, _INVITE_COLUMNS)
    manifest_csv = _build_csv(manifest_rows, _INVITE_COLUMNS + _MANIFEST_EXTRA_COLUMNS)
    return invite_csv, manifest_csv


def _build_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: _escape(row.get(col, "")) for col in columns})
    return buf.getvalue()


def build_invite_zip(segment: "SavedSegment") -> bytes:
    """Return a zip archive containing the invite CSV and the manifest CSV."""
    invite_csv, manifest_csv = export_invite_list(segment)
    slug = segment.name.replace(" ", "_")[:40]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"invite_{slug}.csv", invite_csv)
        zf.writestr(f"manifest_{slug}.csv", manifest_csv)
        zf.writestr(
            "export_metadata.json",
            json.dumps({"heddle_version": __version__, "segment_id": str(segment.pk)}),
        )
    return buf.getvalue()
