"""Tests for enrichment trigger views."""

from __future__ import annotations

import pytest

from core.models import Organization, Person, Publication


@pytest.fixture()
def pub(db):
    return Publication.objects.create(title="Test Pub", doi="10.1234/test")


@pytest.fixture()
def person_with_orcid(db):
    return Person.objects.create(
        given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789"
    )


@pytest.fixture()
def org_with_ror(db):
    return Organization.objects.create(name="Test Org", ror_id="https://ror.org/test")


# ---------------------------------------------------------------------------
# Auth: unauthenticated redirects to login
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_person_openalex_requires_login(client, person_with_orcid):
    resp = client.post(f"/enrichment/person/{person_with_orcid.pk}/openalex/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]


@pytest.mark.django_db
def test_enrich_pub_crossref_requires_login(client, pub):
    resp = client.post(f"/enrichment/publication/{pub.pk}/crossref/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]


# ---------------------------------------------------------------------------
# Auth: Contributor cannot enrich (Organizer+ required)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_person_openalex_requires_organizer(client, contributor, person_with_orcid):
    client.force_login(contributor)
    resp = client.post(f"/enrichment/person/{person_with_orcid.pk}/openalex/")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Organizer can trigger enrichment
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_person_openalex_organizer_ok(client, organizer, person_with_orcid):
    client.force_login(organizer)

    def fake_fetcher(orcid):
        return {"results": [{"display_name": "A. Lovelace"}]}

    import enrichment.services as svc

    # Patch via module-level replacement for this test
    _original = svc.enrich_person_from_openalex

    def patched(person, *, fetcher=None):
        return _original(person, fetcher=fake_fetcher)

    svc.enrich_person_from_openalex = patched
    try:
        resp = client.post(f"/enrichment/person/{person_with_orcid.pk}/openalex/")
    finally:
        svc.enrich_person_from_openalex = _original

    assert resp.status_code == 302
    assert f"/people/{person_with_orcid.pk}/" in resp["Location"]


@pytest.mark.django_db
def test_enrich_org_openalex_organizer_ok(client, organizer, org_with_ror):
    client.force_login(organizer)
    resp = client.post(f"/enrichment/organization/{org_with_ror.pk}/openalex/")
    # Logs a SKIPPED or ERROR (no real HTTP call in tests) but redirects correctly
    assert resp.status_code == 302
    assert f"/organizations/{org_with_ror.pk}/" in resp["Location"]


@pytest.mark.django_db
def test_enrich_org_wikidata_organizer_ok(client, organizer, org_with_ror):
    client.force_login(organizer)
    resp = client.post(f"/enrichment/organization/{org_with_ror.pk}/wikidata/")
    assert resp.status_code == 302
    assert f"/organizations/{org_with_ror.pk}/" in resp["Location"]


@pytest.mark.django_db
def test_enrich_pub_crossref_organizer_ok(client, organizer, pub):
    client.force_login(organizer)
    resp = client.post(f"/enrichment/publication/{pub.pk}/crossref/")
    assert resp.status_code == 302
    assert f"/publications/{pub.pk}/" in resp["Location"]


@pytest.mark.django_db
def test_enrich_pub_openalex_organizer_ok(client, organizer, pub):
    client.force_login(organizer)
    resp = client.post(f"/enrichment/publication/{pub.pk}/openalex/")
    assert resp.status_code == 302
    assert f"/publications/{pub.pk}/" in resp["Location"]


# ---------------------------------------------------------------------------
# 404 for non-existent objects
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_person_openalex_404(client, organizer):
    import uuid

    client.force_login(organizer)
    resp = client.post(f"/enrichment/person/{uuid.uuid4()}/openalex/")
    assert resp.status_code == 404
