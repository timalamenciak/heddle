"""Thin HTTP client used by all enrichment adapters. Injectable for tests."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

_DEFAULT_TIMEOUT = getattr(settings, "ENRICHMENT_TIMEOUT", 15)
_MAILTO = getattr(settings, "CROSSREF_MAILTO", "admin@heddle.local")
_USER_AGENT = f"heddle/1.0 (mailto:{_MAILTO})"
_ALLOWED_HOSTS = frozenset(
    {
        "api.crossref.org",
        "api.openalex.org",
        "pub.orcid.org",
        "www.wikidata.org",
    }
)


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS:
        raise ValueError("Outbound URL must use HTTPS and an approved API host.")
    if parsed.username or parsed.password:
        raise ValueError("Outbound URLs must not contain credentials.")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """GET *url* and return parsed JSON. Raises urllib.error.URLError or ValueError on failure."""
    _validate_url(url)
    t = timeout or _DEFAULT_TIMEOUT
    req_headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)  # noqa: S310
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    with opener.open(req, timeout=t) as resp:  # noqa: S310
        final_url = resp.geturl()
        _validate_url(final_url)
        content_type = resp.headers.get_content_type()
        if content_type != "application/json" and not content_type.endswith("+json"):
            raise ValueError("Remote API returned a non-JSON content type.")
        max_bytes = settings.ENRICHMENT_MAX_RESPONSE_BYTES
        payload = resp.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError("Remote API response exceeded the configured size limit.")
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Remote API returned invalid JSON.") from exc
