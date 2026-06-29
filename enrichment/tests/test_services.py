"""Tests for enrichment services — mocked fetchers, DB-backed."""

from __future__ import annotations

import pytest

from core.models import Organization, Person, Publication
from enrichment.models import EnrichmentLog, EnrichmentStatus
from enrichment.services import (
    enrich_org_from_openalex,
    enrich_org_from_wikidata,
    enrich_person_from_openalex,
    enrich_publication_from_crossref,
    enrich_publication_from_openalex,
)
from metadata.models import MetadataSuggestion, SuggestionStatus

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_CROSSREF_RESPONSE = {
    "message": {
        "title": ["Restored Wetlands"],
        "published-print": {"date-parts": [[2022, 3]]},
        "type": "journal-article",
        "container-title": ["Wetlands"],
    }
}

_OA_WORK_RESPONSE = {
    "results": [
        {
            "title": "Restored Wetlands OA",
            "publication_year": 2022,
            "type": "article",
            "primary_location": {"source": {"display_name": "Wetlands OA"}},
        }
    ]
}

_OA_AUTHOR_RESPONSE = {"results": [{"display_name": "Jane Marie Smith"}]}

_OA_INST_RESPONSE = {
    "results": [
        {
            "display_name": "University of Test",
            "country_code": "CA",
            "type": "education",
            "homepage_url": "https://utest.example",
        }
    ]
}

_WD_SEARCH_RESPONSE = {"search": [{"id": "Q111", "label": "Test University"}]}
_WD_ENTITY_RESPONSE = {
    "entities": {
        "Q111": {
            "id": "Q111",
            "claims": {"P856": [{"mainsnak": {"datavalue": {"value": "https://utest.example"}}}]},
        }
    }
}


def _make_pub(doi: str = "10.1234/wetlands", **kwargs) -> Publication:
    return Publication.objects.create(title="Original Title", doi=doi, **kwargs)


def _make_person(orcid: str = "0000-0001-2345-6789") -> Person:
    return Person.objects.create(given_name="Jane", family_name="Doe", orcid=orcid)


def _make_org(ror_id: str = "https://ror.org/test") -> Organization:
    return Organization.objects.create(name="Test University", ror_id=ror_id)


# ---------------------------------------------------------------------------
# Publication — Crossref
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_pub_crossref_creates_suggestions():
    pub = _make_pub()
    sugs = enrich_publication_from_crossref(pub, fetcher=lambda doi: _CROSSREF_RESPONSE)
    assert len(sugs) >= 1
    titles = [s.field_name for s in sugs]
    assert "title" in titles
    assert all(s.source == "crossref" for s in sugs)
    assert all(s.publication_id == pub.pk for s in sugs)
    assert EnrichmentLog.objects.filter(source="crossref", status=EnrichmentStatus.OK).exists()


@pytest.mark.django_db
def test_enrich_pub_crossref_no_doi_skips():
    pub = _make_pub(doi="")
    sugs = enrich_publication_from_crossref(pub)
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.SKIPPED).exists()


@pytest.mark.django_db
def test_enrich_pub_crossref_no_duplicate_open_suggestions():
    pub = _make_pub()
    enrich_publication_from_crossref(pub, fetcher=lambda doi: _CROSSREF_RESPONSE)
    first_count = MetadataSuggestion.objects.filter(
        publication=pub, status=SuggestionStatus.OPEN
    ).count()
    # Second run should create no new open suggestions
    enrich_publication_from_crossref(pub, fetcher=lambda doi: _CROSSREF_RESPONSE)
    second_count = MetadataSuggestion.objects.filter(
        publication=pub, status=SuggestionStatus.OPEN
    ).count()
    assert first_count == second_count


@pytest.mark.django_db
def test_enrich_pub_crossref_no_suggestion_when_value_matches():
    pub = _make_pub()
    pub.title = "Restored Wetlands"
    pub.save()
    sugs = enrich_publication_from_crossref(pub, fetcher=lambda doi: _CROSSREF_RESPONSE)
    title_sugs = [s for s in sugs if s.field_name == "title"]
    assert title_sugs == [], "No suggestion when value already matches"


@pytest.mark.django_db
def test_enrich_pub_crossref_logs_error_on_exception():
    pub = _make_pub()

    def boom(doi):
        raise ConnectionError("timeout")

    sugs = enrich_publication_from_crossref(pub, fetcher=boom)
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.ERROR).exists()


# ---------------------------------------------------------------------------
# Publication — OpenAlex
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_pub_openalex_creates_suggestions():
    pub = _make_pub()
    sugs = enrich_publication_from_openalex(pub, fetcher=lambda doi: _OA_WORK_RESPONSE)
    assert len(sugs) >= 1
    assert all(s.source == "openalex" for s in sugs)


