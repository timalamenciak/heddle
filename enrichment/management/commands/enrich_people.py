"""Enrich people with metadata from OpenAlex (by ORCID)."""

from django.core.management.base import BaseCommand

from core.models import Person
from enrichment.services import enrich_person_from_openalex


class Command(BaseCommand):
    help = "Enrich people from OpenAlex (by ORCID iD)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of people to process (0 = all).",
        )

    def handle(self, *args, **options):
        qs = Person.objects.exclude(orcid__isnull=True).exclude(orcid="")
        if options["limit"]:
            qs = qs[: options["limit"]]
        total = qs.count()
        self.stdout.write(f"Enriching {total} person(s) from OpenAlex…")
        suggestions_total = errors = 0

        for person in qs:
            try:
                sugs = enrich_person_from_openalex(person)
                suggestions_total += len(sugs)
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(f"Error ({person}): {exc}")
                errors += 1

        self.stdout.write(f"Done. Suggestions: {suggestions_total}, errors: {errors}.")
