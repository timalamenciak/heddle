"""Tests for segment filter logic and match-reason generation."""

import datetime

import pytest

from core.models import Affiliation, ExpertiseTerm, Organization, Person, PersonExpertise
from events.models import Event, Participation, ParticipationStatus
from events.services import apply_segment_filters, get_match_reasons
from metadata.models import IssueStatus, MetadataIssue


def _make_person(**kwargs):
    return Person.objects.create(**kwargs)


def _make_event():
    return Event.objects.create(name="E1", start_date=datetime.date(2025, 1, 1))


@pytest.mark.django_db
class TestApplySegmentFilters:
    def test_empty_filters_returns_all(self):
        _make_person(given_name="A", family_name="B")
        _make_person(given_name="C", family_name="D")
        result = apply_segment_filters({})
        assert result.count() == 2

    def test_country_filter(self):
        _make_person(given_name="CA", family_name="One", country="CA")
        _make_person(given_name="DE", family_name="Two", country="DE")
        result = apply_segment_filters({"countries": ["CA"]})
        assert result.count() == 1
        assert result.first().country == "CA"

    def test_country_filter_or_within_list(self):
        _make_person(given_name="A", family_name="X", country="CA")
        _make_person(given_name="B", family_name="Y", country="US")
        _make_person(given_name="C", family_name="Z", country="DE")
        result = apply_segment_filters({"countries": ["CA", "US"]})
        assert result.count() == 2

    def test_continent_filter(self):
        _make_person(given_name="E", family_name="One", continent="Europe")
        _make_person(given_name="A", family_name="Two", continent="Asia")
        result = apply_segment_filters({"continents": ["Europe"]})
        assert result.count() == 1

    def test_org_type_filter(self):
        uni = Organization.objects.create(name="State Uni", org_type="university")
        ngo = Organization.objects.create(name="Green NGO", org_type="ngo")
        p1 = _make_person(given_name="A", family_name="B")
        p2 = _make_person(given_name="C", family_name="D")
        Affiliation.objects.create(person=p1, organization=uni)
        Affiliation.objects.create(person=p2, organization=ngo)
        result = apply_segment_filters({"org_types": ["university"]})
        pks = set(result.values_list("pk", flat=True))
        assert p1.pk in pks
        assert p2.pk not in pks

    def test_expertise_filter_or_within_list(self):
        term1 = ExpertiseTerm.objects.create(term="ecological-restoration")
        term2 = ExpertiseTerm.objects.create(term="knowledge-graph")
        ExpertiseTerm.objects.create(term="unrelated")
        p1 = _make_person(given_name="A", family_name="B")
        p2 = _make_person(given_name="C", family_name="D")
        p3 = _make_person(given_name="E", family_name="F")
        PersonExpertise.objects.create(person=p1, term=term1)
        PersonExpertise.objects.create(person=p2, term=term2)
        result = apply_segment_filters({"expertise_term_ids": [str(term1.id), str(term2.id)]})
        pks = set(result.values_list("pk", flat=True))
        assert p1.pk in pks
        assert p2.pk in pks
        assert p3.pk not in pks

    def test_consent_contact_filter(self):
        _make_person(given_name="A", family_name="B", consent_contact=True)
        _make_person(given_name="C", family_name="D", consent_contact=False)
        result = apply_segment_filters({"consent_contact": True})
        assert result.count() == 1
        assert result.first().consent_contact is True

    def test_has_orcid_filter(self):
        _make_person(given_name="A", family_name="B", orcid="0000-0001-2345-6789")
        _make_person(given_name="C", family_name="D")
        result = apply_segment_filters({"has_orcid": True})
        assert result.count() == 1

    def test_no_critical_issues_filter(self):
        from metadata.models import MetadataCheck

        p_ok = _make_person(given_name="Clean", family_name="Record")
        p_bad = _make_person(given_name="Bad", family_name="Record")
        mc = MetadataCheck.objects.filter(severity="critical").first()
        if mc is None:
            mc = MetadataCheck.objects.create(
                code="test_critical",
                name="Test critical",
                severity="critical",
                weight=50.0,
                target="person",
            )
        MetadataIssue.objects.create(metadata_check=mc, person=p_bad, status=IssueStatus.OPEN)
        result = apply_segment_filters({"no_critical_issues": True})
        pks = set(result.values_list("pk", flat=True))
        assert p_ok.pk in pks
        assert p_bad.pk not in pks

    def test_not_invited_to_event_filter(self):
        event = _make_event()
        p_invited = _make_person(given_name="A", family_name="B")
        p_free = _make_person(given_name="C", family_name="D")
        Participation.objects.create(
            person=p_invited, event=event, status=ParticipationStatus.INVITED
        )
        result = apply_segment_filters({"not_invited_to_event_id": str(event.pk)})
        pks = set(result.values_list("pk", flat=True))
        assert p_free.pk in pks
        assert p_invited.pk not in pks

    def test_not_invited_excludes_confirmed_too(self):
        event = _make_event()
        p = _make_person(given_name="A", family_name="B")
        Participation.objects.create(person=p, event=event, status=ParticipationStatus.CONFIRMED)
        result = apply_segment_filters({"not_invited_to_event_id": str(event.pk)})
        assert p.pk not in set(result.values_list("pk", flat=True))

    def test_prior_participation_filter(self):
        event = _make_event()
        p_attended = _make_person(given_name="A", family_name="B")
        p_declined = _make_person(given_name="C", family_name="D")
        p_none = _make_person(given_name="E", family_name="F")
        Participation.objects.create(
            person=p_attended, event=event, status=ParticipationStatus.ATTENDED
        )
        Participation.objects.create(
            person=p_declined, event=event, status=ParticipationStatus.DECLINED
        )
        result = apply_segment_filters({"prior_participation_event_id": str(event.pk)})
        pks = set(result.values_list("pk", flat=True))
        assert p_attended.pk in pks
        assert p_declined.pk not in pks
        assert p_none.pk not in pks

    def test_free_text_filter(self):
        _make_person(given_name="Restoration", family_name="Expert", notes="works on ecosystems")
        _make_person(given_name="Other", family_name="Person")
        result = apply_segment_filters({"free_text": "ecosystem"})
        assert result.count() == 1

    def test_combined_filters_are_anded(self):
        _make_person(given_name="A", family_name="B", country="CA", consent_contact=True)
        _make_person(given_name="C", family_name="D", country="CA", consent_contact=False)
        _make_person(given_name="E", family_name="F", country="US", consent_contact=True)
        result = apply_segment_filters({"countries": ["CA"], "consent_contact": True})
        assert result.count() == 1
        assert result.first().country == "CA"
        assert result.first().consent_contact is True


