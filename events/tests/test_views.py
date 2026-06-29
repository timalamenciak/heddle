"""Tests for events and segment views."""

import datetime
import io
import zipfile

import pytest
from django.urls import reverse

from core.models import Person
from events.models import Event, Participation, ParticipationStatus, SavedSegment


def _make_event(**kwargs):
    kwargs.setdefault("start_date", datetime.date(2025, 6, 1))
    kwargs.setdefault("name", "Test Event")
    return Event.objects.create(**kwargs)


def _make_person(**kwargs):
    kwargs.setdefault("given_name", "Ada")
    kwargs.setdefault("family_name", "Lovelace")
    return Person.objects.create(**kwargs)


@pytest.mark.django_db
class TestEventListView:
    def test_requires_login(self, client):
        response = client.get(reverse("events:event_list"))
        assert response.status_code == 302

    def test_viewer_can_access(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("events:event_list"))
        assert response.status_code == 200

    def test_lists_events(self, client, contributor):
        _make_event(name="EcoHack 2025")
        client.force_login(contributor)
        response = client.get(reverse("events:event_list"))
        assert b"EcoHack 2025" in response.content


@pytest.mark.django_db
class TestEventCreateView:
    def test_contributor_cannot_create(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("events:event_create"))
        assert response.status_code == 403

    def test_organizer_can_create(self, client, organizer):
        client.force_login(organizer)
        response = client.get(reverse("events:event_create"))
        assert response.status_code == 200

    def test_post_creates_event(self, client, organizer):
        client.force_login(organizer)
        response = client.post(
            reverse("events:event_create"),
            {
                "name": "New Event",
                "event_type": "workshop",
                "start_date": "2025-09-01",
            },
        )
        assert response.status_code == 302
        assert Event.objects.filter(name="New Event").exists()

    def test_created_by_set_to_user(self, client, organizer):
        client.force_login(organizer)
        client.post(
            reverse("events:event_create"),
            {"name": "Attributed Event", "event_type": "workshop", "start_date": "2025-09-01"},
        )
        event = Event.objects.get(name="Attributed Event")
        assert event.created_by == organizer


@pytest.mark.django_db
class TestEventDetailView:
    def test_shows_roster(self, client, contributor):
        event = _make_event(name="OERC 2025")
        person = _make_person()
        Participation.objects.create(person=person, event=event, status="confirmed")
        client.force_login(contributor)
        response = client.get(reverse("events:event_detail", kwargs={"pk": event.pk}))
        assert response.status_code == 200
        assert b"Ada Lovelace" in response.content

    def test_requires_login(self, client):
        event = _make_event()
        response = client.get(reverse("events:event_detail", kwargs={"pk": event.pk}))
        assert response.status_code == 302


@pytest.mark.django_db
class TestParticipationAddView:
    def test_contributor_cannot_add(self, client, contributor):
        event = _make_event()
        response = client.post(reverse("events:participation_add", kwargs={"pk": event.pk}), {})
        assert response.status_code == 302  # redirect to login (not authenticated)
        client.force_login(contributor)
        response = client.post(reverse("events:participation_add", kwargs={"pk": event.pk}), {})
        assert response.status_code == 403

    def test_organizer_can_add(self, client, organizer):
        event = _make_event()
        person = _make_person()
        client.force_login(organizer)
        response = client.post(
            reverse("events:participation_add", kwargs={"pk": event.pk}),
            {"person": str(person.pk), "role": "attendee", "status": "invited"},
        )
        assert response.status_code == 302
        assert Participation.objects.filter(person=person, event=event).exists()

    def test_duplicate_add_is_graceful(self, client, organizer):
        event = _make_event()
        person = _make_person()
        Participation.objects.create(person=person, event=event)
        client.force_login(organizer)
        response = client.post(
            reverse("events:participation_add", kwargs={"pk": event.pk}),
            {"person": str(person.pk), "role": "attendee", "status": "invited"},
        )
        assert response.status_code == 302
        assert Participation.objects.filter(person=person, event=event).count() == 1


@pytest.mark.django_db
class TestParticipationBulkStatusView:
    def test_bulk_update_changes_status(self, client, organizer):
        event = _make_event()
        person = _make_person()
        p = Participation.objects.create(
            person=person, event=event, status=ParticipationStatus.INVITED
        )
        client.force_login(organizer)
        client.post(
            reverse("events:participation_bulk", kwargs={"pk": event.pk}),
            {"participation_ids": [str(p.pk)], "new_status": "confirmed"},
        )
        p.refresh_from_db()
        assert p.status == ParticipationStatus.CONFIRMED

    def test_invalid_status_rejected(self, client, organizer):
        event = _make_event()
        client.force_login(organizer)
        response = client.post(
            reverse("events:participation_bulk", kwargs={"pk": event.pk}),
            {"participation_ids": [], "new_status": "invalid_status"},
        )
        assert response.status_code == 302  # graceful redirect with error message


