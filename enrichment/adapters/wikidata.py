"""Wikidata MediaWiki API adapter — search by name, fetch entity by QID."""

from __future__ import annotations

import urllib.parse
from typing import Any

_API = "https://www.wikidata.org/w/api.php"


def _default_search_fetcher(name: str) -> dict[str, Any]:
    from .http import get_json

    params = urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "type": "item",
            "format": "json",
            "limit": 3,
        }
    )
    return get_json(f"{_API}?{params}")


def _default_entity_fetcher(qid: str) -> dict[str, Any]:
    from .http import get_json

    params = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims|labels",
            "languages": "en",
            "format": "json",
        }
    )
    return get_json(f"{_API}?{params}")


def search_wikidata_entity(name: str, *, fetcher=None) -> str | None:
    """Search Wikidata for an entity matching *name*. Returns the top QID or None."""
    fn = fetcher or _default_search_fetcher
    data = fn(name)
    results = data.get("search", [])
    return results[0].get("id") if results else None


def fetch_wikidata_entity(qid: str, *, fetcher=None) -> dict[str, Any]:
    """Fetch the Wikidata entity for *qid*. Returns the entity dict (may be empty)."""
    fn = fetcher or _default_entity_fetcher
    data = fn(qid)
    return data.get("entities", {}).get(qid, {})


def parse_wikidata_org(entity: dict[str, Any]) -> dict[str, Any]:
    """Extract {website} from Wikidata entity claims. P856 = official website."""
    website = ""
    try:
        p856 = entity.get("claims", {}).get("P856", [])
        if p856:
            website = p856[0]["mainsnak"]["datavalue"]["value"] or ""
    except (KeyError, TypeError, IndexError):
        pass
    return {"website": website}
