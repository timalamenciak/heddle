"""Import ORCID works as Publications and rebuild coauthor Collaboration edges."""

import re

from django.db.models import Count, Max, Min

from .models import Authorship, Collaboration, ORCIDWork, Person, Publication

_DOI_RE = re.compile(r"^10\.\d{4,}/\S+$")


def normalize_doi(raw: str) -> str:
    """Strip URL/doi: prefix and lowercase. Returns '' for blank input."""
    doi = raw.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def is_valid_doi(raw: str) -> bool:
    """Return True if raw looks like a valid DOI (10.XXXX/...)."""
    return bool(_DOI_RE.match(normalize_doi(raw))) if raw else False


def find_or_create_publication(
    *,
    title: str,
    doi: str = "",
    year: int | None = None,
    publication_type: str = "",
    source: str = "",
    raw_data: dict | None = None,
) -> tuple[Publication, bool]:
    """Return (pub, created). Dedup: DOI first, then title_normalized + year."""
    if raw_data is None:
        raw_data = {}

    doi_norm = normalize_doi(doi) if doi else ""
    title_norm = " ".join(title.lower().split())

    if doi_norm:
        pub = Publication.objects.filter(doi_normalized=doi_norm).first()
        if pub:
            return pub, False

    if title_norm and year:
        pub = Publication.objects.filter(title_normalized=title_norm, year=year).first()
        if pub:
            if doi_norm and not pub.doi_normalized:
                pub.doi = doi
                pub.save(update_fields=["doi", "doi_normalized"])
            return pub, False

    pub = Publication.objects.create(
        title=title,
        doi=doi,
        year=year,
        publication_type=publication_type,
        source=source,
        raw_data=raw_data,
    )
    return pub, True


def import_orcid_works_for_person(person: Person) -> dict[str, int]:
    """Convert ORCIDWork records for a person into Publications and Authorships.

    Returns counts: {created, merged, authors_linked}.
    """
    counts: dict[str, int] = {"created": 0, "merged": 0, "authors_linked": 0}

    for work in ORCIDWork.objects.filter(person=person):
        pub, created = find_or_create_publication(
            title=work.title or "(untitled)",
            doi=work.doi,
            year=work.publication_year,
            publication_type=work.work_type,
            source="orcid_sync",
            raw_data=work.raw_work,
        )
        if created:
            counts["created"] += 1
        else:
            counts["merged"] += 1

        _, auth_created = Authorship.objects.get_or_create(
            publication=pub,
            person=person,
            defaults={"author_name": person.full_name, "source": "orcid_sync"},
        )
        if auth_created:
            counts["authors_linked"] += 1

    rebuild_collaborations_for_person(person)
    return counts


def rebuild_collaborations_for_person(person: Person) -> int:
    """Upsert Collaboration edges between person and every coauthor.

    Canonical ordering: smaller UUID string → person_a. Returns edge count.
    """
    pub_ids = list(
        Authorship.objects.filter(person=person).values_list("publication_id", flat=True)
    )
    if not pub_ids:
        return 0

    coauthor_rows = list(
        Authorship.objects.filter(publication_id__in=pub_ids, person__isnull=False)
        .exclude(person=person)
        .values("person_id")
        .annotate(
            count=Count("publication_id", distinct=True),
            first_year=Min("publication__year"),
            last_year=Max("publication__year"),
        )
    )

    for row in coauthor_rows:
        a_id, b_id = sorted([person.pk, row["person_id"]], key=str)
        Collaboration.objects.update_or_create(
            person_a_id=a_id,
            person_b_id=b_id,
            defaults={
                "publication_count": row["count"],
                "first_year": row["first_year"],
                "last_year": row["last_year"],
            },
        )

    return len(coauthor_rows)
