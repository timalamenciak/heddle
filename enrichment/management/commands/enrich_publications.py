"""Enrich publications with metadata from Crossref and/or OpenAlex."""

from django.core.management.base import BaseCommand

from core.models import Publication
from enrichment.services import enrich_publication_from_crossref, enrich_publication_from_openalex


class Command(BaseCommand):
    help = "Enrich publications from Crossref and/or OpenAlex (by DOI)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["crossref", "openalex", "both"],
            default="both",
            help="Which source to query (default: both).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of publications to process (0 = all).",
        )

    def handle(self, *args, **options):
        qs = Publication.objects.exclude(doi="").exclude(doi__isnull=True)
        if options["limit"]:
            qs = qs[: options["limit"]]
        total = qs.count()
        self.stdout.write(f"Enriching {total} publication(s)…")
        crossref_total = openalex_total = errors = 0
        source = options["source"]

        for pub in qs:
            if source in ("crossref", "both"):
                try:
                    sugs = enrich_publication_from_crossref(pub)
                    crossref_total += len(sugs)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"Crossref error ({pub.doi}): {exc}")
                    errors += 1
            if source in ("openalex", "both"):
                try:
                    sugs = enrich_publication_from_openalex(pub)
                    openalex_total += len(sugs)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"OpenAlex error ({pub.doi}): {exc}")
                    errors += 1

        self.stdout.write(
            f"Done. Crossref suggestions: {crossref_total}, "
            f"OpenAlex suggestions: {openalex_total}, errors: {errors}."
        )
