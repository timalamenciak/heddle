"""Tests for ORCID-related metadata checks."""

import datetime

import pytest
from django.utils import timezone

from core.models import ORCIDProfile, Person
from metadata.checks import check_person_orcid_name_divergence, check_person_orcid_sync_stale
from metadata.models import IssueStatus, MetadataCheck, MetadataIssue


def _make_check(code: str, severity: str = "warning") -> MetadataCheck:
    mc, _ = MetadataCheck.objects.get_or_create(
        code=code,
        defaults={
            "name": code,
            "severity": severity,
            "weight": 10.0,
            "target": "person",
        },
    )
    return mc


def _make_person(**kwargs) -> Person:
    kwargs.setdefault("given_name", "Ada")
    kwargs.setdefault("family_name", "Lovelace")
    return Person.objects.create(**kwargs)


def _make_profile(person: Person, *, fetched_days_ago: int = 1, **kwargs) -> ORCIDProfile:
    fetched_at = timezone.now() - datetime.timedelta(days=fetched_days_ago)
    defaults = {
        "fetched_at": fetched_at,
        "given_name_remote": person.given_name,
        "family_name_remote": person.family_name,
        "raw_record": {},
    }
    defaults.update(kwargs)
    profile, _ = ORCIDProfile.objects.update_or_create(person=person, defaults=defaults)
    return profile


@pytest.mark.django_db
class TestCheckPersonOrcidSyncStale:
    def setup_method(self):
        _make_check("person_orcid_sync_stale")

    def test_no_orcid_no_issue(self):
        person = _make_person()
        check_person_orcid_sync_stale(person)
        assert not MetadataIssue.objects.filter(person=person).exists()

    def test_orcid_never_synced_opens_issue(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        check_person_orcid_sync_stale(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_fresh_profile_resolves_issue(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        _make_profile(person, fetched_days_ago=1)
        check_person_orcid_sync_stale(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_stale_profile_opens_issue(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        _make_profile(person, fetched_days_ago=100)
        check_person_orcid_sync_stale(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_stale_issue_resolves_after_sync(self):
        person = _make_person(orcid="0000-0001-2345-6789")
        _make_profile(person, fetched_days_ago=100)
        check_person_orcid_sync_stale(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

        # Simulate re-sync (fresh profile)
        _make_profile(person, fetched_days_ago=0)
        check_person_orcid_sync_stale(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_disabled_check_skipped(self):
        MetadataCheck.objects.filter(code="person_orcid_sync_stale").update(is_enabled=False)
        person = _make_person(orcid="0000-0001-2345-6789")
        check_person_orcid_sync_stale(person)
        assert not MetadataIssue.objects.filter(person=person).exists()


@pytest.mark.django_db
class TestCheckPersonOrcidNameDivergence:
    def setup_method(self):
        _make_check("person_orcid_name_divergence")

    def test_no_profile_no_issue(self):
        person = _make_person()
        check_person_orcid_name_divergence(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_matching_name_no_issue(self):
        person = _make_person(given_name="Ada", family_name="Lovelace")
        _make_profile(person, given_name_remote="Ada", family_name_remote="Lovelace")
        check_person_orcid_name_divergence(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_case_insensitive_match_no_issue(self):
        person = _make_person(given_name="ada", family_name="lovelace")
        _make_profile(person, given_name_remote="Ada", family_name_remote="Lovelace")
        check_person_orcid_name_divergence(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_diverged_given_name_opens_issue(self):
        person = _make_person(given_name="Ada", family_name="Lovelace")
        _make_profile(person, given_name_remote="Adelaide", family_name_remote="Lovelace")
        check_person_orcid_name_divergence(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_diverged_family_name_opens_issue(self):
        person = _make_person(given_name="Ada", family_name="Lovelace")
        _make_profile(person, given_name_remote="Ada", family_name_remote="Byron")
        check_person_orcid_name_divergence(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

    def test_issue_resolves_after_name_fixed(self):
        person = _make_person(given_name="Ada", family_name="Lovelace")
        _make_profile(person, given_name_remote="Adelaide", family_name_remote="Lovelace")
        check_person_orcid_name_divergence(person)
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()

        # Fix the local name to match remote
        person.given_name = "Adelaide"
        person.save()
        check_person_orcid_name_divergence(person)
        assert not MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()
