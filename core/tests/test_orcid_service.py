"""Tests for ORCID service: normalization, validation, sync, suggestion generation."""

import pytest

from core.models import ORCIDProfile, ORCIDWork, Person
from core.orcid_service import (
    normalize_orcid,
    sync_person_orcid,
    validate_orcid,
)
from metadata.models import MetadataSuggestion, SuggestionStatus

# ---------------------------------------------------------------------------
# Minimal mock ORCID record (ORCID 3.0 schema)
# ---------------------------------------------------------------------------

_GIVEN = "Ada"
_FAMILY = "Lovelace"

MOCK_RECORD = {
    "person": {
        "name": {
            "given-names": {"value": _GIVEN},
            "family-name": {"value": _FAMILY},
        }
    },
    "activities-summary": {
        "works": {
            "group": [
                {
                    "work-summary": [
                        {
                            "put-code": 12345,
                            "title": {"title": {"value": "On Analytical Engines"}},
                            "type": "journal-article",
                            "publication-date": {"year": {"value": "1843"}},
                            "external-ids": {
                                "external-id": [
                                    {
                                        "external-id-type": "doi",
                                        "external-id-value": "10.0000/test",
                                    }
                                ]
                            },
                        }
                    ]
                }
            ]
        },
        "employments": {"affiliation-group": []},
    },
}

MOCK_RECORD_DIVERGED = {
    "person": {
        "name": {
            "given-names": {"value": "Adelaide"},
            "family-name": {"value": "Love"},
        }
    },
    "activities-summary": {"works": {"group": []}, "employments": {"affiliation-group": []}},
}


def _fetcher(record: dict):
    return lambda orcid: record


def _make_person(**kwargs) -> Person:
    kwargs.setdefault("given_name", "Ada")
    kwargs.setdefault("family_name", "Lovelace")
    return Person.objects.create(**kwargs)


# ---------------------------------------------------------------------------
# normalize_orcid
# ---------------------------------------------------------------------------


class TestNormalizeOrcid:
    def test_strips_https_prefix(self):
        assert normalize_orcid("https://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"

    def test_strips_http_prefix(self):
        assert normalize_orcid("http://orcid.org/0000-0001-2345-6789") == "0000-0001-2345-6789"

    def test_strips_whitespace(self):
        assert normalize_orcid("  0000-0001-2345-6789  ") == "0000-0001-2345-6789"

    def test_bare_orcid_unchanged(self):
        assert normalize_orcid("0000-0001-2345-6789") == "0000-0001-2345-6789"

    def test_checksum_x_preserved(self):
        assert normalize_orcid("0000-0002-1694-233X") == "0000-0002-1694-233X"


# ---------------------------------------------------------------------------
# validate_orcid
# ---------------------------------------------------------------------------


class TestValidateOrcid:
    def test_valid_orcid(self):
        assert validate_orcid("0000-0001-2345-6789") is True

    def test_valid_checksum_x(self):
        assert validate_orcid("0000-0002-1694-233X") is True

    def test_rejects_bad_check_digit(self):
        assert validate_orcid("0000-0002-1825-009X") is False

    def test_invalid_too_short(self):
        assert validate_orcid("0000-0001-2345-678") is False

    def test_invalid_url_form_rejected(self):
        assert validate_orcid("https://orcid.org/0000-0001-2345-6789") is False

    def test_invalid_letters(self):
        assert validate_orcid("ABCD-0001-2345-6789") is False


# ---------------------------------------------------------------------------
# sync_person_orcid
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncPersonOrcid:
    def test_creates_orcid_profile(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert ORCIDProfile.objects.filter(person=person).exists()

    def test_stores_remote_name_on_profile(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        profile = ORCIDProfile.objects.get(person=person)
        assert profile.given_name_remote == "Ada"
        assert profile.family_name_remote == "Lovelace"

    def test_creates_orcid_works(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert ORCIDWork.objects.filter(person=person, put_code=12345).exists()

    def test_work_fields_populated(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        work = ORCIDWork.objects.get(person=person, put_code=12345)
        assert work.title == "On Analytical Engines"
        assert work.work_type == "journal-article"
        assert work.publication_year == 1843
        assert work.doi == "10.0000/test"

    def test_no_suggestion_when_names_match(self):
        person = _make_person(given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert MetadataSuggestion.objects.filter(person=person).count() == 0

    def test_suggestion_created_when_name_differs(self):
        person = _make_person(given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD_DIVERGED))
        assert (
            MetadataSuggestion.objects.filter(person=person, status=SuggestionStatus.OPEN).count()
            == 2
        )  # given_name and family_name differ

    def test_no_duplicate_suggestions_on_re_sync(self):
        person = _make_person(given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD_DIVERGED))
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD_DIVERGED))
        assert (
            MetadataSuggestion.objects.filter(person=person, status=SuggestionStatus.OPEN).count()
            == 2
        )

    def test_no_sync_without_orcid(self):
        person = _make_person()
        result = sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert result == []
        assert not ORCIDProfile.objects.filter(person=person).exists()

    def test_no_sync_with_invalid_orcid(self):
        person = _make_person(orcid="not-an-orcid")
        result = sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert result == []
        assert not ORCIDProfile.objects.filter(person=person).exists()

    def test_re_sync_updates_profile(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD_DIVERGED))
        profile = ORCIDProfile.objects.get(person=person)
        assert profile.given_name_remote == "Adelaide"

    def test_works_upserted_not_duplicated(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert ORCIDWork.objects.filter(person=person, put_code=12345).count() == 1

    def test_case_insensitive_name_match(self):
        person = _make_person(given_name="ada", family_name="lovelace", orcid="0000-0001-2345-6789")
        sync_person_orcid(person, fetcher=_fetcher(MOCK_RECORD))
        assert MetadataSuggestion.objects.filter(person=person).count() == 0
