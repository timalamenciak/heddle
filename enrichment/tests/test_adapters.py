"""Unit tests for enrichment adapters — no HTTP, all fetchers injected."""

from __future__ import annotations

from enrichment.adapters.crossref import fetch_crossref_work, parse_crossref_work
from enrichment.adapters.openalex import (
    fetch_openalex_author,
    fetch_openalex_institution,
    fetch_openalex_work,
    parse_openalex_author,
    parse_openalex_institution,
    parse_openalex_work,
)
from enrichment.adapters.wikidata import (
    fetch_wikidata_entity,
    parse_wikidata_org,
    search_wikidata_entity,
)

# ---------------------------------------------------------------------------
# Crossref
# ---------------------------------------------------------------------------

_CROSSREF_FULL = {
    "message": {
        "title": ["The Effect of Soil Moisture on Restoration"],
        "published-print": {"date-parts": [[2023, 6, 1]]},
        "type": "journal-article",
        "container-title": ["Restoration Ecology"],
        "abstract": "Abstract text here.",
    }
}

_CROSSREF_ONLINE_DATE = {
    "message": {
        "title": ["Online-first Paper"],
        "published-online": {"date-parts": [[2022]]},
        "type": "proceedings-article",
        "container-title": [],
    }
}

_CROSSREF_NO_DATE = {
    "message": {
        "title": ["Dateless Work"],
        "type": "dataset",
        "container-title": [],
    }
}


def test_parse_crossref_full():
    result = parse_crossref_work(_CROSSREF_FULL)
    assert result["title"] == "The Effect of Soil Moisture on Restoration"
    assert result["year"] == 2023
    assert result["publication_type"] == "journal_article"
    assert result["venue"] == "Restoration Ecology"


def test_parse_crossref_fallback_to_online_date():
    result = parse_crossref_work(_CROSSREF_ONLINE_DATE)
    assert result["year"] == 2022
    assert result["publication_type"] == "conference_paper"
    assert result["venue"] == ""


def test_parse_crossref_no_date():
    result = parse_crossref_work(_CROSSREF_NO_DATE)
    assert result["year"] is None
    assert result["publication_type"] == "dataset"


def test_parse_crossref_empty_message():
    result = parse_crossref_work({})
    assert result["title"] == ""
    assert result["year"] is None
    assert result["venue"] == ""


def test_fetch_crossref_work_uses_injected_fetcher():
    captured: list[str] = []

    def fake_fetcher(doi: str) -> dict:
        captured.append(doi)
        return _CROSSREF_FULL

    result = fetch_crossref_work("10.1234/test", fetcher=fake_fetcher)
    assert captured == ["10.1234/test"]
    assert result == _CROSSREF_FULL


# ---------------------------------------------------------------------------
# OpenAlex — works
# ---------------------------------------------------------------------------

_OA_WORK = {
    "id": "https://openalex.org/W123",
    "title": "Causal Mosaic Ontology Paper",
    "publication_year": 2021,
    "type": "article",
    "primary_location": {"source": {"display_name": "PLOS ONE"}},
}

_OA_WORK_RESPONSE = {"results": [_OA_WORK], "meta": {"count": 1}}
_OA_EMPTY = {"results": [], "meta": {"count": 0}}


def test_parse_openalex_work_full():
    result = parse_openalex_work(_OA_WORK)
    assert result["title"] == "Causal Mosaic Ontology Paper"
    assert result["year"] == 2021
    assert result["publication_type"] == "article"
    assert result["venue"] == "PLOS ONE"


def test_parse_openalex_work_missing_location():
    item = {**_OA_WORK, "primary_location": None}
    result = parse_openalex_work(item)
    assert result["venue"] == ""


def test_fetch_openalex_work_returns_first_result():
    fetcher = lambda doi: _OA_WORK_RESPONSE  # noqa: E731
    result = fetch_openalex_work("10.1234/x", fetcher=fetcher)
    assert result == _OA_WORK


def test_fetch_openalex_work_returns_none_when_empty():
    fetcher = lambda doi: _OA_EMPTY  # noqa: E731
    result = fetch_openalex_work("10.999/none", fetcher=fetcher)
    assert result is None


# ---------------------------------------------------------------------------
# OpenAlex — authors
# ---------------------------------------------------------------------------

_OA_AUTHOR = {
    "id": "https://openalex.org/A123",
    "display_name": "Jane Marie Smith",
    "last_known_institutions": [{"display_name": "MIT"}],
}

