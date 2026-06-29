"""Tests for invite-list CSV export and manifest generation."""

import io
import zipfile

import pytest

from core.models import Person
from events.models import SavedSegment
from events.services import build_invite_zip, export_invite_list
from metadata.models import IssueStatus, MetadataCheck, MetadataIssue


def _make_person(**kwargs):
    return Person.objects.create(**kwargs)


def _make_segment(filters=None):
    return SavedSegment.objects.create(name="Test segment", filters=filters or {})


def _critical_check():
    existing = MetadataCheck.objects.filter(severity="critical").first()
    if existing:
        return existing
    return MetadataCheck.objects.create(
        code="test_crit_export",
        name="Critical test",
        severity="critical",
        weight=50.0,
        target="person",
    )


@pytest.mark.django_db
class TestExportInviteList:
    def test_included_person_appears_in_invite_csv(self):
        _make_person(given_name="Ada", family_name="Lovelace", consent_contact=True)
        seg = _make_segment()
        invite_csv, _ = export_invite_list(seg)
        assert "Ada" in invite_csv

    def test_non_consenting_excluded_from_invite(self):
        _make_person(given_name="No", family_name="Consent", consent_contact=False)
        seg = _make_segment()
        invite_csv, _ = export_invite_list(seg)
        assert "No" not in invite_csv.split("\n", 1)[1]  # skip header

    def test_non_consenting_appears_in_manifest(self):
        _make_person(given_name="No", family_name="Consent", consent_contact=False)
        seg = _make_segment()
        _, manifest_csv = export_invite_list(seg)
        assert "No" in manifest_csv
        assert "consent" in manifest_csv.lower()

    def test_critical_issue_excluded_from_invite(self):
        person = _make_person(given_name="Bad", family_name="Record", consent_contact=True)
        mc = _critical_check()
        MetadataIssue.objects.create(metadata_check=mc, person=person, status=IssueStatus.OPEN)
        seg = _make_segment()
        invite_csv, _ = export_invite_list(seg)
        # Header counts as a row; person should not appear in data rows
        data_rows = invite_csv.strip().split("\n")[1:]
        assert not any("Bad" in row for row in data_rows)

    def test_critical_issue_appears_in_manifest_with_reason(self):
        person = _make_person(given_name="Bad", family_name="Record", consent_contact=True)
        mc = _critical_check()
        MetadataIssue.objects.create(metadata_check=mc, person=person, status=IssueStatus.OPEN)
        seg = _make_segment()
        _, manifest_csv = export_invite_list(seg)
        assert "Bad" in manifest_csv
        assert "critical" in manifest_csv.lower()

    def test_manifest_has_included_yes_for_clean_records(self):
        _make_person(given_name="Clean", family_name="Record", consent_contact=True)
        seg = _make_segment()
        _, manifest_csv = export_invite_list(seg)
        assert "yes" in manifest_csv

    def test_manifest_has_included_no_for_excluded_records(self):
        _make_person(given_name="No", family_name="Consent", consent_contact=False)
        seg = _make_segment()
        _, manifest_csv = export_invite_list(seg)
        assert "no" in manifest_csv

    def test_formula_injection_escaped_in_invite(self):
        _make_person(given_name="=SUM(A1)", family_name="Hack", consent_contact=True)
        seg = _make_segment()
        invite_csv, _ = export_invite_list(seg)
        # Cell value must be prefixed with ' so it is not executed as a formula.
        # The raw value should not appear at the start of any CSV cell (after a comma).
        assert ",=SUM" not in invite_csv
        assert "'=SUM" in invite_csv

    def test_formula_injection_escaped_in_manifest(self):
        _make_person(given_name="-DANGER", family_name="Person", consent_contact=False)
        seg = _make_segment()
        _, manifest_csv = export_invite_list(seg)
        assert ",-DANGER" not in manifest_csv

    def test_segment_filter_applied_to_export(self):
        _make_person(
            given_name="European",
            family_name="Person",
            consent_contact=True,
            continent="Europe",
        )
        _make_person(
            given_name="Asian",
            family_name="Person",
            consent_contact=True,
            continent="Asia",
        )
        seg = _make_segment(filters={"continents": ["Europe"]})
        invite_csv, _ = export_invite_list(seg)
        assert "European" in invite_csv
        assert "Asian" not in invite_csv

    def test_manifest_includes_match_reasons(self):
        _make_person(given_name="Consenting", family_name="Person", consent_contact=True)
        seg = _make_segment(filters={"consent_contact": True})
        _, manifest_csv = export_invite_list(seg)
        assert "consent" in manifest_csv.lower()


@pytest.mark.django_db
class TestBuildInviteZip:
    def test_zip_contains_both_files(self):
        _make_person(given_name="A", family_name="B", consent_contact=True)
        seg = _make_segment()
        zip_bytes = build_invite_zip(seg)
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
        assert len(names) == 3
        assert any("invite" in n for n in names)
        assert any("manifest" in n for n in names)
        assert "export_metadata.json" in names

    def test_zip_is_valid(self):
        seg = _make_segment()
        zip_bytes = build_invite_zip(seg)
        assert zipfile.is_zipfile(io.BytesIO(zip_bytes))
