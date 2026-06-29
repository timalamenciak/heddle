"""Tests for quality score computation."""

import pytest

from core.models import Person
from metadata.checks import check_person_missing_orcid, check_person_no_consent
from metadata.models import IssueStatus, MetadataIssue
from metadata.services import compute_person_quality


@pytest.mark.django_db
class TestComputePersonQuality:
    def test_perfect_score_with_no_issues(self):
        person = Person.objects.create(given_name="A", family_name="B")
        score, breakdown = compute_person_quality(person)
        assert score == 100
        assert breakdown == []

    def test_score_decreases_per_open_issue(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)  # −15
        score, breakdown = compute_person_quality(person)
        assert score == 85
        assert len(breakdown) == 1
        assert breakdown[0]["check_code"] == "person_missing_orcid"
        assert breakdown[0]["weight"] == 15.0

    def test_score_with_multiple_issues(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)  # −15
        check_person_no_consent(person)  # −5
        score, breakdown = compute_person_quality(person)
        assert score == 80
        assert len(breakdown) == 2

    def test_score_updates_after_resolve(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        score_before, _ = compute_person_quality(person)
        assert score_before == 85

        # Resolve the issue (simulate adding ORCID and re-running)
        person.orcid = "0000-0001-2345-6789"
        person.save()
        check_person_missing_orcid(person)  # now closes the issue

        score_after, _ = compute_person_quality(person)
        assert score_after == 100

    def test_ignored_issues_not_counted_in_score(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        issue = MetadataIssue.objects.get(
            person=person, metadata_check__code="person_missing_orcid"
        )
        issue.status = IssueStatus.IGNORED
        issue.save()

        score, breakdown = compute_person_quality(person)
        assert score == 100
        assert breakdown == []

    def test_score_floored_at_zero(self):
        """A record with many heavy issues should not go below 0."""
        person = Person.objects.create(given_name="A", family_name="B")
        # Manually create many issues with large weights
        from metadata.models import MetadataCheck, MetadataIssue

        mc = MetadataCheck.objects.first()
        for _ in range(20):
            MetadataIssue.objects.create(
                metadata_check=mc,
                person=person,
                detail="test",
            )
        score, _ = compute_person_quality(person)
        assert score >= 0

    def test_breakdown_includes_detail_and_issue_pk(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        _, breakdown = compute_person_quality(person)
        assert len(breakdown) == 1
        item = breakdown[0]
        assert "detail" in item
        assert "issue_pk" in item
        assert "severity" in item
        assert "check_name" in item
