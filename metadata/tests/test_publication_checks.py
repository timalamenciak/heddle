import datetime

import pytest
from django.utils import timezone

from core.models import Authorship, Person, Publication
from metadata.checks import (
    check_publication_duplicate_doi,
    check_publication_invalid_doi,
    check_publication_missing_doi,
    check_publication_unlinked_authors,
    check_publication_unreviewed_import,
)
from metadata.models import IssueStatus, MetadataCheck, MetadataFreshnessRule, MetadataIssue


def _get_check(code: str, target: str = "publication", severity: str = "warning") -> MetadataCheck:
    mc, _ = MetadataCheck.objects.get_or_create(
        code=code,
        defaults={"name": code, "severity": severity, "weight": 5.0, "target": target},
    )
    return mc


def _freshness_rule(mc: MetadataCheck, days: int = 365) -> MetadataFreshnessRule:
    rule, _ = MetadataFreshnessRule.objects.get_or_create(
        metadata_check=mc, defaults={"max_age_days": days}
    )
    return rule


def _pub(**kwargs) -> Publication:
    defaults: dict = {"title": "Test Publication", "source": "manual"}
    defaults.update(kwargs)
    return Publication.objects.create(**defaults)


@pytest.mark.django_db
class TestCheckPublicationMissingDoi:
    def test_opens_issue_when_no_doi(self):
        _get_check("pub_missing_doi")
        pub = _pub(title="No DOI")
        check_publication_missing_doi(pub)
        assert MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_missing_doi", status=IssueStatus.OPEN
        ).exists()

    def test_closes_issue_when_doi_present(self):
        _get_check("pub_missing_doi")
        pub = _pub(doi="10.1234/test")
        check_publication_missing_doi(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_missing_doi", status=IssueStatus.OPEN
        ).exists()

    def test_resolves_existing_open_issue_when_doi_added(self):
        _get_check("pub_missing_doi")
        pub = _pub(title="No DOI")
        check_publication_missing_doi(pub)
        assert MetadataIssue.objects.filter(publication=pub, status=IssueStatus.OPEN).exists()
        pub.doi = "10.1234/fixed"
        pub.save()
        check_publication_missing_doi(pub)
        assert not MetadataIssue.objects.filter(publication=pub, status=IssueStatus.OPEN).exists()


@pytest.mark.django_db
class TestCheckPublicationInvalidDoi:
    def test_opens_issue_for_malformed_doi(self):
        _get_check("pub_invalid_doi")
        pub = _pub(doi="not-a-doi")
        check_publication_invalid_doi(pub)
        assert MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_invalid_doi", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_for_valid_doi(self):
        _get_check("pub_invalid_doi")
        pub = _pub(doi="10.1038/nature12345")
        check_publication_invalid_doi(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_invalid_doi", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_when_doi_absent(self):
        _get_check("pub_invalid_doi")
        pub = _pub()
        check_publication_invalid_doi(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_invalid_doi"
        ).exists()


@pytest.mark.django_db
class TestCheckPublicationDuplicateDoi:
    def test_opens_issue_when_duplicate_exists(self):
        _get_check("pub_duplicate_doi", severity="critical")
        _pub(title="Original", doi="10.1234/dup")
        pub2 = _pub(title="Duplicate", doi="10.1234/dup")
        check_publication_duplicate_doi(pub2)
        assert MetadataIssue.objects.filter(
            publication=pub2, metadata_check__code="pub_duplicate_doi", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_when_doi_unique(self):
        _get_check("pub_duplicate_doi", severity="critical")
        pub = _pub(doi="10.9999/unique")
        check_publication_duplicate_doi(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_duplicate_doi"
        ).exists()

    def test_no_issue_when_doi_absent(self):
        _get_check("pub_duplicate_doi", severity="critical")
        pub = _pub()
        check_publication_duplicate_doi(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_duplicate_doi"
        ).exists()


@pytest.mark.django_db
class TestCheckPublicationUnlinkedAuthors:
    def test_opens_issue_when_unlinked_authorship_exists(self):
        _get_check("pub_unlinked_authors", severity="info")
        pub = _pub()
        Authorship.objects.create(publication=pub, person=None, author_name="Unknown Author")
        check_publication_unlinked_authors(pub)
        assert MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unlinked_authors",
            status=IssueStatus.OPEN,
        ).exists()

    def test_no_issue_when_all_authors_linked(self):
        _get_check("pub_unlinked_authors", severity="info")
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        pub = _pub()
        Authorship.objects.create(publication=pub, person=person)
        check_publication_unlinked_authors(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unlinked_authors",
            status=IssueStatus.OPEN,
        ).exists()

    def test_no_issue_when_no_authorships(self):
        _get_check("pub_unlinked_authors", severity="info")
        pub = _pub()
        check_publication_unlinked_authors(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub, metadata_check__code="pub_unlinked_authors"
        ).exists()


@pytest.mark.django_db
class TestCheckPublicationUnreviewedImport:
    def _setup(self):
        mc = _get_check("pub_unreviewed_import", severity="info")
        _freshness_rule(mc, days=365)
        return mc

    def test_opens_issue_for_old_unreviewed_orcid_import(self):
        self._setup()
        pub = Publication.objects.create(title="Old Import", source="orcid_sync", is_reviewed=False)
        Publication.objects.filter(pk=pub.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=400)
        )
        pub.refresh_from_db()
        check_publication_unreviewed_import(pub)
        assert MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unreviewed_import",
            status=IssueStatus.OPEN,
        ).exists()

    def test_no_issue_for_recent_unreviewed_import(self):
        self._setup()
        pub = _pub(source="orcid_sync", is_reviewed=False)
        check_publication_unreviewed_import(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unreviewed_import",
            status=IssueStatus.OPEN,
        ).exists()

    def test_no_issue_when_reviewed(self):
        self._setup()
        pub = Publication.objects.create(title="Reviewed", source="orcid_sync", is_reviewed=True)
        Publication.objects.filter(pk=pub.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=400)
        )
        pub.refresh_from_db()
        check_publication_unreviewed_import(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unreviewed_import",
            status=IssueStatus.OPEN,
        ).exists()

    def test_no_issue_for_manual_source(self):
        self._setup()
        pub = Publication.objects.create(title="Manual", source="manual", is_reviewed=False)
        Publication.objects.filter(pk=pub.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=400)
        )
        pub.refresh_from_db()
        check_publication_unreviewed_import(pub)
        assert not MetadataIssue.objects.filter(
            publication=pub,
            metadata_check__code="pub_unreviewed_import",
            status=IssueStatus.OPEN,
        ).exists()
