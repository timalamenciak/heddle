"""Tests for MetadataSuggestion accept/reject/bulk-accept workflow."""

import pytest
from django.urls import reverse

from core.models import Person
from metadata.models import MetadataSuggestion, MetadataVerification, SuggestionStatus


def _make_person(**kwargs) -> Person:
    kwargs.setdefault("given_name", "Ada")
    kwargs.setdefault("family_name", "Lovelace")
    return Person.objects.create(**kwargs)


def _make_suggestion(person, field="given_name", current="Ada", suggested="Adelaide", **kwargs):
    kwargs.setdefault("source", "orcid_sync")
    kwargs.setdefault("confidence_score", 0.9)
    return MetadataSuggestion.objects.create(
        person=person,
        field_name=field,
        current_value=current,
        suggested_value=suggested,
        **kwargs,
    )


@pytest.mark.django_db
class TestSuggestionListView:
    def test_requires_login(self, client):
        response = client.get(reverse("metadata:suggestions"))
        assert response.status_code == 302

    def test_viewer_cannot_access(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("metadata:suggestions"))
        assert response.status_code == 403

    def test_contributor_can_view(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("metadata:suggestions"))
        assert response.status_code == 200

    def test_shows_open_suggestions(self, client, contributor):
        person = _make_person()
        _make_suggestion(person)
        client.force_login(contributor)
        response = client.get(reverse("metadata:suggestions"))
        assert b"given_name" in response.content


@pytest.mark.django_db
class TestSuggestionAcceptView:
    def test_contributor_cannot_accept(self, client, contributor):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(contributor)
        response = client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        assert response.status_code == 403

    def test_organizer_can_accept(self, client, organizer):
        person = _make_person(given_name="Ada")
        sug = _make_suggestion(person, field="given_name", current="Ada", suggested="Adelaide")
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        person.refresh_from_db()
        assert person.given_name == "Adelaide"

    def test_accept_marks_suggestion_accepted(self, client, organizer):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        sug.refresh_from_db()
        assert sug.status == SuggestionStatus.ACCEPTED

    def test_accept_creates_verification(self, client, organizer):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        assert MetadataVerification.objects.filter(person=person).exists()

    def test_accept_sets_reviewed_by(self, client, organizer):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        sug.refresh_from_db()
        assert sug.reviewed_by == organizer

    def test_accept_family_name(self, client, organizer):
        person = _make_person(family_name="Lovelace")
        sug = _make_suggestion(person, field="family_name", current="Lovelace", suggested="Byron")
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_accept", kwargs={"pk": sug.pk}))
        person.refresh_from_db()
        assert person.family_name == "Byron"


@pytest.mark.django_db
class TestSuggestionRejectView:
    def test_contributor_cannot_reject(self, client, contributor):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(contributor)
        response = client.post(reverse("metadata:suggestion_reject", kwargs={"pk": sug.pk}))
        assert response.status_code == 403

    def test_organizer_can_reject(self, client, organizer):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_reject", kwargs={"pk": sug.pk}))
        sug.refresh_from_db()
        assert sug.status == SuggestionStatus.REJECTED

    def test_reject_does_not_change_person_field(self, client, organizer):
        person = _make_person(given_name="Ada")
        sug = _make_suggestion(person, field="given_name", current="Ada", suggested="Adelaide")
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_reject", kwargs={"pk": sug.pk}))
        person.refresh_from_db()
        assert person.given_name == "Ada"

    def test_reject_does_not_create_verification(self, client, organizer):
        person = _make_person()
        sug = _make_suggestion(person)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_reject", kwargs={"pk": sug.pk}))
        assert not MetadataVerification.objects.filter(person=person).exists()


@pytest.mark.django_db
class TestSuggestionBulkAcceptView:
    def test_bulk_accepts_high_confidence_only(self, client, organizer):
        person = _make_person()
        high = _make_suggestion(person, field="given_name", confidence_score=0.9)
        low = _make_suggestion(person, field="family_name", confidence_score=0.5)
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_bulk_accept"))
        high.refresh_from_db()
        low.refresh_from_db()
        assert high.status == SuggestionStatus.ACCEPTED
        assert low.status == SuggestionStatus.OPEN

    def test_bulk_accept_updates_person_fields(self, client, organizer):
        person = _make_person(given_name="Ada")
        _make_suggestion(
            person, field="given_name", current="Ada", suggested="Adelaide", confidence_score=0.95
        )
        client.force_login(organizer)
        client.post(reverse("metadata:suggestion_bulk_accept"))
        person.refresh_from_db()
        assert person.given_name == "Adelaide"

    def test_contributor_cannot_bulk_accept(self, client, contributor):
        client.force_login(contributor)
        response = client.post(reverse("metadata:suggestion_bulk_accept"))
        assert response.status_code == 403
