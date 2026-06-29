"""Enrich organizations from OpenAlex (by ROR) and Wikidata."""

from django.core.management.base import BaseCommand

from core.models import Organization
from enrichment.services import enrich_org_from_openalex, enrich_org_from_wikidata


class Command(BaseCommand):
    help = "Enrich organizations from OpenAlex (by ROR) and/or Wikidata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["openalex", "wikidata", "both"],
            default="both",
            help="Which source to query (default: both).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of organizations to process (0 = all).",
        )

    def handle(self, *args, **options):
        qs = Organization.objects.all()
        if options["limit"]:
            qs = qs[: options["limit"]]
        total = qs.count()
        self.stdout.write(f"Enriching {total} organization(s)…")
        oa_total = wd_total = errors = 0
        source = options["source"]

        for org in qs:
            if source in ("openalex", "both"):
                try:
                    sugs = enrich_org_from_openalex(org)
                    oa_total += len(sugs)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"OpenAlex error ({org}): {exc}")
                    errors += 1
            if source in ("wikidata", "both"):
                try:
                    sugs = enrich_org_from_wikidata(org)
                    wd_total += len(sugs)
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"Wikidata error ({org}): {exc}")
                    errors += 1

        self.stdout.write(
            f"Done. OpenAlex suggestions: {oa_total}, "
            f"Wikidata suggestions: {wd_total}, errors: {errors}."
        )
