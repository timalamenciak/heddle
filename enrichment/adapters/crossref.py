"""Crossref public API adapter — no authentication required.

Polite pool: include CROSSREF_MAILTO in User-Agent (handled by http.get_json).
"""

from __future__ import annotations

import urllib.parse
from typing import Any

_BASE_URL = "https://api.crossref.org/works/"

_TYPE_MAP: dict[str, str] = {
    "journal-article": "journal_article",
    "book-chapter": "book_chapter",
    "proceedings-article": "conference_paper",
    "book": "book",
    "dataset": "dataset",
    "preprint": "preprint",
    "report": "report",
    "dissertation": "dissertation",
}


def _default_fetcher(doi: str) -> dict[str, Any]:
    from .http import get_json

    url = _BASE_URL + urllib.parse.quote(doi, safe="")
    return get_json(url)


def fetch_crossref_work(doi: str, *, fetcher=None) -> dict[str, Any]:
    """Fetch Crossref work by DOI. Inject *fetcher* in tests to avoid HTTP."""
    fn = fetcher or _default_fetcher
    return fn(doi)


def _first(lst: list, default: str = "") -> str:
    return lst[0] if lst else default


def parse_crossref_work(data: dict[str, Any]) -> dict[str, Any]:
    """Return flat {title, year, publication_type, venue} from a Crossref 'message' dict."""
    msg = data.get("message", {})

    title = _first(msg.get("title", []))

    year: int | None = None
    for date_key in ("published-print", "published-online", "issued"):
        parts = msg.get(date_key, {}).get("date-parts", [[]])
        if parts and parts[0]:
            try:
                year = int(parts[0][0])
                break
            except (TypeError, ValueError):
                pass

    cr_type = msg.get("type", "")
    pub_type = _TYPE_MAP.get(cr_type, cr_type)

    venue = _first(msg.get("container-title", []))

    return {"title": title, "year": year, "publication_type": pub_type, "venue": venue}