_OA_AUTHOR_RESPONSE = {"results": [_OA_AUTHOR]}


def test_parse_openalex_author_splits_name():
    result = parse_openalex_author(_OA_AUTHOR)
    assert result["given_name"] == "Jane Marie"
    assert result["family_name"] == "Smith"


def test_parse_openalex_author_single_name():
    result = parse_openalex_author({"display_name": "Plato"})
    assert result["given_name"] == ""
    assert result["family_name"] == "Plato"


def test_parse_openalex_author_empty():
    result = parse_openalex_author({})
    assert result["given_name"] == ""
    assert result["family_name"] == ""


def test_fetch_openalex_author_returns_first():
    fetcher = lambda orcid: _OA_AUTHOR_RESPONSE  # noqa: E731
    result = fetch_openalex_author("0000-0001-2345-6789", fetcher=fetcher)
    assert result == _OA_AUTHOR


# ---------------------------------------------------------------------------
# OpenAlex — institutions
# ---------------------------------------------------------------------------

_OA_INST = {
    "id": "https://openalex.org/I123",
    "display_name": "University of Toronto",
    "country_code": "CA",
    "type": "education",
    "homepage_url": "https://www.utoronto.ca",
}

_OA_INST_RESPONSE = {"results": [_OA_INST]}


def test_parse_openalex_institution_full():
    result = parse_openalex_institution(_OA_INST)
    assert result["country"] == "CA"
    assert result["org_type"] == "university"
    assert result["website"] == "https://www.utoronto.ca"


def test_parse_openalex_institution_maps_types():
    for oa_type, expected in [
        ("company", "industry"),
        ("government", "government"),
        ("nonprofit", "ngo"),
        ("funder", "ngo"),
        ("healthcare", "research_institute"),
        ("archive", "other"),
    ]:
        result = parse_openalex_institution(
            {"type": oa_type, "country_code": "", "homepage_url": ""}
        )
        assert result["org_type"] == expected, f"{oa_type} should map to {expected}"


def test_fetch_openalex_institution_returns_none_when_empty():
    fetcher = lambda ror: _OA_EMPTY  # noqa: E731
    result = fetch_openalex_institution("https://ror.org/xyz", fetcher=fetcher)
    assert result is None


# ---------------------------------------------------------------------------
# Wikidata
# ---------------------------------------------------------------------------

_WD_SEARCH = {
    "search": [
        {"id": "Q123456", "label": "Ducks Unlimited Canada", "description": "NGO"},
        {"id": "Q999", "label": "Duck Duck Go", "description": "search engine"},
    ]
}

_WD_ENTITY = {
    "entities": {
        "Q123456": {
            "id": "Q123456",
            "claims": {"P856": [{"mainsnak": {"datavalue": {"value": "https://www.ducks.ca"}}}]},
        }
    }
}


def test_search_wikidata_returns_top_qid():
    fetcher = lambda name: _WD_SEARCH  # noqa: E731
    qid = search_wikidata_entity("Ducks Unlimited Canada", fetcher=fetcher)
    assert qid == "Q123456"


def test_search_wikidata_returns_none_on_empty():
    fetcher = lambda name: {"search": []}  # noqa: E731
    qid = search_wikidata_entity("Unknown Corp XYZ", fetcher=fetcher)
    assert qid is None


def test_fetch_wikidata_entity_returns_entity_dict():
    fetcher = lambda qid: _WD_ENTITY  # noqa: E731
    entity = fetch_wikidata_entity("Q123456", fetcher=fetcher)
    assert entity["id"] == "Q123456"


def test_fetch_wikidata_entity_missing_qid():
    fetcher = lambda qid: {"entities": {}}  # noqa: E731
    entity = fetch_wikidata_entity("Q999", fetcher=fetcher)
    assert entity == {}


def test_parse_wikidata_org_extracts_website():
    entity = _WD_ENTITY["entities"]["Q123456"]
    result = parse_wikidata_org(entity)
    assert result["website"] == "https://www.ducks.ca"


def test_parse_wikidata_org_no_p856():
    result = parse_wikidata_org({"claims": {}})
    assert result["website"] == ""


def test_parse_wikidata_org_malformed_claims():
    result = parse_wikidata_org({"claims": {"P856": [{"mainsnak": {}}]}})
    assert result["website"] == ""
