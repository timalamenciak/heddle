"""Import pipeline: parse, preview (dry-run), and apply."""

import csv
import hashlib
import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.models import Affiliation, Organization, Person

from .normalize import (
    country_to_continent,
    normalize_country,
    normalize_email,
    normalize_orcid,
    normalize_whitespace,
    split_full_name,
)

if TYPE_CHECKING:
    from .models import ImportSession


class CSVImportError(ValueError):
    """Raised when an uploaded CSV is unsafe or structurally invalid."""


def inspect_csv_upload(uploaded: UploadedFile) -> tuple[str, int, str]:
    """Decode and validate a bounded CSV upload.

    Returns ``(decoded_text, row_count, sha256)``. UTF-16 is accepted only
    when a byte-order mark is present, avoiding ambiguous encoding guesses.
    """
    max_bytes = settings.CSV_IMPORT_MAX_BYTES
    data = uploaded.read(max_bytes + 1)
    if not data:
        raise CSVImportError("The CSV file is empty.")
    if len(data) > max_bytes:
        raise CSVImportError(f"CSV files must be {max_bytes // (1024 * 1024)} MB or smaller.")

    try:
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            raw_csv = data.decode("utf-16")
        else:
            raw_csv = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CSVImportError("Use UTF-8, or UTF-16 with a byte-order mark.") from exc

    if "\x00" in raw_csv:
        raise CSVImportError("The CSV contains unsupported NUL characters.")

    try:
        csv.field_size_limit(max_bytes)
        reader = csv.reader(io.StringIO(raw_csv))
        headers = next(reader, None)
        if not headers or not any(header.strip() for header in headers):
            raise CSVImportError("The CSV must have a non-empty header row.")
        if len(headers) > settings.CSV_IMPORT_MAX_COLUMNS:
            raise CSVImportError(
                f"The CSV has too many columns (maximum {settings.CSV_IMPORT_MAX_COLUMNS})."
            )
        normalized_headers = [header.strip().casefold() for header in headers]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise CSVImportError("CSV column names must be unique.")

        row_count = 0
        for row_count, row in enumerate(reader, start=1):
            if row_count > settings.CSV_IMPORT_MAX_ROWS:
                raise CSVImportError(
                    f"The CSV has too many rows (maximum {settings.CSV_IMPORT_MAX_ROWS})."
                )
            if len(row) > len(headers):
                raise CSVImportError(f"Row {row_count + 1} has more values than the header.")
    except csv.Error as exc:
        raise CSVImportError(f"The CSV could not be parsed: {exc}") from exc

    return raw_csv, row_count, hashlib.sha256(data).hexdigest()


@dataclass
class PreviewRow:
    row_num: int
    action: str  # "create" | "update" | "unchanged" | "error"
    data: dict[str, Any]
    matched_person_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class PreviewResult:
    creates: list[PreviewRow] = field(default_factory=list)
    updates: list[PreviewRow] = field(default_factory=list)
    unchanged: list[PreviewRow] = field(default_factory=list)
    errors: list[PreviewRow] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.creates) + len(self.updates) + len(self.unchanged) + len(self.errors)


def parse_csv(raw_csv: str, mapping: dict[str, str]) -> list[dict[str, Any]]:
    """Parse CSV string applying column mapping. Returns list of field dicts."""
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(raw_csv))
    for row_number, csv_row in enumerate(reader, start=1):
        if row_number > settings.CSV_IMPORT_MAX_ROWS:
            raise CSVImportError(
                f"The CSV has too many rows (maximum {settings.CSV_IMPORT_MAX_ROWS})."
            )
        normalized: dict[str, Any] = {}
        for csv_col, field_name in mapping.items():
            if not field_name or csv_col not in csv_row:
                continue
            normalized[field_name] = (csv_row[csv_col] or "").strip()
        rows.append(normalized)
    return rows


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)

    # Split full_name into given/family if individual fields aren't already set
    full_name = out.pop("full_name", None)
    if full_name:
        if not out.get("given_name") and not out.get("family_name"):
            out["given_name"], out["family_name"] = split_full_name(full_name)

    if "orcid" in out:
        out["orcid"] = normalize_orcid(out["orcid"]) or ""
    if "email" in out and out["email"]:
        out["email"] = normalize_email(out["email"])
    for f in ("given_name", "family_name", "organization", "notes"):
        if f in out:
            out[f] = normalize_whitespace(out[f])

    if "country" in out:
        raw_country = out["country"]
        out["country"] = normalize_country(raw_country)
        out["_country_raw"] = raw_country  # carry through for warning generation

    if out.get("country") and not out.get("continent"):
        out["continent"] = country_to_continent(out["country"])

    return out


