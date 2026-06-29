import pytest

from core.models import Person
from exporter.services import escape_cell, export_people_csv


class TestEscapeCell:
    def test_equals_prefix(self):
        assert escape_cell("=SUM(A1)").startswith("'")

    def test_plus_prefix(self):
        assert escape_cell("+1").startswith("'")

    def test_minus_prefix(self):
        assert escape_cell("-1").startswith("'")

    def test_at_prefix(self):
        assert escape_cell("@user").startswith("'")

    def test_tab_prefix(self):
        assert escape_cell("\tinjected").startswith("'")

    def test_normal_text_unchanged(self):
        assert escape_cell("Ada Lovelace") == "Ada Lovelace"

    def test_empty_string_unchanged(self):
        assert escape_cell("") == ""

    def test_value_preserved_after_escape(self):
        assert escape_cell("=DANGER") == "'=DANGER"


@pytest.mark.django_db
class TestExportPeopleCSV:
    def test_basic_output(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name", "family_name"])
        assert "Ada" in csv_out
        assert "Lovelace" in csv_out

    def test_headers_present(self, db):
        Person.objects.create(given_name="A", family_name="B")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name", "family_name"])
        lines = csv_out.strip().split("\r\n")
        assert "Given name" in lines[0]
        assert "Family name" in lines[0]

    def test_column_selection(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace")
        qs = Person.objects.all()
        # Only request given_name — family_name should not appear in header
        csv_out = export_people_csv(qs, ["given_name"])
        assert "Given name" in csv_out
        assert "Family name" not in csv_out

    def test_notes_private_excluded_by_default(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", notes_private="SECRET")
        qs = Person.objects.all()
        # Not including notes_private in columns
        csv_out = export_people_csv(qs, ["given_name", "family_name"])
        assert "SECRET" not in csv_out

    def test_notes_private_included_when_selected(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", notes_private="SECRET")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name", "notes_private"])
        assert "SECRET" in csv_out

    def test_bom_included_when_requested(self, db):
        Person.objects.create(given_name="A", family_name="B")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name"], include_bom=True)
        assert csv_out.startswith("﻿")

    def test_no_bom_by_default(self, db):
        Person.objects.create(given_name="A", family_name="B")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name"], include_bom=False)
        assert not csv_out.startswith("﻿")

    def test_formula_injection_escaped_in_name(self, db):
        Person.objects.create(given_name="=HYPERLINK(evil)", family_name="Test")
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["given_name", "family_name"])
        assert "'=HYPERLINK(evil)" in csv_out

    def test_consent_rendered_as_yes_no(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", consent_contact=True)
        qs = Person.objects.all()
        csv_out = export_people_csv(qs, ["consent_contact"])
        assert "Yes" in csv_out

    def test_empty_queryset(self, db):
        qs = Person.objects.none()
        csv_out = export_people_csv(qs, ["given_name", "family_name"])
        lines = [line for line in csv_out.strip().split("\r\n") if line]
        assert len(lines) == 1  # header only
