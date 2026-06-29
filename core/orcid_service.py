"""ORCID public-API integration. No tokens stored or logged. Derived data
becomes MetadataSuggestion records; it never overwrites human-entered fields."""

from typing import Any

from django.utils import timezone

from .identifiers import normalize_orcid as normalize_orcid
from .identifiers import validate_orcid
from .models import ORCIDProfile, ORCIDWork

# ---------------------------------------------------------------------------
# HTTP fetcher (injectable for tests)
# ---------------------------------------------------------------------------


def _default_fetcher(orcid: str) -> dict[str, Any]:
    from enrichment.adapters.http import get_json

    url = f"https://pub.orcid.org/v3.0/{orcid}"
    return get_json(url)


def fetch_orcid_record(orcid: str, *, fetcher=None) -> dict[str, Any]:
    """Fetch the ORCID 3.0 public record. Pass *fetcher* in tests to avoid HTTP."""
    fn = fetcher or _default_fetcher
    return fn(orcid)


# ---------------------------------------------------------------------------
# Record parsing helpers
# ---------------------------------------------------------------------------


def _extract_given_name(record: dict) -> str:
    try:
        return record["person"]["name"]["given-names"]["value"] or ""
    except (KeyError, TypeError):
        return ""


def _extract_family_name(record: dict) -> str:
    try:
        return record["person"]["name"]["family-name"]["value"] or ""
    except (KeyError, TypeError):
        return ""


def _extract_works(record: dict) -> list[dict]:
    try:
        groups = record["activities-summary"]["works"]["group"]
    except (KeyError, TypeError):
        return []
    results = []
    for group in groups:
        summaries = group.get("work-summary", [])
        if summaries:
            results.append(summaries[0])  # first summary = most-recent version in group
    return results


# ---------------------------------------------------------------------------
# Work sync
# ---------------------------------------------------------------------------


def _sync_works(person, profile: ORCIDProfile, record: dict) -> None:
    for ws in _extract_works(record):
        put_code = ws.get("put-code")
        if not put_code:
            continue
        title = ""
        try:
            title = ws["title"]["title"]["value"] or ""
        except (KeyError, TypeError):
            pass
        work_type = ws.get("type", "")
        pub_year = None
        try:
            pub_year = int(ws["publication-date"]["year"]["value"])
        except (KeyError, TypeError, ValueError):
            pass
        doi = ""
        try:
            for ext_id in ws["external-ids"]["external-id"]:
                if ext_id.get("external-id-type") == "doi":
                    doi = ext_id.get("external-id-value", "")
                    break
        except (KeyError, TypeError):
            pass
        ORCIDWork.objects.update_or_create(
            person=person,
            put_code=put_code,
            defaults={
                "profile": profile,
                "title": title[:500],
                "work_type": work_type,
                "publication_year": pub_year,
                "doi": doi,
                "raw_work": ws,
            },
        )


# ---------------------------------------------------------------------------
# Suggestion generation
# ---------------------------------------------------------------------------


def _names_differ(a: str, b: str) -> bool:
    return a.strip().lower() != b.strip().lower()


def _generate_suggestions(person, profile: ORCIDProfile, _record: dict) -> list:
    from metadata.models import MetadataSuggestion, SuggestionStatus

    created = []
    for field, current, remote in [
        ("given_name", person.given_name, profile.given_name_remote),
        ("family_name", person.family_name, profile.family_name_remote),
    ]:
        if not remote:
            continue
        if not _names_differ(current, remote):
            continue
        if MetadataSuggestion.objects.filter(
            person=person, field_name=field, status=SuggestionStatus.OPEN
        ).exists():
            continue
        sug = MetadataSuggestion.objects.create(
            person=person,
            field_name=field,
            current_value=current,
            suggested_value=remote,
            source="orcid_sync",
            confidence_score=0.9,
            detail=(f"ORCID public record shows '{remote}' but the stored value is '{current}'."),
        )
        created.append(sug)
    return created


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def sync_person_orcid(person, *, fetcher=None) -> list:
    """Fetch ORCID public record, cache it, and return any new MetadataSuggestions.

    Returns an empty list if person has no ORCID or if validation fails.
    Derived data is NEVER written directly to Person fields.
    """
    if not person.orcid or not validate_orcid(person.orcid):
        return []

    record = fetch_orcid_record(person.orcid, fetcher=fetcher)

    given_remote = _extract_given_name(record)
    family_remote = _extract_family_name(record)

    profile, _ = ORCIDProfile.objects.update_or_create(
        person=person,
        defaults={
            "fetched_at": timezone.now(),
            "given_name_remote": given_remote,
            "family_name_remote": family_remote,
            "raw_record": record,
        },
    )

    _sync_works(person, profile, record)
    return _generate_suggestions(person, profile, record)
