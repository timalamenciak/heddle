"""Canonical identifier normalization and validation."""

import re

_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def validate_orcid(value: str) -> bool:
    """Validate ORCID format and ISO 7064 MOD 11-2 check digit."""
    if not _ORCID_RE.fullmatch(value):
        return False
    digits = value.replace("-", "")
    total = 0
    for char in digits[:15]:
        total = (total + int(char)) * 2
    remainder = (12 - (total % 11)) % 11
    expected = "X" if remainder == 10 else str(remainder)
    return digits[-1] == expected


def normalize_orcid(value: str) -> str | None:
    """Return a canonical, checksum-valid ORCID or ``None``."""
    if not value:
        return None
    candidate = value.strip().rstrip("/")
    if "/" in candidate:
        candidate = candidate.rsplit("/", 1)[-1]
    digits = candidate.replace("-", "").upper()
    if len(digits) != 16:
        return None
    canonical = f"{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
    return canonical if validate_orcid(canonical) else None
