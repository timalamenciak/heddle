import pytest
from django.utils import timezone

from core.models import Authorship, Collaboration, ORCIDProfile, ORCIDWork, Person, Publication
from core.publication_service import (
    find_or_create_publication,
    import_orcid_works_for_person,
    is_valid_doi,
    normalize_doi,
    rebuild_collaborations_for_person,
)

# ---------------------------------------------------------------------------
# normalize_doi / is_valid_doi
# ---------------------------------------------------------------------------


class TestNormalizeDoi:
    def test_strips_https_prefix(self):
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"

    def test_strips_http_prefix(self):
        assert normalize_doi("http://doi.org/10.1234/test") == "10.1234/test"

    def test_strips_doi_colon_prefix(self):
        assert normalize_doi("doi:10.1234/test") == "10.1234/test"

    def test_lowercases(self):
        assert normalize_doi("10.1234/TEST") == "10.1234/test"

    def test_bare_doi_unchanged(self):
        assert normalize_doi("10.1234/test.xyz") == "10.1234/test.xyz"

    def test_empty_string(self):
        assert normalize_doi("") == ""

    def test_strips_whitespace(self):
        assert normalize_doi("  10.1234/test  ") == "10.1234/test"


class TestIsValidDoi:
    def test_valid_doi(self):
        assert is_valid_doi("10.1038/nature12345") is True

    def test_valid_with_slash_parts(self):
        assert is_valid_doi("10.1000/xyz123") is True

    def test_url_prefix_valid(self):
        assert is_valid_doi("https://doi.org/10.1038/nature12345") is True

    def test_missing_registrant(self):
        assert is_valid_doi("10./something") is False

    def test_not_starting_with_10(self):
        assert is_valid_doi("20.1234/test") is False

    def test_empty_string(self):
        assert is_valid_doi("") is False

    def test_plain_text(self):
        assert is_valid_doi("not-a-doi") is False


# ---------------------------------------------------------------------------
# find_or_create_publication (dedup logic)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFindOrCreatePublication:
    def test_creates_new_publication(self):
        pub, created = find_or_create_publication(title="Test Paper", doi="10.1234/test")
        assert created is True
        assert pub.title == "Test Paper"
        assert pub.doi_normalized == "10.1234/test"

    def test_dedup_by_doi(self):
        pub1, _ = find_or_create_publication(title="Paper One", doi="10.1234/same")
        pub2, created = find_or_create_publication(title="Paper One Different", doi="10.1234/same")
        assert created is False
        assert pub2.pk == pub1.pk

    def test_dedup_doi_ignores_url_prefix(self):
        pub1, _ = find_or_create_publication(title="Paper", doi="10.1234/abc")
        pub2, created = find_or_create_publication(title="Paper", doi="https://doi.org/10.1234/abc")
        assert created is False
        assert pub2.pk == pub1.pk

    def test_dedup_by_title_and_year(self):
        pub1, _ = find_or_create_publication(title="Unique Title", year=2021)
        pub2, created = find_or_create_publication(title="Unique Title", year=2021)
        assert created is False
        assert pub2.pk == pub1.pk

    def test_same_title_different_year_creates_new(self):
        find_or_create_publication(title="Same Title", year=2020)
        _, created = find_or_create_publication(title="Same Title", year=2021)
        assert created is True

    def test_title_year_dedup_merges_doi(self):
        pub1, _ = find_or_create_publication(title="Paper", year=2022)
        assert pub1.doi_normalized == ""
        pub2, created = find_or_create_publication(title="Paper", year=2022, doi="10.9999/new")
        assert created is False
        pub1.refresh_from_db()
        assert pub1.doi_normalized == "10.9999/new"

    def test_normalized_title_key_used_for_dedup(self):
        pub1, _ = find_or_create_publication(title="  Ecology  Paper  ", year=2023)
        pub2, created = find_or_create_publication(title="Ecology Paper", year=2023)
        assert created is False
        assert pub2.pk == pub1.pk

    def test_save_sets_normalized_fields(self):
        pub, _ = find_or_create_publication(title="Test", doi="https://doi.org/10.1111/XYZ")
        assert pub.doi_normalized == "10.1111/xyz"
        assert pub.title_normalized == "test"


# ---------------------------------------------------------------------------
# import_orcid_works_for_person
# ---------------------------------------------------------------------------


