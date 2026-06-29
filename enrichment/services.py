"""External enrichment services.

Each function fetches one external source, diffs against the current record,
and creates MetadataSuggestion records for differing fields.
Derived data is NEVER written directly to core models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import EnrichmentLog, EnrichmentSource, EnrichmentStatus, TargetType

if TYPE_CHECKING:
    from core.models import Organization, Person, Publication


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _log(
    source: str,
    target_type: str,
    target_id: Any,
    *,
    status: str,
    http_status: int | None = None,
    suggestions_created: int = 0,
    error_message: str = "",
) -> EnrichmentLog:
    return EnrichmentLog.objects.create(
        source=source,
        target_type=target_type,
        target_id=target_id,
        status=status,
        http_status=http_status,
        suggestions_created=suggestions_created,
        error_message=error_message[:2000],
    )


def _make_suggestion(
    *,
    field_name: str,
    current: str,
    remote: str,
    source: str,
    confidence: float,
    detail: str,
    **target_kwargs: Any,
) -> Any | None:
    """Create a MetadataSuggestion if the value differs and no open duplicate exists."""
    from metadata.models import MetadataSuggestion, SuggestionStatus

    if not remote or str(remote).strip() == str(current or "").strip():
        return None
    if MetadataSuggestion.objects.filter(
        field_name=field_name, status=SuggestionStatus.OPEN, **target_kwargs
    ).exists():
        return None
    return MetadataSuggestion.objects.create(
        field_name=field_name,
        current_value=str(current or ""),
        suggested_value=str(remote),
        source=source,
        confidence_score=confidence,
        detail=detail,
        **target_kwargs,
    )


# ---------------------------------------------------------------------------
# Publication enrichment
# ---------------------------------------------------------------------------

_PUB_CONFIDENCE: dict[str, float] = {
    "title": 0.85,
    "year": 0.9,
    "publication_type": 0.75,
    "venue": 0.8,
}


def _pub_suggestions(pub: Publication, parsed: dict[str, Any], source: str) -> list:
    out = []
    for field, remote in parsed.items():
        if remote is None:
            continue
        current = getattr(pub, field, None)
        sug = _make_suggestion(
            field_name=field,
            current=str(current) if current is not None else "",
            remote=str(remote),
            source=source,
            confidence=_PUB_CONFIDENCE.get(field, 0.75),
            detail=f"{source} reports {field}={remote!r} (DOI: {pub.doi_normalized})",
            publication=pub,
        )
        if sug:
            out.append(sug)
    return out


def enrich_publication_from_crossref(pub: Publication, *, fetcher=None) -> list:
    """Fetch Crossref metadata by DOI and return new MetadataSuggestion records."""
    from .adapters.crossref import fetch_crossref_work, parse_crossref_work

    if not pub.doi_normalized:
        _log(
            EnrichmentSource.CROSSREF,
            TargetType.PUBLICATION,
            pub.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No DOI",
        )
        return []

    try:
        data = fetch_crossref_work(pub.doi_normalized, fetcher=fetcher)
    except Exception as exc:  # noqa: BLE001
        _log(
            EnrichmentSource.CROSSREF,
            TargetType.PUBLICATION,
            pub.pk,
            status=EnrichmentStatus.ERROR,
            error_message=str(exc),
        )
        return []

    parsed = parse_crossref_work(data)
    suggestions = _pub_suggestions(pub, parsed, "crossref")
    _log(
        EnrichmentSource.CROSSREF,
        TargetType.PUBLICATION,
        pub.pk,
        status=EnrichmentStatus.OK,
        suggestions_created=len(suggestions),
    )
    return suggestions


def enrich_publication_from_openalex(pub: Publication, *, fetcher=None) -> list:
    """Fetch OpenAlex metadata by DOI and return new MetadataSuggestion records."""
    from .adapters.openalex import fetch_openalex_work, parse_openalex_work

    if not pub.doi_normalized:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PUBLICATION,
            pub.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No DOI",
        )
        return []

    try:
        item = fetch_openalex_work(pub.doi_normalized, fetcher=fetcher)
    except Exception as exc:  # noqa: BLE001
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PUBLICATION,
            pub.pk,
            status=EnrichmentStatus.ERROR,
            error_message=str(exc),
        )
        return []

    if item is None:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PUBLICATION,
            pub.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No OpenAlex record for DOI",
        )
        return []

    parsed = parse_openalex_work(item)
    suggestions = _pub_suggestions(pub, parsed, "openalex")
    _log(
        EnrichmentSource.OPENALEX,
        TargetType.PUBLICATION,
        pub.pk,
        status=EnrichmentStatus.OK,
        suggestions_created=len(suggestions),
    )
    return suggestions


# ---------------------------------------------------------------------------
# Person enrichment (OpenAlex)
# ---------------------------------------------------------------------------

_PERSON_CONFIDENCE: dict[str, float] = {"given_name": 0.7, "family_name": 0.7}


def enrich_person_from_openalex(person: Person, *, fetcher=None) -> list:
    """Fetch OpenAlex author record by ORCID and return new MetadataSuggestion records."""
    from .adapters.openalex import fetch_openalex_author, parse_openalex_author

    if not person.orcid:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PERSON,
            person.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No ORCID",
        )
        return []

    try:
        item = fetch_openalex_author(person.orcid, fetcher=fetcher)
    except Exception as exc:  # noqa: BLE001
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PERSON,
            person.pk,
            status=EnrichmentStatus.ERROR,
            error_message=str(exc),
        )
        return []

    if item is None:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.PERSON,
            person.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No OpenAlex record for ORCID",
        )
        return []

    parsed = parse_openalex_author(item)
    suggestions = []
    for field, remote in parsed.items():
        if not remote:
            continue
        sug = _make_suggestion(
            field_name=field,
            current=getattr(person, field, ""),
            remote=remote,
            source="openalex",
            confidence=_PERSON_CONFIDENCE.get(field, 0.7),
            detail=f"OpenAlex display_name suggests {field}={remote!r}",
            person=person,
        )
        if sug:
            suggestions.append(sug)

    _log(
        EnrichmentSource.OPENALEX,
        TargetType.PERSON,
        person.pk,
        status=EnrichmentStatus.OK,
        suggestions_created=len(suggestions),
    )
    return suggestions


# ---------------------------------------------------------------------------
# Organization enrichment (OpenAlex + Wikidata)
# ---------------------------------------------------------------------------

_ORG_OA_CONFIDENCE: dict[str, float] = {
    "country": 0.85,
    "org_type": 0.75,
    "website": 0.8,
}


def enrich_org_from_openalex(org: Organization, *, fetcher=None) -> list:
    """Fetch OpenAlex institution record by ROR and return new MetadataSuggestion records."""
    from .adapters.openalex import fetch_openalex_institution, parse_openalex_institution

    if not org.ror_id:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.ORGANIZATION,
            org.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No ROR ID",
        )
        return []

    try:
        item = fetch_openalex_institution(org.ror_id, fetcher=fetcher)
    except Exception as exc:  # noqa: BLE001
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.ORGANIZATION,
            org.pk,
            status=EnrichmentStatus.ERROR,
            error_message=str(exc),
        )
        return []

    if item is None:
        _log(
            EnrichmentSource.OPENALEX,
            TargetType.ORGANIZATION,
            org.pk,
            status=EnrichmentStatus.SKIPPED,
            error_message="No OpenAlex record for ROR",
        )
        return []

    parsed = parse_openalex_institution(item)
    suggestions = []
    for field, remote in parsed.items():
        if not remote:
            continue
        sug = _make_suggestion(
            field_name=field,
            current=getattr(org, field, ""),
            remote=remote,
            source="openalex",
            confidence=_ORG_OA_CONFIDENCE.get(field, 0.75),
            detail=f"OpenAlex reports {field}={remote!r} (ROR: {org.ror_id})",
            organization=org,
        )
        if sug:
            suggestions.append(sug)

    _log(
        EnrichmentSource.OPENALEX,
        TargetType.ORGANIZATION,
        org.pk,
        status=EnrichmentStatus.OK,
        suggestions_created=len(suggestions),
    )
    return suggestions


def enrich_org_from_wikidata(org: Organization, *, fetcher=None) -> list:
    """
    Enrich an org from Wikidata.
    - If no wikidata_qid: search by name, suggest the top QID (confidence 0.5).
    - If wikidata_qid set: fetch entity, suggest website (P856).
    """
    from .adapters.wikidata import (
        fetch_wikidata_entity,
        parse_wikidata_org,
        search_wikidata_entity,
    )

    if not org.wikidata_qid:
        try:
            qid = search_wikidata_entity(org.name, fetcher=fetcher)
        except Exception as exc:  # noqa: BLE001
            _log(
                EnrichmentSource.WIKIDATA,
                TargetType.ORGANIZATION,
                org.pk,
                status=EnrichmentStatus.ERROR,
                error_message=str(exc),
            )
            return []

        suggestions = []
        if qid:
            sug = _make_suggestion(
                field_name="wikidata_qid",
                current="",
                remote=qid,
                source="wikidata",
                confidence=0.5,
                detail=(
                    f"Top Wikidata search result for '{org.name}'. "
                    "Verify this is the correct entity before accepting."
                ),
                organization=org,
            )
            if sug:
                suggestions.append(sug)
        _log(
            EnrichmentSource.WIKIDATA,
            TargetType.ORGANIZATION,
            org.pk,
            status=EnrichmentStatus.OK,
            suggestions_created=len(suggestions),
        )
        return suggestions

    # QID known — fetch entity claims
    try:
        entity = fetch_wikidata_entity(org.wikidata_qid, fetcher=fetcher)
    except Exception as exc:  # noqa: BLE001
        _log(
            EnrichmentSource.WIKIDATA,
            TargetType.ORGANIZATION,
            org.pk,
            status=EnrichmentStatus.ERROR,
            error_message=str(exc),
        )
        return []

    parsed = parse_wikidata_org(entity)
    suggestions = []
    for field, remote in parsed.items():
        if not remote:
            continue
        sug = _make_suggestion(
            field_name=field,
            current=getattr(org, field, ""),
            remote=remote,
            source="wikidata",
            confidence=0.85,
            detail=f"Wikidata ({org.wikidata_qid}) reports {field}={remote!r}",
            organization=org,
        )
        if sug:
            suggestions.append(sug)

    _log(
        EnrichmentSource.WIKIDATA,
        TargetType.ORGANIZATION,
        org.pk,
        status=EnrichmentStatus.OK,
        suggestions_created=len(suggestions),
    )
    return suggestions
