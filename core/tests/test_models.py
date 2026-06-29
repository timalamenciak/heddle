import pytest

from core.models import Affiliation, Organization, Person


@pytest.mark.django_db
class TestPerson:
    def test_str(self):
        p = Person(given_name="Ada", family_name="Lovelace")
        assert str(p) == "Ada Lovelace"

    def test_name_normalized_on_save(self, db):
        p = Person.objects.create(given_name="Ada", family_name="Lovelace")
        assert p.name_normalized == "ada lovelace"

    def test_name_normalized_collapses_whitespace(self, db):
        p = Person.objects.create(given_name="  Ada  ", family_name=" Lovelace ")
        assert p.name_normalized == "ada lovelace"

    def test_full_name_property(self):
        p = Person(given_name="Grace", family_name="Hopper")
        assert p.full_name == "Grace Hopper"

    def test_primary_organization_returns_none_without_affiliation(self, db):
        p = Person.objects.create(given_name="X", family_name="Y")
        assert p.primary_organization is None

    def test_primary_organization_returns_primary_affiliation(self, db):
        p = Person.objects.create(given_name="X", family_name="Y")
        org = Organization.objects.create(name="Test Org")
        Affiliation.objects.create(person=p, organization=org, is_primary=True)
        assert p.primary_organization == org

    def test_default_metadata_status_is_unreviewed(self, db):
        p = Person.objects.create(given_name="X", family_name="Y")
        assert p.metadata_status == "unreviewed"

    def test_orcid_unique(self, db):
        from django.db import IntegrityError

        Person.objects.create(given_name="A", family_name="B", orcid="0000-0001-2345-6789")
        with pytest.raises(IntegrityError):
            Person.objects.create(given_name="C", family_name="D", orcid="0000-0001-2345-6789")


@pytest.mark.django_db
class TestOrganization:
    def test_str(self):
        org = Organization(name="University of Toronto")
        assert str(org) == "University of Toronto"

    def test_name_normalized_on_save(self, db):
        org = Organization.objects.create(name="University of Toronto")
        assert org.name_normalized == "university of toronto"


@pytest.mark.django_db
class TestAffiliation:
    def test_str(self, db):
        p = Person.objects.create(given_name="Ada", family_name="Lovelace")
        org = Organization.objects.create(name="Uni")
        aff = Affiliation.objects.create(person=p, organization=org)
        assert "Ada Lovelace" in str(aff)
        assert "Uni" in str(aff)

    def test_unique_constraint(self, db):
        from django.db import IntegrityError

        p = Person.objects.create(given_name="X", family_name="Y")
        org = Organization.objects.create(name="Org")
        Affiliation.objects.create(person=p, organization=org)
        with pytest.raises(IntegrityError):
            Affiliation.objects.create(person=p, organization=org)
