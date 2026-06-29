import pytest
from django.urls import reverse

from core.models import Organization, Person


@pytest.fixture
def person(db):
    return Person.objects.create(given_name="Ada", family_name="Lovelace", email="ada@example.com")


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test University")


@pytest.mark.django_db
class TestPersonListView:
    def test_requires_login(self, client):
        response = client.get(reverse("core:person_list"))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_viewer_can_access(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_list"))
        assert response.status_code == 200

    def test_shows_people(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_list"))
        assert b"Ada" in response.content

    def test_filter_by_country(self, client, viewer):
        Person.objects.create(given_name="Canadian", family_name="Researcher", country="CA")
        Person.objects.create(given_name="American", family_name="Researcher2", country="US")
        client.force_login(viewer)
        response = client.get(reverse("core:person_list"), {"country": "CA"})
        assert response.status_code == 200
        assert b"Canadian" in response.content
        assert b"American" not in response.content

    def test_htmx_returns_partial(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_list"), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        # Partial should not contain the full HTML skeleton
        assert b"<!DOCTYPE" not in response.content

    def test_filter_missing_orcid(self, client, viewer):
        Person.objects.create(given_name="Has", family_name="ORCID", orcid="0000-0001-2345-6789")
        Person.objects.create(given_name="No", family_name="ORCID")
        client.force_login(viewer)
        response = client.get(reverse("core:person_list"), {"missing_orcid": "on"})
        assert b"No ORCID" in response.content


@pytest.mark.django_db
class TestPersonDetailView:
    def test_requires_login(self, client, person):
        response = client.get(reverse("core:person_detail", kwargs={"pk": person.pk}))
        assert response.status_code == 302

    def test_shows_person(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_detail", kwargs={"pk": person.pk}))
        assert response.status_code == 200
        assert b"Ada" in response.content


@pytest.mark.django_db
class TestPersonEditView:
    def test_viewer_cannot_edit(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_edit", kwargs={"pk": person.pk}))
        assert response.status_code == 403

    def test_contributor_can_edit(self, client, contributor, person):
        client.force_login(contributor)
        response = client.get(reverse("core:person_edit", kwargs={"pk": person.pk}))
        assert response.status_code == 200

    def test_edit_saves_changes(self, client, contributor, person):
        client.force_login(contributor)
        response = client.post(
            reverse("core:person_edit", kwargs={"pk": person.pk}),
            {
                "given_name": "Ada",
                "family_name": "Lovelace",
                "email": "ada2@example.com",
                "metadata_status": "verified",
                # omitting consent booleans -> unchecked (False) in Django form
            },
        )
        assert response.status_code == 302
        person.refresh_from_db()
        assert person.email == "ada2@example.com"

    def test_admin_cannot_see_private_notes_in_viewer_form(self, client, viewer, person):
        client.force_login(viewer)
        response = client.get(reverse("core:person_edit", kwargs={"pk": person.pk}))
        # Viewer gets 403, not the form
        assert response.status_code == 403


@pytest.mark.django_db
class TestPersonCreateView:
    def test_viewer_cannot_create(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("core:person_create"))
        assert response.status_code == 403

    def test_contributor_can_access_create_form(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("core:person_create"))
        assert response.status_code == 200

    def test_create_person(self, client, contributor):
        client.force_login(contributor)
        response = client.post(
            reverse("core:person_create"),
            {
                "given_name": "Grace",
                "family_name": "Hopper",
                "metadata_status": "unreviewed",
            },
        )
        assert response.status_code == 302
        assert Person.objects.filter(family_name="Hopper").exists()
