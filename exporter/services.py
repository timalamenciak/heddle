"""CSV export services for the exporter pipeline."""

import csv
import io
from typing import Any

from django.db.models import QuerySet

from core.models import Person

_FORMULA_PREFIXES = frozenset({"=", "+", "-", "@", "\t"})

PERSON_COLUMNS: list[tuple[str, str]] = [
    ("given_name", "Given name"),
    ("family_name", "Family name"),
    ("orcid", "ORCID"),
    ("country", "Country"),
    ("continent", "Continent"),
    ("website", "Website"),
    ("primary_organization", "Primary organization"),
    ("notes", "Notes"),
    ("consent_contact", "Consent to contact"),
    ("consent_public_profile", "Consent public profile"),
    ("metadata_status", "Metadata status"),
    ("source", "Source"),
    ("created_at", "Created at"),
]

# Email is omitted from PERSON_COLUMNS because it must never appear in
# public exports. It can only be added explicitly by admin+ when needed.
ADMIN_ONLY_COLUMNS: frozenset[str] = frozenset({"notes_private", "email"})


def escape_cell(value: str) -> str:
    """Prefix formula-injection characters so spreadsheet apps don't execute them."""
    s = str(value)
    if s and s[0] in _FORMULA_PREFIXES:
        return f"'{s}"
    return s


def export_people_csv(
    qs: "QuerySet[Any]",
    columns: list[str],
    *,
    include_bom: bool = False,
) -> str:
    """Generate a CSV string for the given Person queryset and column list."""
    col_labels: dict[str, str] = dict(PERSON_COLUMNS)
    col_labels["notes_private"] = "Notes (private)"
    col_labels["email"] = "Email"

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([col_labels.get(c, c) for c in columns])

    for person in qs.prefetch_related("affiliations__organization"):
        row = [escape_cell(_get_person_field(person, col)) for col in columns]
        writer.writerow(row)

    result = output.getvalue()
    if include_bom:
        result = "﻿" + result
    return result


def _get_person_field(person: Person, col: str) -> str:
    if col == "primary_organization":
        org = person.primary_organization
        return str(org) if org else ""
    value = getattr(person, col, "")
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value) if value is not None else ""