@pytest.fixture
def person(db):
    return Person.objects.create(given_name="Ada", family_name="Lovelace")


@pytest.fixture
def person_b(db):
    return Person.objects.create(given_name="Grace", family_name="Hopper")


def _make_orcid_work(person, title="A Paper", doi="", year=2020, put_code=1):
    profile, _ = ORCIDProfile.objects.get_or_create(
        person=person,
        defaults={"fetched_at": timezone.now(), "raw_record": {}},
    )
    return ORCIDWork.objects.create(
        person=person,
        profile=profile,
        put_code=put_code,
        title=title,
        doi=doi,
        publication_year=year,
        work_type="journal-article",
        raw_work={},
    )


@pytest.mark.django_db
class TestImportOrcidWorksForPerson:
    def test_creates_publication_and_authorship(self, person):
        _make_orcid_work(person, title="My Paper", doi="10.1234/mp", year=2021)
        counts = import_orcid_works_for_person(person)
        assert counts["created"] == 1
        assert counts["authors_linked"] == 1
        assert Publication.objects.filter(title="My Paper").exists()
        assert Authorship.objects.filter(person=person).count() == 1

    def test_merges_duplicate_doi_across_persons(self, person, person_b):
        _make_orcid_work(person, title="Shared", doi="10.5555/shared", year=2020)
        _make_orcid_work(person_b, title="Shared", doi="10.5555/shared", year=2020, put_code=2)
        import_orcid_works_for_person(person)
        counts = import_orcid_works_for_person(person_b)
        assert counts["merged"] == 1
        assert Publication.objects.filter(doi_normalized="10.5555/shared").count() == 1
        assert Authorship.objects.count() == 2

    def test_idempotent_reimport(self, person):
        _make_orcid_work(person, title="Paper", doi="10.1/p", year=2020)
        import_orcid_works_for_person(person)
        counts = import_orcid_works_for_person(person)
        assert counts["created"] == 0
        assert counts["merged"] == 1
        assert counts["authors_linked"] == 0
        assert Publication.objects.count() == 1

    def test_no_works_returns_zeros(self, person):
        counts = import_orcid_works_for_person(person)
        assert counts == {"created": 0, "merged": 0, "authors_linked": 0}

    def test_sets_source_orcid_sync(self, person):
        _make_orcid_work(person, title="T", doi="10.1/t", year=2020)
        import_orcid_works_for_person(person)
        pub = Publication.objects.get()
        assert pub.source == "orcid_sync"


# ---------------------------------------------------------------------------
# rebuild_collaborations_for_person
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRebuildCollaborations:
    def test_creates_collaboration_edge(self, person, person_b):
        _make_orcid_work(person, title="Collab", doi="10.1/c", year=2020)
        _make_orcid_work(person_b, title="Collab", doi="10.1/c", year=2020, put_code=2)
        import_orcid_works_for_person(person)
        import_orcid_works_for_person(person_b)
        assert Collaboration.objects.count() == 1
        collab = Collaboration.objects.get()
        assert collab.publication_count == 1

    def test_canonical_ordering_a_less_than_b(self, person, person_b):
        _make_orcid_work(person, title="P", doi="10.1/p", year=2020)
        _make_orcid_work(person_b, title="P", doi="10.1/p", year=2020, put_code=2)
        import_orcid_works_for_person(person)
        import_orcid_works_for_person(person_b)
        collab = Collaboration.objects.get()
        assert str(collab.person_a_id) < str(collab.person_b_id)

    def test_no_self_collaboration(self, person):
        _make_orcid_work(person, title="Solo", doi="10.1/s", year=2020)
        import_orcid_works_for_person(person)
        assert Collaboration.objects.count() == 0

    def test_publication_count_increases_with_more_shared_works(self, person, person_b):
        _make_orcid_work(person, title="Work1", doi="10.1/w1", year=2019)
        _make_orcid_work(person_b, title="Work1", doi="10.1/w1", year=2019, put_code=2)
        _make_orcid_work(person, title="Work2", doi="10.1/w2", year=2020, put_code=3)
        _make_orcid_work(person_b, title="Work2", doi="10.1/w2", year=2020, put_code=4)
        import_orcid_works_for_person(person)
        import_orcid_works_for_person(person_b)
        collab = Collaboration.objects.get()
        assert collab.publication_count == 2

    def test_no_works_returns_zero(self, person):
        count = rebuild_collaborations_for_person(person)
        assert count == 0
