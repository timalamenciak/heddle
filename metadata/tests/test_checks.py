"""Tests that each check creates/closes issues correctly."""

import datetime

import pytest
from django.utils import timezone

from core.models import Affiliation, Organization, Person
from metadata.checks import (
    check_org_dup_name,
    check_org_missing_country,
    check_org_no_people,
    check_org_stale,
    check_person_dup_email,
    check_person_dup_name,
    check_person_invalid_orcid,
    check_person_missing_orcid,
    check_person_missing_org,
    check_person_no_consent,
    check_person_stale_profile,
)
from metadata.models import IssueStatus, MetadataIssue


def _stale_person():
    """Create a person whose updated_at is >400 days ago."""
    p = Person.objects.create(given_name="Old", family_name="Record")
    Person.objects.filter(pk=p.pk).update(updated_at=timezone.now() - datetime.timedelta(days=400))
    p.refresh_from_db()
    return p


def _stale_org():
    """Create an org whose updated_at is >400 days ago."""
    o = Organization.objects.create(name="Stale Corp")
    Organization.objects.filter(pk=o.pk).update(
        updated_at=timezone.now() - datetime.timedelta(days=400)
    )
    o.refresh_from_db()
    return o


@pytest.mark.django_db
class TestPersonMissingOrcid:
    def test_creates_issue_when_no_orcid(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_orcid", status=IssueStatus.OPEN
        ).exists()

    def test_closes_issue_when_orcid_added(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        person.orcid = "0000-0001-2345-6789"
        person.save()
        check_person_missing_orcid(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_orcid", status=IssueStatus.OPEN
        ).exists()
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_orcid", status=IssueStatus.RESOLVED
        ).exists()

    def test_no_duplicate_open_issue_on_rerun(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        check_person_missing_orcid(person)
        assert (
            MetadataIssue.objects.filter(
                person=person, metadata_check__code="person_missing_orcid"
            ).count()
            == 1
        )

    def test_ignored_issue_stays_ignored_on_rerun(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        issue = MetadataIssue.objects.get(
            person=person, metadata_check__code="person_missing_orcid"
        )
        issue.status = IssueStatus.IGNORED
        issue.save()
        check_person_missing_orcid(person)
        # Should still be just one issue, still ignored
        issues = MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_orcid"
        )
        assert issues.count() == 1
        assert issues.first().status == IssueStatus.IGNORED

    def test_resolved_issue_reopens_if_condition_still_holds(self):
        """Manually resolving without fixing the data → re-run creates new open issue."""
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_orcid(person)
        issue = MetadataIssue.objects.get(
            person=person, metadata_check__code="person_missing_orcid"
        )
        issue.status = IssueStatus.RESOLVED
        issue.save()
        check_person_missing_orcid(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_orcid", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonInvalidOrcid:
    def test_creates_issue_for_malformed_orcid(self):
        person = Person.objects.create(given_name="A", family_name="B", orcid="not-valid")
        check_person_invalid_orcid(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_invalid_orcid", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_for_valid_orcid(self):
        person = Person.objects.create(given_name="A", family_name="B", orcid="0000-0001-2345-6789")
        check_person_invalid_orcid(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_invalid_orcid", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_when_orcid_absent(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_invalid_orcid(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_invalid_orcid", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonMissingOrg:
    def test_creates_issue_when_no_affiliation(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_missing_org(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_org", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_when_affiliated(self):
        person = Person.objects.create(given_name="A", family_name="B")
        org = Organization.objects.create(name="Test Uni")
        Affiliation.objects.create(person=person, organization=org)
        check_person_missing_org(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_missing_org", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonNoConsent:
    def test_creates_issue_when_no_consent(self):
        person = Person.objects.create(given_name="A", family_name="B", consent_contact=False)
        check_person_no_consent(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_no_consent", status=IssueStatus.OPEN
        ).exists()

    def test_closes_issue_when_consent_given(self):
        person = Person.objects.create(given_name="A", family_name="B", consent_contact=False)
        check_person_no_consent(person)
        person.consent_contact = True
        person.save()
        check_person_no_consent(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_no_consent", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonStaleProfile:
    def test_creates_issue_for_old_record(self):
        person = _stale_person()
        check_person_stale_profile(person)
        assert MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_stale_profile", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_for_recent_record(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_stale_profile(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_stale_profile", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonDuplicateEmail:
    def test_creates_issue_on_both_records(self):
        p1 = Person.objects.create(given_name="A", family_name="B", email="dup@example.com")
        p2 = Person.objects.create(given_name="C", family_name="D", email="dup@example.com")
        check_person_dup_email(p1)
        check_person_dup_email(p2)
        assert (
            MetadataIssue.objects.filter(
                metadata_check__code="person_dup_email", status=IssueStatus.OPEN
            ).count()
            == 2
        )

    def test_no_issue_for_unique_email(self):
        person = Person.objects.create(given_name="A", family_name="B", email="unique@example.com")
        check_person_dup_email(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_dup_email", status=IssueStatus.OPEN
        ).exists()

    def test_no_issue_when_no_email(self):
        person = Person.objects.create(given_name="A", family_name="B")
        check_person_dup_email(person)
        assert not MetadataIssue.objects.filter(
            person=person, metadata_check__code="person_dup_email", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestPersonDuplicateName:
    def test_creates_issue_when_same_name_no_orcid(self):
        p1 = Person.objects.create(given_name="Ada", family_name="Lovelace")
        p2 = Person.objects.create(given_name="Ada", family_name="Lovelace")
        check_person_dup_name(p1)
        check_person_dup_name(p2)
        assert (
            MetadataIssue.objects.filter(
                metadata_check__code="person_dup_name", status=IssueStatus.OPEN
            ).count()
            == 2
        )

    def test_no_issue_when_orcid_distinguishes(self):
        p1 = Person.objects.create(
            given_name="Ada", family_name="Lovelace", orcid="0000-0001-2345-6789"
        )
        p2 = Person.objects.create(
            given_name="Ada", family_name="Lovelace", orcid="0000-0002-3456-7890"
        )
        check_person_dup_name(p1)
        check_person_dup_name(p2)
        assert not MetadataIssue.objects.filter(
            metadata_check__code="person_dup_name", status=IssueStatus.OPEN
        ).exists()


@pytest.mark.django_db
class TestOrgChecks:
    def test_missing_country_creates_issue(self):
        org = Organization.objects.create(name="No Country Org")
        check_org_missing_country(org)
        assert MetadataIssue.objects.filter(
            organization=org, metadata_check__code="org_missing_country", status=IssueStatus.OPEN
        ).exists()

    def test_missing_country_closed_when_set(self):
        org = Organization.objects.create(name="Gets Country")
        check_org_missing_country(org)
        org.country = "CA"
        org.save()
        check_org_missing_country(org)
        assert not MetadataIssue.objects.filter(
            organization=org, metadata_check__code="org_missing_country", status=IssueStatus.OPEN
        ).exists()

    def test_no_people_creates_issue(self):
        org = Organization.objects.create(name="Empty Org")
        check_org_no_people(org)
        assert MetadataIssue.objects.filter(
            organization=org, metadata_check__code="org_no_people", status=IssueStatus.OPEN
        ).exists()

    def test_no_people_closed_when_affiliated(self):
        org = Organization.objects.create(name="Gets People")
        check_org_no_people(org)
        person = Person.objects.create(given_name="X", family_name="Y")
        Affiliation.objects.create(person=person, organization=org)
        check_org_no_people(org)
        assert not MetadataIssue.objects.filter(
            organization=org, metadata_check__code="org_no_people", status=IssueStatus.OPEN
        ).exists()

    def test_dup_name_creates_issue_on_both(self):
        o1 = Organization.objects.create(name="Duplicate University")
        o2 = Organization.objects.create(name="Duplicate University")
        check_org_dup_name(o1)
        check_org_dup_name(o2)
        assert (
            MetadataIssue.objects.filter(
                metadata_check__code="org_dup_name", status=IssueStatus.OPEN
            ).count()
            == 2
        )

    def test_stale_org_creates_issue(self):
        org = _stale_org()
        check_org_stale(org)
        assert MetadataIssue.objects.filter(
            organization=org, metadata_check__code="org_stale", status=IssueStatus.OPEN
        ).exists()
