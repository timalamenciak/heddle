"""Badge-tool CSV export.

Only participants with consent_public_profile=True are included.
Email is never exported.
A manifest.json explains exclusions so the badge tool operator has audit trail.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from config.version import __version__
from events.models import Event, Participation
from metadata.services import compute_person_quality

from .kgx import _esc, node_id_person

BADGE_FIELDNAMES = [
    "person_id",
    "display_name",
    "public_label",
    "orcid",
    "organization",
    "country",
    "event_code",
    "event_name",
    "participation_role",
    "participation_status",
    "consent_public_profile",
    "qr_target_url",
    "metadata_quality_score",
    "metadata_status",
]


def build_badge_export(
    event: Event,
    *,
    generated_by: str = "system",
    include_quality_score: bool = True,
) -> tuple[str, dict]:
    """
    Return (badge_csv_string, manifest_dict) for one event.

    Rows are ordered by family_name, given_name.
    Only consent_public_profile=True participants appear in the CSV.
    """
    participations = list(
        Participation.objects.filter(event=event)
        .select_related("person", "event")
        .prefetch_related("person__affiliations__organization")
        .order_by("person__family_name", "person__given_name")
    )

    included = 0
    excluded_no_consent = 0
    excluded_no_person = 0

    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=BADGE_FIELDNAMES,
        lineterminator="\r\n",
        extrasaction="ignore",
    )
    writer.writeheader()

    for part in participations:
        person = part.person
        if person is None:
            excluded_no_person += 1
            continue
        if not person.consent_public_profile:
            excluded_no_consent += 1
            continue

        org = person.primary_organization
        quality_score = ""
        if include_quality_score:
            score, _ = compute_person_quality(person)
            quality_score = str(score)

        writer.writerow(
            {
                "person_id": _esc(node_id_person(person)),
                "display_name": _esc(person.full_name),
                "public_label": "",  # TODO(phase-N): add credential/title field to Person
                "orcid": _esc(person.orcid or ""),
                "organization": _esc(str(org) if org else ""),
                "country": _esc(person.country or ""),
                "event_code": _esc(str(event.pk)[:8]),
                "event_name": _esc(event.name),
                "participation_role": _esc(part.role),
                "participation_status": _esc(part.status),
                "consent_public_profile": "true",
                "qr_target_url": "",
                "metadata_quality_score": _esc(quality_score),
                "metadata_status": _esc(person.metadata_status),
            }
        )
        included += 1

    manifest = {
        "heddle_version": __version__,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "generated_by": generated_by,
        "event_id": str(event.pk),
        "event_name": event.name,
        "tool": "heddle-badge-export v1.0",
        "included": included,
        "excluded_no_consent": excluded_no_consent,
        "excluded_no_person_record": excluded_no_person,
        "note": (
            "Only participants with consent_public_profile=True are included. "
            "excluded_no_consent records were omitted and must not be "
            "re-added without re-checking consent."
        ),
    }

    return out.getvalue(), manifest
