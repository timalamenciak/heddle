"""OpenAlex public API adapter — no authentication required."""

from __future__ import annotations

import urllib.parse
from typing import Any

_BASE = "https://api.openalex.org/"

_INST_TYPE_MAP: dict[str, str] = {
    "education": "university",
    "healthcare": "research_institute",
    "company": "industry",
    "government": "government",
    "nonprofit": "ngo",
    "funder": "ngo",
    "archive": "other",
    "facility": "research_institute",
    "other": "other",
}

_WORK_SELECT = "id,title,publication_year,type,primary_location"
_AUTHOR_SELECT = "id,display_name,last_known_institutions,x_concepts"
_INST_SELECT = "id,display_name,country_code,type,homepage_url"


def _default_work_fetcher(doi: str) -> dict[str, Any]:
    from .http import get_json

    enc = urllib.parse.quote(doi, safe="")
    url = f"{_BASE}works?filter=doi:{enc}&select={_WORK_SELECT}&per-page=1"
    return get_json(url)


def _default_author_fetcher(orcid: str) -> dict[str, Any]:
    from .http import get_json

    url = f"{_BASE}authors?filter=orcid:{orcid}&select={_AUTHOR_SELECT}&per-page=1"
    return get_json(url)


def _default_institution_fetcher(ror_id: str) -> dict[str, Any]:
    from .http import get_json

    enc = urllib.parse.quote(ror_id, safe="")
    url = f"{_BASE}institutions?filter=ror:{enc}&select={_INST_SELECT}&per-page=1"
    return get_json(url)


def fetch_openalex_work(doi: str, *, fetcher=None) -> dict[str, Any] | None:
    """Return the first OpenAlex work matching *doi*, or None."""
    fn = fetcher or _default_work_fetcher
    data = fn(doi)
    results = data.get("results", [])
    return results[0] if results else None


def fetch_openalex_author(orcid: str, *, fetcher=None) -> dict[str, Any] | None:
    """Return the first OpenAlex author matching *orcid*, or None."""
    fn = fetcher or _default_author_fetcher
    data = fn(orcid)
    results = data.get("results", [])
    return results[0] if results else None


def fetch_openalex_institution(ror_id: str, *, fetcher=None) -> dict[str, Any] | None:
    """Return the first OpenAlex institution matching *ror_id*, or None."""
    fn = fetcher or _default_institution_fetcher
    data = fn(ror_id)
    results = data.get("results", [])
    return results[0] if results else None


def parse_openalex_work(item: dict[str, Any]) -> dict[str, Any]:
    """Return {title, year, publication_type, venue} from an OpenAlex work item."""
    title = item.get("title") or ""
    year = item.get("publication_year")
    pub_type = item.get("type") or ""
    venue = ""
    try:
        venue = item["primary_location"]["source"]["display_name"] or ""
    except (KeyError, TypeError):
        pass
    return {"title": title, "year": year, "publication_type": pub_type, "venue": venue}


def parse_openalex_author(item: dict[str, Any]) -> dict[str, Any]:
    """Return {given_name, family_name} split from OpenAlex display_name."""
    display_name = (item.get("display_name") or "").strip()
    parts = display_name.split()
    if len(parts) >= 2:
        given = " ".join(parts[:-1])
        family = parts[-1]
    elif parts:
        given, family = "", parts[0]
    else:
        given, family = "", ""
    return {"given_name": given, "family_name": family}


def parse_openalex_institution(item: dict[str, Any]) -> dict[str, Any]:
    """Return {country, org_type, website} from an OpenAlex institution item."""
    country = (item.get("country_code") or "").upper()
    oa_type = (item.get("type") or "").lower()
    org_type = _INST_TYPE_MAP.get(oa_type, "")
    website = item.get("homepage_url") or ""
    return {"country": country, "org_type": org_type, "website": website}
