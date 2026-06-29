"""Tests for metadata views: dashboard, issue actions, panels."""

import pytest
from django.urls import reverse

from core.models import Person
from metadata.checks import check_person_missing_orcid
from metadata.models import IssueStatus, MetadataIssue


@pytest.fixture
def person_with_issue(db):
    person = Person.objects.create(given_name="Ada", family_name="Lovelace")
    check_person_missing_orcid(person)
    return person


@pytest.fixture
def open_issue(person_with_issue):
    return MetadataIssue.objects.get(
        person=person_with_issue, metadata_check__code="person_missing_orcid"
    )


@pytest.mark.django_db
class TestMetadataDashboard:
    def test_requires_login(self, client):
        response = client.get(reverse("metadata:dashboard"))
        assert response.status_code == 302

    def test_viewer_cannot_access(self, client, viewer):
        client.force_login(viewer)
        response = client.get(reverse("metadata:dashboard"))
        assert response.status_code == 403

    def test_contributor_can_access(self, client, contributor):
        client.force_login(contributor)
        response = client.get(reverse("metadata:dashboard"))
        assert response.status_code == 200

    def test_shows_issue_counts(self, client, contributor, person_with_issue):
        client.force_login(contributor)
        response = client.get(reverse("metadata:dashboard"))
        assert response.status_code == 200
        assert b"1" in response.content  # at least one open issue


@pytest.mark.django_db
class TestRunChecksView:
    def test_requires_contributor(self, client, viewer):
        client.force_login(viewer)
        response = client.post(reverse("metadata:run_checks"))
        assert response.status_code == 403

    def test_creates_issues_for_incomplete_records(self, client, contributor):
        person = Person.objects.create(given_name="No", family_name="Orcid")
        client.force_login(contributor)
        response = client.post(reverse("metadata:run_checks"))
        assert response.status_code == 302
        assert MetadataIssue.objects.filter(person=person, status=IssueStatus.OPEN).exists()


@pytest.mark.django_db
class TestIssueResolveView:
    def test_viewer_cannot_resolve(self, client, viewer, open_issue):
        client.force_login(viewer)
        response = client.post(
            reverse("metadata:issue_resolve", kwargs={"pk": open_issue.pk}),
            {"next": "/"},
        )
        assert response.status_code == 403

    def test_contributor_can_resolve(self, client, contributor, open_issue):
        client.force_login(contributor)
        response = client.post(
            reverse("metadata:issue_resolve", kwargs={"pk": open_issue.pk}),
            {"next": "/"},
        )
        assert response.status_code == 302
        open_issue.refresh_from_db()
        assert open_issue.status == IssueStatus.RESOLVED
        assert open_issue.resolved_by == contributor

    def test_external_next_url_is_rejected(self, client, contributor, open_issue):
        client.force_login(contributor)
        response = client.post(
            reverse("metadata:issue_resolve", kwargs={"pk": open_issue.pk}),
            {"next": "https://attacker.example/phish"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/metadata/"

    def test_resolve_sets_resolved_at(self, client, contributor, open_issue):
        client.force_login(contributor)
        client.post(
            reverse("metadata:issue_resolve", kwargs={"pk": open_issue.pk}),
            {"next": "/"},
        )
        open_issue.refresh_from_db()
        assert open_issue.resolved_at is not None


@pytest.mark.django_db
class TestIssueIgnoreView:
    def test_contributor_can_ignore(self, client, contributor, open_issue):
        client.force_login(contributor)
        response = client.post(
            reverse("metadata:issue_ignore", kwargs={"pk": open_issue.pk}),
            {"next": "/", "reason": "not applicable"},
        )
        assert response.status_code == 302
        open_issue.refresh_from_db()
        assert open_issue.status == IssueStatus.IGNORED
        assert open_issue.ignore_reason == "not applicable"
        assert open_issue.ignored_by == contributor


@pytest.mark.django_db
class TestPersonIssuesPanelView:
    def test_requires_login(self, client, person_with_issue):
        response = client.get(
            reverse("metadata:person_issues", kwargs={"pk": person_with_issue.pk})
        )
        assert response.status_code == 302

    def test_viewer_can_access(self, client, viewer, person_with_issue):
        client.force_login(viewer)
        response = client.get(
            reverse("metadata:person_issues", kwargs={"pk": person_with_issue.pk})
        )
        assert response.status_code == 200

    def test_shows_open_issues(self, client, viewer, person_with_issue):
        client.force_login(viewer)
        response = client.get(
            reverse("metadata:person_issues", kwargs={"pk": person_with_issue.pk})
        )
        assert b"Missing ORCID" in response.content

    def test_shows_quality_score(self, client, viewer, person_with_issue):
        client.force_login(viewer)
        response = client.get(
            reverse("metadata:person_issues", kwargs={"pk": person_with_issue.pk})
        )
        assert b"85" in response.content  # 100 - 15 = 85