def _match_person(row: dict[str, Any]) -> tuple["Person | None", str]:
    """Return (Person, match_key) or (None, '') if no match."""
    orcid = row.get("orcid")
    if orcid:
        try:
            return Person.objects.get(orcid=orcid), "orcid"
        except Person.DoesNotExist:
            pass

    email = row.get("email")
    if email:
        qs = Person.objects.filter(email__iexact=email)
        if qs.count() == 1:
            person = qs.first()
            if person is not None:
                return person, "email"

    given = row.get("given_name", "")
    family = row.get("family_name", "")
    if given and family:
        name_key = " ".join(f"{given} {family}".lower().split())
        candidates = Person.objects.filter(name_normalized=name_key)
        org_name = row.get("organization", "")
        if org_name and candidates.count() > 1:
            org_norm = " ".join(org_name.lower().split())
            candidates = candidates.filter(affiliations__organization__name_normalized=org_norm)
        if candidates.count() == 1:
            person = candidates.first()
            if person is not None:
                return person, "name+org"

    return None, ""


def _person_needs_update(person: Person, row: dict[str, Any]) -> bool:
    for row_key, model_attr in _UPDATABLE_FIELDS.items():
        new_val = row.get(row_key)
        if new_val and new_val != getattr(person, model_attr, ""):
            return True
    return False


_UPDATABLE_FIELDS: dict[str, str] = {
    "given_name": "given_name",
    "family_name": "family_name",
    "email": "email",
    "orcid": "orcid",
    "country": "country",
    "continent": "continent",
    "website": "website",
    "notes": "notes",
}


def run_preview(rows: list[dict[str, Any]], source_label: str = "") -> PreviewResult:
    """Dry-run: compute what would happen without writing to the database."""
    result = PreviewResult()
    for i, raw_row in enumerate(rows, start=1):
        row = _normalize_row(raw_row)
        warnings: list[str] = []

        # Country warning before stripping internal key
        raw_country = row.pop("_country_raw", "")
        if raw_country and not row.get("country"):
            warnings.append(
                f"Country {raw_country!r} not recognized as ISO code or known name"  # noqa: E501
                " — field left blank"
            )

        if not row.get("given_name") and not row.get("family_name"):
            result.errors.append(
                PreviewRow(i, "error", row, error="Given name and family name are both empty")
            )
            continue

        if not row.get("given_name"):
            warnings.append("Missing given name")
        if not row.get("family_name"):
            warnings.append("Missing family name")

        orcid_raw = raw_row.get("orcid", "")
        if orcid_raw and not row.get("orcid"):
            warnings.append(f"Invalid ORCID ignored: {orcid_raw!r}")

        person, match_key = _match_person(row)

        if person is None:
            result.creates.append(PreviewRow(i, "create", row, warnings=warnings))
        elif _person_needs_update(person, row):
            result.updates.append(PreviewRow(i, "update", row, str(person.pk), warnings=warnings))
        else:
            result.unchanged.append(
                PreviewRow(i, "unchanged", row, str(person.pk), warnings=warnings)
            )
    return result


def apply_import(
    raw_rows: list[dict[str, Any]],
    source_label: str,
    session: "ImportSession",
) -> dict[str, int]:
    """Apply import: create/update Person and Affiliation records. Returns counts dict."""
    counts: dict[str, int] = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}

    for raw_row in raw_rows:
        row = _normalize_row(raw_row)
        row.pop("_country_raw", None)

        if not row.get("given_name") and not row.get("family_name"):
            counts["errors"] += 1
            continue

        person, _ = _match_person(row)
        org = _get_or_create_org(row, source_label)

        if person is None:
            person = _create_person(row, source_label)
            if org:
                Affiliation.objects.get_or_create(
                    person=person,
                    organization=org,
                    defaults={
                        "is_primary": True,
                        "role": row.get("organization_role", ""),
                        "source": source_label or "import",
                    },
                )
            counts["created"] += 1
        elif _person_needs_update(person, row):
            _update_person(person, row)
            if org:
                _upsert_affiliation(person, org, row, source_label)
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1

    return counts


def _get_or_create_org(row: dict[str, Any], source: str) -> "Organization | None":
    org_name = row.get("organization", "")
    if not org_name:
        return None
    org_norm = " ".join(org_name.lower().split())
    org, _ = Organization.objects.get_or_create(
        name_normalized=org_norm,
        defaults={"name": org_name, "source": source or "import"},
    )
    return org


def _create_person(row: dict[str, Any], source: str) -> Person:
    return Person.objects.create(
        given_name=row.get("given_name", ""),
        family_name=row.get("family_name", ""),
        email=row.get("email") or None,
        orcid=row.get("orcid") or None,
        country=row.get("country", ""),
        continent=row.get("continent", ""),
        website=row.get("website", ""),
        notes=row.get("notes", ""),
        source=source or "import",
    )


def _update_person(person: Person, row: dict[str, Any]) -> None:
    for row_key, model_attr in _UPDATABLE_FIELDS.items():
        new_val = row.get(row_key)
        if new_val:
            setattr(person, model_attr, new_val)
    person.save()


def _upsert_affiliation(
    person: Person, org: Organization, row: dict[str, Any], source: str
) -> None:
    Affiliation.objects.get_or_create(
        person=person,
        organization=org,
        defaults={
            "is_primary": False,
            "role": row.get("organization_role", ""),
            "source": source or "import",
        },
    )
