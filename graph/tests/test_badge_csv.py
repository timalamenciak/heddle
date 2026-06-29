"""Tests for graph/exporters/badge_csv.py."""

import csv
import datetime
import io

import pytest

from core.models import Affiliation, Organization, Person
from events.models import Event, Participation
from graph.exporters.badge_csv import BADGE_FIELDNAMES, build_badge_export


def _person(**kw) -> Person:
    defaults = {"given_name": "Ada", "family_name": "Lovelace"}
    defaults.update(kw)
    return Person.objects.create(**defaults)


def _event(**kw) -> Event:
    defaults = {"name": "EcoTransform 2024", "start_date": datetime.date(2024, 6, 1)}
    defaults.update(kw)
    return Event.objects.create(**defaults)


def _participate(person, event, **kw) -> Participation:
    defaults = {"role": "attendee", "status": "confirmed"}
    defaults.update(kw)
    return Participation.objects.create(person=person, event=event, **defaults)


def _parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


@pytest.mark.django_db
class TestBuildBadgeExport:
    def test_consenting_participant_included(self):
        p = _person(consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, manifest = build_badge_export(event, generated_by="test")
        rows = _parse_csv(csv_data)
        assert len(rows) == 1
        assert manifest["included"] == 1
        assert manifest["excluded_no_consent"] == 0

    def test_non_consenting_excluded(self):
        p = _person(consent_public_profile=False)
        event = _event()
        _participate(p, event)

        csv_data, manifest = build_badge_export(event, generated_by="test")
        rows = _parse_csv(csv_data)
        assert len(rows) == 0
        assert manifest["excluded_no_consent"] == 1

    def test_mixed_consent(self):
        p_yes = _person(given_name="Alice", consent_public_profile=True)
        p_no = _person(given_name="Bob", family_name="Smith", consent_public_profile=False)
        event = _event()
        _participate(p_yes, event)
        _participate(p_no, event)

        csv_data, manifest = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert len(rows) == 1
        assert manifest["included"] == 1
        assert manifest["excluded_no_consent"] == 1

    def test_all_required_columns_present(self):
        p = _person(consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        for field in BADGE_FIELDNAMES:
            assert field in rows[0], f"Missing column: {field}"

    def test_orcid_populated(self):
        p = _person(orcid="0000-0001-2345-6789", consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["orcid"] == "0000-0001-2345-6789"

    def test_email_never_in_csv(self):
        p = _person(email="secret@example.com", consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        assert "secret@example.com" not in csv_data

    def test_person_id_uses_orcid_scheme(self):
        p = _person(orcid="0000-0001-2345-6789", consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["person_id"] == "ORCID:0000-0001-2345-6789"

    def test_person_id_uses_heddle_scheme_when_no_orcid(self):
        p = _person(consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["person_id"] == f"heddle:person/{p.pk}"

    def test_event_name_in_row(self):
        p = _person(consent_public_profile=True)
        event = _event(name="OERC Workshop 2025")
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["event_name"] == "OERC Workshop 2025"

    def test_consent_public_profile_column_is_true(self):
        p = _person(consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["consent_public_profile"] == "true"

    def test_organization_column_populated(self):
        org = Organization.objects.create(name="University of Test")
        p = _person(consent_public_profile=True)
        Affiliation.objects.create(person=p, organization=org, is_primary=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["organization"] == "University of Test"

    def test_manifest_has_required_keys(self):
        event = _event()
        _, manifest = build_badge_export(event)
        for key in (
            "generated_at",
            "generated_by",
            "event_id",
            "event_name",
            "included",
            "excluded_no_consent",
            "excluded_no_person_record",
            "note",
        ):
            assert key in manifest, f"Missing manifest key: {key}"

    def test_formula_injection_in_name_escaped(self):
        p = _person(given_name="=INJECT", family_name="Person", consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows[0]["display_name"].startswith("'")

    def test_empty_event_returns_empty_csv(self):
        event = _event()
        csv_data, manifest = build_badge_export(event)
        rows = _parse_csv(csv_data)
        assert rows == []
        assert manifest["included"] == 0

    def test_quality_score_column_present(self):
        p = _person(consent_public_profile=True)
        event = _event()
        _participate(p, event)

        csv_data, _ = build_badge_export(event, include_quality_score=True)
        rows = _parse_csv(csv_data)
        # Score is a number string (possibly "100" for no issues)
        assert rows[0]["metadata_quality_score"] != ""
