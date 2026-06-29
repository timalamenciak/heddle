"""End-to-end integration test for the full heddle workflow.

Exercises (in order):
  import → normalise → dedup → metadata checks → event/participation →
  badge CSV export → KGX graph slice + validation → roster CSV export →
  segment filter.

Unit tests for each step live in the individual app test suites.
This test confirms all the pieces compose correctly.
"""

from __future__ import annotations

import csv
import datetime
import io

import pytest

from core.models import Affiliation, Organization, Person
from events.models import Event, Participation, SavedSegment
from exporter.services import export_people_csv
from graph.exporters.badge_csv import build_badge_export
from graph.slices import event_kgx_export
from graph.validators import validate_kgx_export
from importer.models import ImportSession
from importer.services import apply_import, parse_csv, run_preview
from metadata.services import run_checks_for_person

# ── Fixtures ────────────────────────────────────────────────────────────────

_CSV = """\
full_name,country,organization,orcid,email
Ada Lovelace,Canada,University of Test,0000-0001-2345-6789,ada@test.example
Grace Hopper,US,Naval Computing,,grace@test.example
"""

_MAPPING = {
    "full_name": "full_name",
    "country": "country",
    "organization": "organization",
    "orcid": "orcid",
    "email": "email",
}


def _make_session(raw_csv: str, mapping: dict, label: str = "e2e") -> ImportSession:
    return ImportSession.objects.create(
        raw_csv=raw_csv,
        column_mapping=mapping,
        source_label=label,
        row_count=2,
        status=ImportSession.Status.PREVIEWED,
    )


# ── The test ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_full_heddle_workflow():
    # ── Step 1: Parse CSV and preview (dry-run) ───────────────────────────
    raw_rows = parse_csv(_CSV, _MAPPING)
    preview = run_preview(raw_rows, source_label="e2e")

    assert len(preview.creates) == 2, "Both rows should be creates on first import"
    assert len(preview.errors) == 0
    assert Person.objects.count() == 0, "Preview must not write to the database"

    # ── Step 2: Apply import — people are created ─────────────────────────
    session = _make_session(_CSV, _MAPPING)
    counts = apply_import(raw_rows, "e2e", session)

    assert counts["created"] == 2
    assert counts["errors"] == 0
    assert Person.objects.count() == 2

    ada = Person.objects.get(orcid="0000-0001-2345-6789")
    grace = Person.objects.get(family_name="Hopper")

    # full_name was split correctly
    assert ada.given_name == "Ada"
    assert ada.family_name == "Lovelace"
    # "Canada" normalised to ISO alpha-2
    assert ada.country == "CA"
    # continent auto-derived from country
    assert ada.continent == "North America"

    # organisation was created and linked via Affiliation
    assert Organization.objects.filter(name="University of Test").exists()
    assert Affiliation.objects.filter(person=ada).exists()

    # ── Step 3: Dedup — re-importing same ORCID updates, not creates ──────
    update_csv = "full_name,country,orcid\nAda Lovelace,DE,0000-0001-2345-6789\n"
    update_mapping = {"full_name": "full_name", "country": "country", "orcid": "orcid"}
    update_rows = parse_csv(update_csv, update_mapping)
    update_session = _make_session(update_csv, update_mapping, label="e2e-update")
    update_counts = apply_import(update_rows, "e2e-update", update_session)

    assert update_counts["updated"] == 1
    assert update_counts["created"] == 0
    assert Person.objects.count() == 2, "No new person created on dedup"
    ada.refresh_from_db()
    assert ada.country == "DE", "Country should have been updated"

    # ── Step 4: Metadata checks run without crashing ──────────────────────
    # (No checks may be seeded in the test DB; this just confirms no exceptions)
    run_checks_for_person(ada)
    run_checks_for_person(grace)

    # ── Step 5: Event + participation ─────────────────────────────────────
    event = Event.objects.create(
        name="EcoTransform 2024",
        event_type="hackathon",
        start_date=datetime.date(2024, 6, 15),
        country="CA",
    )
    # Grant public consent for both participants
    Person.objects.filter(pk__in=[ada.pk, grace.pk]).update(consent_public_profile=True)
    ada.refresh_from_db()
    grace.refresh_from_db()

    Participation.objects.create(person=ada, event=event, role="attendee", status="confirmed")
    Participation.objects.create(person=grace, event=event, role="speaker", status="confirmed")

    # ── Step 6: Badge CSV — both consenting → both included ───────────────
    badge_csv, manifest = build_badge_export(event, generated_by="e2e-test")
    badge_rows = list(csv.DictReader(io.StringIO(badge_csv)))

    assert manifest["included"] == 2
    assert manifest["excluded_no_consent"] == 0
    # Email must never appear in any export
    assert "ada@test.example" not in badge_csv
    assert "grace@test.example" not in badge_csv
    assert badge_rows[0]["consent_public_profile"] == "true"

    # ── Step 7: KGX event slice validates against schema ──────────────────
    kgx = event_kgx_export(event.pk, generated_by="e2e-test")
    result = validate_kgx_export(kgx.nodes_tsv, kgx.edges_tsv)

    assert result.valid is True, f"KGX validation errors: {result.errors}"
    # 2 Person nodes + 1 Event node + organisations = at least 3
    assert result.node_count >= 3
    # 2 participates_in edges
    assert result.edge_count >= 2
    assert kgx.manifest["slice"].startswith("event:")
    assert "node_count" in kgx.manifest
    assert "generated_at" in kgx.manifest
    # Email never in graph export
    assert "ada@test.example" not in kgx.nodes_tsv
    assert "ada@test.example" not in kgx.edges_tsv

    # Non-consenting person would be anonymised (test with a new person)
    no_consent = Person.objects.create(
        given_name="Anon", family_name="User", consent_public_profile=False
    )
    from graph.exporters.kgx import build_kgx_export

    anon_export = build_kgx_export(people=[no_consent], anonymize_non_consenting=True)
    assert "Anon User" not in anon_export.nodes_tsv
    assert "Anonymous" in anon_export.nodes_tsv
    assert "heddle:anon/" in anon_export.nodes_tsv

    # ── Step 8: Roster CSV — formula injection escaped ─────────────────────
    danger = Person.objects.create(given_name="=DANGER", family_name="Formula")
    roster = export_people_csv(
        Person.objects.all(),
        columns=["given_name", "family_name", "orcid", "country"],
    )
    # Unescaped formula must not start any cell (would appear after \r\n or comma)
    assert "\r\n=DANGER" not in roster, "Raw formula must not start a row cell"
    assert ",=DANGER" not in roster, "Raw formula must not start a middle cell"
    assert "'=DANGER" in roster, "Formula must be escaped with leading apostrophe"
    # Verify email is absent even with all columns (it's not in PERSON_COLUMNS)
    from exporter.services import PERSON_COLUMNS

    public_cols = [c for c, _ in PERSON_COLUMNS]
    assert "email" not in public_cols

    # ── Step 9: Segment filter matches by country ──────────────────────────
    # ada.country == "DE" after the update step
    segment = SavedSegment.objects.create(
        name="DE researchers",
        filters={"country": "DE"},
    )
    matched = Person.objects.filter(**segment.filters)
    assert matched.filter(pk=ada.pk).exists(), "Ada (DE) should match the segment"
    assert not matched.filter(pk=grace.pk).exists(), "Grace (US) should not match"
    assert not matched.filter(pk=danger.pk).exists(), "Danger (no country) should not match"