@pytest.mark.django_db
class TestGetMatchReasons:
    def test_country_reason(self):
        person = _make_person(given_name="A", family_name="B", country="CA")
        reasons = get_match_reasons(person, {"countries": ["CA"]})
        assert any("CA" in r for r in reasons)

    def test_consent_reason(self):
        person = _make_person(given_name="A", family_name="B", consent_contact=True)
        reasons = get_match_reasons(person, {"consent_contact": True})
        assert any("consent" in r.lower() for r in reasons)

    def test_orcid_reason(self):
        person = _make_person(given_name="A", family_name="B", orcid="0000-0001-2345-6789")
        reasons = get_match_reasons(person, {"has_orcid": True})
        assert any("ORCID" in r for r in reasons)

    def test_no_critical_issues_reason(self):
        person = _make_person(given_name="A", family_name="B")
        reasons = get_match_reasons(person, {"no_critical_issues": True})
        assert any("critical" in r.lower() for r in reasons)

    def test_expertise_reason(self):
        term = ExpertiseTerm.objects.create(term="ecological-restoration")
        person = _make_person(given_name="A", family_name="B")
        PersonExpertise.objects.create(person=person, term=term)
        reasons = get_match_reasons(person, {"expertise_term_ids": [str(term.id)]})
        assert any("ecological-restoration" in r for r in reasons)

    def test_fallback_reason_when_no_filter_produces_reasons(self):
        person = _make_person(given_name="A", family_name="B")
        reasons = get_match_reasons(person, {})
        assert reasons == ["Matched all criteria"]
