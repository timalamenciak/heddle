"""Slice-building helpers: collect querysets for each export scope, then delegate to
build_kgx_export."""

from __future__ import annotations

from uuid import UUID

from core.models import Affiliation, Authorship, Collaboration, Organization, Person, Publication
from events.models import Event, Participation, SavedSegment

from .exporters.kgx import KGXExport, build_kgx_export


def _gather_for_people(person_pks: set) -> dict:
    """Return the related org/pub/affiliation/authorship/collab data for a set of person PKs."""
    affiliations = list(
        Affiliation.objects.filter(person_id__in=person_pks).select_related(
            "person", "organization"
        )
    )
    org_pks = {a.organization_id for a in affiliations}
    organizations = list(Organization.objects.filter(pk__in=org_pks))

    authorships = list(
        Authorship.objects.filter(person_id__in=person_pks, person__isnull=False).select_related(
            "person", "publication"
        )
    )
    pub_pks = {a.publication_id for a in authorships}
    publications = list(Publication.objects.filter(pk__in=pub_pks))

    # Only include collaboration edges where BOTH ends are in this slice
    collaborations = list(
        Collaboration.objects.filter(
            person_a_id__in=person_pks, person_b_id__in=person_pks
        ).select_related("person_a", "person_b")
    )

    return {
        "organizations": organizations,
        "publications": publications,
        "affiliations": affiliations,
        "authorships": authorships,
        "collaborations": collaborations,
    }


def full_kgx_export(*, generated_by: str = "system") -> KGXExport:
    people = list(Person.objects.all())
    organizations = list(Organization.objects.all())
    publications = list(Publication.objects.all())
    events = list(Event.objects.all())
    affiliations = list(Affiliation.objects.select_related("person", "organization").all())
    authorships = list(
        Authorship.objects.filter(person__isnull=False).select_related("person", "publication")
    )
    collaborations = list(Collaboration.objects.select_related("person_a", "person_b").all())
    participations = list(Participation.objects.select_related("person", "event").all())

    return build_kgx_export(
        people=people,
        organizations=organizations,
        publications=publications,
        events=events,
        affiliations=affiliations,
        authorships=authorships,
        collaborations=collaborations,
        participations=participations,
        slice_name="full",
        generated_by=generated_by,
    )


def event_kgx_export(event_pk: UUID, *, generated_by: str = "system") -> KGXExport:
    event = Event.objects.get(pk=event_pk)
    participations = list(
        Participation.objects.filter(event=event).select_related("person", "event")
    )
    person_pks = {p.person_id for p in participations if p.person_id}
    people = list(Person.objects.filter(pk__in=person_pks))
    related = _gather_for_people(person_pks)

    return build_kgx_export(
        people=people,
        events=[event],
        participations=participations,
        slice_name=f"event:{event_pk}",
        generated_by=generated_by,
        **related,
    )


def segment_kgx_export(segment_pk: UUID, *, generated_by: str = "system") -> KGXExport:
    segment = SavedSegment.objects.get(pk=segment_pk)
    filters = segment.filters or {}
    qs = Person.objects.all()
    for key in ("country", "continent", "metadata_status"):
        if val := filters.get(key):
            qs = qs.filter(**{key: val})
    people = list(qs)
    person_pks = {p.pk for p in people}
    related = _gather_for_people(person_pks)

    return build_kgx_export(
        people=people,
        slice_name=f"segment:{segment_pk}",
        generated_by=generated_by,
        **related,
    )


def person_neighbourhood_kgx_export(
    person_pk: UUID,
    hops: int = 1,
    *,
    generated_by: str = "system",
) -> KGXExport:
    """BFS over Collaboration edges up to `hops` levels from a single person."""
    hops = max(1, min(hops, 3))

    visited: set = {person_pk}
    frontier: set = {person_pk}

    for _ in range(hops):
        next_ids = (
            set(
                Collaboration.objects.filter(person_a_id__in=frontier).values_list(
                    "person_b_id", flat=True
                )
            )
            | set(
                Collaboration.objects.filter(person_b_id__in=frontier).values_list(
                    "person_a_id", flat=True
                )
            )
        ) - visited
        visited |= next_ids
        frontier = next_ids
        if not frontier:
            break

    people = list(Person.objects.filter(pk__in=visited))
    related = _gather_for_people(visited)

    return build_kgx_export(
        people=people,
        slice_name=f"person-neighbourhood:{person_pk}:{hops}",
        generated_by=generated_by,
        **related,
    )