@pytest.mark.django_db
def test_enrich_pub_openalex_skips_when_no_result():
    pub = _make_pub()
    sugs = enrich_publication_from_openalex(pub, fetcher=lambda doi: {"results": []})
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.SKIPPED).exists()


# ---------------------------------------------------------------------------
# Person — OpenAlex
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_person_openalex_creates_suggestions():
    person = _make_person()
    sugs = enrich_person_from_openalex(person, fetcher=lambda orcid: _OA_AUTHOR_RESPONSE)
    assert len(sugs) >= 1
    fields = {s.field_name for s in sugs}
    assert "given_name" in fields or "family_name" in fields
    assert all(s.person_id == person.pk for s in sugs)


@pytest.mark.django_db
def test_enrich_person_openalex_skips_without_orcid():
    person = Person.objects.create(given_name="No", family_name="ORCID")
    sugs = enrich_person_from_openalex(person)
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.SKIPPED).exists()


@pytest.mark.django_db
def test_enrich_person_openalex_no_suggestion_when_name_matches():
    person = _make_person()
    person.given_name = "Jane Marie"
    person.family_name = "Smith"
    person.save()
    sugs = enrich_person_from_openalex(person, fetcher=lambda orcid: _OA_AUTHOR_RESPONSE)
    assert sugs == []


# ---------------------------------------------------------------------------
# Organization — OpenAlex
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_org_openalex_creates_suggestions():
    org = _make_org()
    sugs = enrich_org_from_openalex(org, fetcher=lambda ror: _OA_INST_RESPONSE)
    assert len(sugs) >= 1
    assert all(s.organization_id == org.pk for s in sugs)
    assert all(s.source == "openalex" for s in sugs)


@pytest.mark.django_db
def test_enrich_org_openalex_skips_without_ror():
    org = Organization.objects.create(name="No ROR")
    sugs = enrich_org_from_openalex(org)
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.SKIPPED).exists()


@pytest.mark.django_db
def test_enrich_org_openalex_skips_when_no_result():
    org = _make_org()
    sugs = enrich_org_from_openalex(org, fetcher=lambda ror: {"results": []})
    assert sugs == []


# ---------------------------------------------------------------------------
# Organization — Wikidata (search path)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_org_wikidata_search_suggests_qid():
    org = Organization.objects.create(name="Test University")
    sugs = enrich_org_from_wikidata(org, fetcher=lambda name: _WD_SEARCH_RESPONSE)
    assert len(sugs) == 1
    assert sugs[0].field_name == "wikidata_qid"
    assert sugs[0].suggested_value == "Q111"
    assert sugs[0].confidence_score == pytest.approx(0.5)
    assert sugs[0].source == "wikidata"


@pytest.mark.django_db
def test_enrich_org_wikidata_search_no_result():
    org = Organization.objects.create(name="Unknown Org")
    sugs = enrich_org_from_wikidata(org, fetcher=lambda name: {"search": []})
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.OK).exists()


# ---------------------------------------------------------------------------
# Organization — Wikidata (fetch path when QID known)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enrich_org_wikidata_fetch_suggests_website():
    org = Organization.objects.create(name="Test University", wikidata_qid="Q111")
    sugs = enrich_org_from_wikidata(org, fetcher=lambda qid: _WD_ENTITY_RESPONSE)
    assert len(sugs) == 1
    assert sugs[0].field_name == "website"
    assert sugs[0].suggested_value == "https://utest.example"
    assert sugs[0].confidence_score == pytest.approx(0.85)


@pytest.mark.django_db
def test_enrich_org_wikidata_no_duplicate_open_suggestions():
    org = Organization.objects.create(name="Test University")
    enrich_org_from_wikidata(org, fetcher=lambda name: _WD_SEARCH_RESPONSE)
    first_count = MetadataSuggestion.objects.filter(
        organization=org, status=SuggestionStatus.OPEN
    ).count()
    enrich_org_from_wikidata(org, fetcher=lambda name: _WD_SEARCH_RESPONSE)
    second_count = MetadataSuggestion.objects.filter(
        organization=org, status=SuggestionStatus.OPEN
    ).count()
    assert first_count == second_count


@pytest.mark.django_db
def test_enrich_org_wikidata_logs_error():
    org = Organization.objects.create(name="Error Org")

    def boom(name):
        raise OSError("network down")

    sugs = enrich_org_from_wikidata(org, fetcher=boom)
    assert sugs == []
    assert EnrichmentLog.objects.filter(status=EnrichmentStatus.ERROR).exists()
