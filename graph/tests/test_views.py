"""Tests for graph/views.py — auth, response types, and content."""

import csv
import datetime
import io
import json
import zipfile

import pytest
from django.urls import reverse

from core.models import Person
from events.models import Event, Participation


def _person(**kw) -> Person:
    defaults = {"given_name": "Ada", "family_name": "Lovelace", "consent_public_profile": True}
    defaults.update(kw)
    return Person.objects.create(**defaults)


def _event(**kw) -> Event:
    defaults = {"name": "Test Event", "start_date": datetime.date(2024, 6, 1)}
    defaults.update(kw)
    return Event.objects.create(**defaults)


def _unpack_zip(response) -> dict[str, bytes]:
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


# ── Auth guards ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAuthGuards:
    def test_export_index_requires_login(self, client):
        resp = client.get(reverse("graph:export_index"))
        assert resp.status_code in (302, 403)

    def test_kgx_full_requires_login(self, client):
        resp = client.get(reverse("graph:kgx_full"))
        assert resp.status_code in (302, 403)

    def test_viewer_cannot_access_export_index(self, client, viewer):
        client.force_login(viewer)
        resp = client.get(reverse("graph:export_index"))
        assert resp.status_code == 403

    def test_contributor_cannot_access_export_index(self, client, contributor):
        client.force_login(contributor)
        resp = client.get(reverse("graph:export_index"))
        assert resp.status_code == 403

    def test_organizer_can_access_export_index(self, client, organizer):
        client.force_login(organizer)
        resp = client.get(reverse("graph:export_index"))
        assert resp.status_code == 200


@pytest.mark.django_db
def test_invalid_hops_falls_back_to_one(client, organizer):
    person = _person()
    client.force_login(organizer)
    response = client.get(
        reverse("graph:kgx_person_neighbourhood", kwargs={"pk": person.pk}),
        {"hops": "not-a-number"},
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"


# ── KGX full ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestKGXFullExportView:
    def test_returns_zip(self, client, organizer):
        client.force_login(organizer)
        resp = client.get(reverse("graph:kgx_full"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"
        assert "heddle_kgx_full" in resp["Content-Disposition"]

    def test_zip_contains_required_files(self, client, organizer):
        client.force_login(organizer)
        resp = client.get(reverse("graph:kgx_full"))
        files = _unpack_zip(resp)
        assert "nodes.tsv" in files
        assert "edges.tsv" in files
        assert "manifest.json" in files

    def test_manifest_is_valid_json(self, client, organizer):
        client.force_login(organizer)
        resp = client.get(reverse("graph:kgx_full"))
        files = _unpack_zip(resp)
        manifest = json.loads(files["manifest.json"])
        assert manifest["slice"] == "full"
        assert "generated_at" in manifest


# ── KGX event ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestKGXEventExportView:
    def test_returns_zip_for_event(self, client, organizer):
        client.force_login(organizer)
        event = _event()
        resp = client.get(reverse("graph:kgx_event", kwargs={"pk": event.pk}))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"

    def test_404_for_unknown_event(self, client, organizer):
        import uuid

        client.force_login(organizer)
        resp = client.get(reverse("graph:kgx_event", kwargs={"pk": uuid.uuid4()}))
        assert resp.status_code == 404

    def test_event_manifest_names_event_slice(self, client, organizer):
        client.force_login(organizer)
        event = _event()
        resp = client.get(reverse("graph:kgx_event", kwargs={"pk": event.pk}))
        files = _unpack_zip(resp)
        manifest = json.loads(files["manifest.json"])
        assert str(event.pk) in manifest["slice"]


# ── KGX person neighbourhood ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestKGXPersonNeighbourhoodView:
    def test_returns_zip(self, client, organizer):
        client.force_login(organizer)
        p = _person()
        resp = client.get(reverse("graph:kgx_person_neighbourhood", kwargs={"pk": p.pk}))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"

    def test_hops_param_respected(self, client, organizer):
        client.force_login(organizer)
        p = _person()
        resp = client.get(
            reverse("graph:kgx_person_neighbourhood", kwargs={"pk": p.pk}) + "?hops=2"
        )
        files = _unpack_zip(resp)
        manifest = json.loads(files["manifest.json"])
        assert manifest["slice"].endswith(":2")

    def test_hops_capped_at_3(self, client, organizer):
        client.force_login(organizer)
        p = _person()
        resp = client.get(
            reverse("graph:kgx_person_neighbourhood", kwargs={"pk": p.pk}) + "?hops=99"
        )
        files = _unpack_zip(resp)
        manifest = json.loads(files["manifest.json"])
        assert manifest["slice"].endswith(":3")

    def test_404_for_unknown_person(self, client, organizer):
        import uuid

        client.force_login(organizer)
        resp = client.get(reverse("graph:kgx_person_neighbourhood", kwargs={"pk": uuid.uuid4()}))
        assert resp.status_code == 404


# ── Badge CSV event ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBadgeCSVEventExportView:
    def test_returns_zip(self, client, organizer):
        client.force_login(organizer)
        event = _event()
        resp = client.get(reverse("graph:badge_event", kwargs={"pk": event.pk}))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/zip"

    def test_zip_contains_badges_and_manifest(self, client, organizer):
        client.force_login(organizer)
        event = _event()
        resp = client.get(reverse("graph:badge_event", kwargs={"pk": event.pk}))
        files = _unpack_zip(resp)
        assert "badges.csv" in files
        assert "manifest.json" in files

    def test_only_consenting_participants_in_badges_csv(self, client, organizer):
        client.force_login(organizer)
        p_yes = _person(given_name="Alice")
        p_no = _person(given_name="Bob", family_name="Smith", consent_public_profile=False)
        event = _event()
        Participation.objects.create(person=p_yes, event=event)
        Participation.objects.create(person=p_no, event=event)

        resp = client.get(reverse("graph:badge_event", kwargs={"pk": event.pk}))
        files = _unpack_zip(resp)
        csv_text = files["badges.csv"].decode()
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        assert len(rows) == 1
        assert rows[0]["display_name"] == "Alice Lovelace"

    def test_404_for_unknown_event(self, client, organizer):
        import uuid

        client.force_login(organizer)
        resp = client.get(reverse("graph:badge_event", kwargs={"pk": uuid.uuid4()}))
        assert resp.status_code == 404
