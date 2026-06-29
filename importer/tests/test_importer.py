import pytest

from core.models import Affiliation, Organization, Person
from importer.models import ImportSession
from importer.services import apply_import, parse_csv, run_preview


@pytest.fixture
def session(db):
    return ImportSession.objects.create(
        raw_csv="given_name,family_name\nAda,Lovelace\n",
        column_mapping={"given_name": "given_name", "family_name": "family_name"},
        source_label="test-import",
    )


class TestParseCSV:
    def test_basic_parse(self):
        raw = "first,last,email\nAda,Lovelace,ada@example.com\n"
        mapping = {"first": "given_name", "last": "family_name", "email": "email"}
        rows = parse_csv(raw, mapping)
        assert len(rows) == 1
        assert rows[0]["given_name"] == "Ada"
        assert rows[0]["family_name"] == "Lovelace"
        assert rows[0]["email"] == "ada@example.com"

    def test_ignores_unmapped_columns(self):
        raw = "first,last,phone\nAda,Lovelace,555-0100\n"
        mapping = {"first": "given_name", "last": "family_name"}
        rows = parse_csv(raw, mapping)
        assert "phone" not in rows[0]
        assert "given_name" in rows[0]

    def test_multiple_rows(self):
        raw = "first,last\nAda,Lovelace\nGrace,Hopper\n"
        mapping = {"first": "given_name", "last": "family_name"}
        rows = parse_csv(raw, mapping)
        assert len(rows) == 2


@pytest.mark.django_db
class TestRunPreview:
    def test_dry_run_makes_no_writes(self, db):
        rows = [{"given_name": "New", "family_name": "Person", "email": "new@example.com"}]
        run_preview(rows)
        assert Person.objects.count() == 0

    def test_creates_for_new_person(self, db):
        rows = [{"given_name": "New", "family_name": "Person"}]
        result = run_preview(rows)
        assert len(result.creates) == 1
        assert result.creates[0].action == "create"

    def test_updates_for_orcid_match(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789")
        rows = [{"given_name": "Ada", "family_name": "Changed", "orcid": "0000-0001-2345-6789"}]
        result = run_preview(rows)
        assert len(result.updates) == 1
        assert result.updates[0].action == "update"

    def test_updates_for_email_match(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", email="ada@example.com")
        rows = [{"given_name": "Ada", "family_name": "Changed", "email": "ada@example.com"}]
        result = run_preview(rows)
        assert len(result.updates) == 1

    def test_updates_for_name_org_match(self, db):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        org = Organization.objects.create(name="Test Uni")
        Affiliation.objects.create(person=person, organization=org)
        rows = [
            {
                "given_name": "Ada",
                "family_name": "Lovelace",
                "organization": "Test Uni",
                "email": "new@example.com",
            }
        ]
        result = run_preview(rows)
        assert len(result.updates) == 1

    def test_unchanged_when_no_diff(self, db):
        Person.objects.create(given_name="Ada", family_name="Lovelace", email="ada@example.com")
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "email": "ada@example.com"}]
        result = run_preview(rows)
        assert len(result.unchanged) == 1

    def test_error_when_both_names_missing(self, db):
        rows = [{"email": "nobody@example.com"}]
        result = run_preview(rows)
        assert len(result.errors) == 1
        assert result.errors[0].error != ""

    def test_warns_on_invalid_orcid(self, db):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "orcid": "not-an-orcid"}]
        result = run_preview(rows)
        assert len(result.creates) == 1
        assert any("ORCID" in w for w in result.creates[0].warnings)

    def test_total_count(self, db):
        Person.objects.create(given_name="Existing", family_name="Person")
        rows = [
            {"given_name": "New", "family_name": "One"},
            {"given_name": "Existing", "family_name": "Person"},
        ]
        result = run_preview(rows)
        assert result.total == 2