@pytest.mark.django_db
class TestSegmentListView:
    def test_requires_login(self, client):
        response = client.get(reverse("events:segment_list"))
        assert response.status_code == 302

    def test_viewer_cannot_access(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("events:segment_list"))
        assert response.status_code == 403

    def test_contributor_can_access(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("events:segment_list"))
        assert response.status_code == 200

    def test_lists_segments(self, client, contributor):
        SavedSegment.objects.create(name="Europe researchers", filters={})
        client.force_login(contributor)
        response = client.get(reverse("events:segment_list"))
        assert b"Europe researchers" in response.content


@pytest.mark.django_db
class TestSegmentCreateView:
    def test_contributor_cannot_create(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("events:segment_create"))
        assert response.status_code == 403

    def test_organizer_can_create(self, client, organizer):
        client.force_login(organizer)
        response = client.get(reverse("events:segment_create"))
        assert response.status_code == 200

    def test_post_saves_segment(self, client, organizer):
        client.force_login(organizer)
        response = client.post(
            reverse("events:segment_create"),
            {
                "name": "Europe + consent",
                "description": "Test",
                "continents": ["Europe"],
                "consent_contact": "on",
            },
        )
        assert response.status_code == 302
        seg = SavedSegment.objects.get(name="Europe + consent")
        assert seg.filters.get("continents") == ["Europe"]
        assert seg.filters.get("consent_contact") is True
        assert seg.created_by == organizer


@pytest.mark.django_db
class TestSegmentPreviewView:
    def test_contributor_can_view(self, client, contributor):
        seg = SavedSegment.objects.create(name="All", filters={})
        client.force_login(contributor)
        response = client.get(reverse("events:segment_preview", kwargs={"pk": seg.pk}))
        assert response.status_code == 200

    def test_shows_matched_people(self, client, contributor):
        _make_person(given_name="Jane", family_name="Doe", continent="Europe")
        seg = SavedSegment.objects.create(name="Europe", filters={"continents": ["Europe"]})
        client.force_login(contributor)
        response = client.get(reverse("events:segment_preview", kwargs={"pk": seg.pk}))
        assert b"Jane Doe" in response.content

    def test_why_matched_shown(self, client, contributor):
        _make_person(given_name="Jane", family_name="Doe", continent="Europe")
        seg = SavedSegment.objects.create(name="Europe", filters={"continents": ["Europe"]})
        client.force_login(contributor)
        response = client.get(reverse("events:segment_preview", kwargs={"pk": seg.pk}))
        assert b"Europe" in response.content


@pytest.mark.django_db
class TestSegmentPreviewPartialView:
    def test_post_returns_preview_html(self, client, contributor):
        _make_person(given_name="A", family_name="B", continent="Europe")
        client.force_login(contributor)
        response = client.post(
            reverse("events:segment_preview_partial"),
            {"continents": ["Europe"]},
        )
        assert response.status_code == 200
        assert b"A B" in response.content

    def test_no_matches_shows_empty_state(self, client, contributor):
        client.force_login(contributor)
        response = client.post(
            reverse("events:segment_preview_partial"),
            {"countries": ["ZZ"]},
        )
        assert response.status_code == 200
        assert b"No people match" in response.content


@pytest.mark.django_db
class TestInviteListExportView:
    def test_contributor_cannot_export(self, client, contributor):
        seg = SavedSegment.objects.create(name="S", filters={})
        client.force_login(contributor)
        response = client.get(reverse("events:segment_export", kwargs={"pk": seg.pk}))
        assert response.status_code == 403

    def test_organizer_gets_zip(self, client, organizer):
        seg = SavedSegment.objects.create(name="Test export", filters={})
        client.force_login(organizer)
        response = client.get(reverse("events:segment_export", kwargs={"pk": seg.pk}))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        assert zipfile.is_zipfile(io.BytesIO(response.content))

    def test_zip_contains_invite_and_manifest(self, client, organizer):
        seg = SavedSegment.objects.create(name="Test export", filters={})
        client.force_login(organizer)
        response = client.get(reverse("events:segment_export", kwargs={"pk": seg.pk}))
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
        assert any("invite" in n for n in names)
        assert any("manifest" in n for n in names)

    def test_non_consenting_excluded_from_invite_csv(self, client, organizer):
        _make_person(given_name="No", family_name="Consent", consent_contact=False)
        seg = SavedSegment.objects.create(name="All", filters={})
        client.force_login(organizer)
        response = client.get(reverse("events:segment_export", kwargs={"pk": seg.pk}))
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            invite_name = next(n for n in zf.namelist() if "invite" in n)
            invite_content = zf.read(invite_name).decode()
        data_rows = invite_content.strip().split("\n")[1:]
        assert not any("No" in row for row in data_rows)
