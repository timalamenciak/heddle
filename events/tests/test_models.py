"""Basic model-creation tests for the events app."""

import datetime

import pytest

from core.models import Person
from events.models import (
    Event,
    Participation,
    ParticipationRole,
    ParticipationStatus,
    SavedSegment,
    Session,
)


@pytest.mark.django_db
class TestEvent:
    def test_create_minimal(self):
        event = Event.objects.create(name="EcoTransform 2025", start_date=datetime.date(2025, 9, 1))
        assert str(event) == "EcoTransform 2025"
        assert event.pk is not None

    def test_ordering_newest_first(self):
        Event.objects.create(name="Old", start_date=datetime.date(2020, 1, 1))
        Event.objects.create(name="New", start_date=datetime.date(2024, 1, 1))
        names = list(Event.objects.values_list("name", flat=True))
        assert names[0] == "New"

    def test_fields(self):
        event = Event.objects.create(
            name="OERC 2025",
            start_date=datetime.date(2025, 6, 1),
            end_date=datetime.date(2025, 6, 3),
            location="Ottawa",
            country="CA",
            event_type="conference",
        )
        assert event.location == "Ottawa"
        assert event.country == "CA"


@pytest.mark.django_db
class TestSession:
    def test_create(self):
        event = Event.objects.create(name="E1", start_date=datetime.date(2025, 1, 1))
        session = Session.objects.create(event=event, name="Opening plenary")
        assert str(session) == "E1 — Opening plenary"


@pytest.mark.django_db
class TestParticipation:
    def test_create(self):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        event = Event.objects.create(name="E1", start_date=datetime.date(2025, 1, 1))
        p = Participation.objects.create(person=person, event=event)
        assert p.status == ParticipationStatus.INVITED
        assert p.role == ParticipationRole.ATTENDEE

    def test_unique_person_event_constraint(self):
        from django.db import IntegrityError

        person = Person.objects.create(given_name="A", family_name="B")
        event = Event.objects.create(name="E1", start_date=datetime.date(2025, 1, 1))
        Participation.objects.create(person=person, event=event)
        with pytest.raises(IntegrityError):
            Participation.objects.create(person=person, event=event)

    def test_str(self):
        person = Person.objects.create(given_name="Ada", family_name="Lovelace")
        event = Event.objects.create(name="EcoHack", start_date=datetime.date(2025, 1, 1))
        p = Participation.objects.create(person=person, event=event, status="confirmed")
        assert "Ada Lovelace" in str(p)
        assert "confirmed" in str(p)


@pytest.mark.django_db
class TestSavedSegment:
    def test_create_with_filters(self):
        filters = {"continents": ["Europe"], "consent_contact": True, "no_critical_issues": True}
        seg = SavedSegment.objects.create(name="Europe researchers", filters=filters)
        assert seg.filters["continents"] == ["Europe"]
        assert seg.pk is not None

    def test_default_filters_is_empty_dict(self):
        seg = SavedSegment.objects.create(name="Empty")
        assert seg.filters == {}