@pytest.mark.django_db
class TestApplyImport:
    def test_creates_person(self, session):
        rows = [{"given_name": "New", "family_name": "Person"}]
        counts = apply_import(rows, "test", session)
        assert counts["created"] == 1
        assert Person.objects.filter(family_name="Person").exists()

    def test_updates_person_by_orcid(self, session):
        person = Person.objects.create(
            given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789"
        )
        rows = [
            {
                "given_name": "Ada",
                "family_name": "Lovelace",
                "orcid": "0000-0001-2345-6789",
                "email": "updated@example.com",
            }
        ]
        counts = apply_import(rows, "test", session)
        assert counts["updated"] == 1
        person.refresh_from_db()
        assert person.email == "updated@example.com"

    def test_creates_organization_and_links_via_affiliation(self, session):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "organization": "Test University"}]
        apply_import(rows, "test", session)
        assert Organization.objects.filter(name="Test University").exists()
        person = Person.objects.get(family_name="Lovelace")
        assert Affiliation.objects.filter(person=person).exists()

    def test_reuses_existing_organization(self, session):
        Organization.objects.create(name="Existing Uni")
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "organization": "Existing Uni"}]
        apply_import(rows, "test", session)
        assert Organization.objects.filter(name__icontains="Uni").count() == 1

    def test_unchanged_count(self, session):
        Person.objects.create(given_name="Ada", family_name="Lovelace")
        rows = [{"given_name": "Ada", "family_name": "Lovelace"}]
        counts = apply_import(rows, "test", session)
        assert counts["unchanged"] == 1

    def test_error_count_for_missing_name(self, session):
        rows = [{"email": "nobody@example.com"}]
        counts = apply_import(rows, "test", session)
        assert counts["errors"] == 1
        assert Person.objects.count() == 0

    def test_full_name_split_given_family_order(self, session):
        rows = [{"full_name": "Ada Lovelace"}]
        counts = apply_import(rows, "test", session)
        assert counts["created"] == 1
        p = Person.objects.get()
        assert p.given_name == "Ada"
        assert p.family_name == "Lovelace"

    def test_full_name_split_comma_format(self, session):
        rows = [{"full_name": "Lovelace, Ada"}]
        counts = apply_import(rows, "test", session)
        assert counts["created"] == 1
        p = Person.objects.get()
        assert p.given_name == "Ada"
        assert p.family_name == "Lovelace"

    def test_full_name_ignored_when_given_family_present(self, session):
        rows = [{"full_name": "Should Ignore", "given_name": "Ada", "family_name": "Lovelace"}]
        counts = apply_import(rows, "test", session)
        assert counts["created"] == 1
        p = Person.objects.get()
        assert p.given_name == "Ada"
        assert p.family_name == "Lovelace"

    def test_full_country_name_normalized_to_alpha2(self, session):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "country": "Canada"}]
        counts = apply_import(rows, "test", session)
        assert counts["created"] == 1
        p = Person.objects.get()
        assert p.country == "CA"

    def test_usa_full_name_normalized(self, session):
        rows = [{"given_name": "Grace", "family_name": "Hopper", "country": "United States"}]
        apply_import(rows, "test", session)
        p = Person.objects.get()
        assert p.country == "US"

    def test_unrecognized_country_blanked(self, session):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "country": "Narnia"}]
        apply_import(rows, "test", session)
        p = Person.objects.get()
        assert p.country == ""


@pytest.mark.django_db
class TestPreviewFullNameAndCountry:
    def test_preview_full_name_creates(self, db):
        rows = [{"full_name": "Grace Hopper"}]
        result = run_preview(rows)
        assert len(result.creates) == 1
        row_data = result.creates[0].data
        assert row_data["given_name"] == "Grace"
        assert row_data["family_name"] == "Hopper"

    def test_preview_warns_on_unrecognized_country(self, db):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "country": "Narnia"}]
        result = run_preview(rows)
        assert len(result.creates) == 1
        assert any("Narnia" in w for w in result.creates[0].warnings)

    def test_preview_no_warning_for_valid_country_name(self, db):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "country": "Canada"}]
        result = run_preview(rows)
        assert len(result.creates) == 1
        assert not any("not recognized" in w for w in result.creates[0].warnings)

    def test_preview_no_internal_country_raw_in_data(self, db):
        rows = [{"given_name": "Ada", "family_name": "Lovelace", "country": "Canada"}]
        result = run_preview(rows)
        assert "_country_raw" not in result.creates[0].data
