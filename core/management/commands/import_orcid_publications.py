"""Import ORCID works as Publications for people who have synced ORCID records."""

from django.core.management.base import BaseCommand

from core.models import ORCIDWork, Person
from core.publication_service import import_orcid_works_for_person


class Command(BaseCommand):
    help = "Import ORCID works as Publications. Run after sync_orcid."

    def add_arguments(self, parser):
        parser.add_argument(
            "--person-id",
            type=str,
            default=None,
            help="UUID of a single Person to import for (default: all people with ORCID works).",
        )

    def handle(self, *args, **options):
        person_id = options.get("person_id")
        if person_id:
            try:
                people = [Person.objects.get(pk=person_id)]
            except Person.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Person {person_id} not found."))
                return
        else:
            person_ids = ORCIDWork.objects.values_list("person_id", flat=True).distinct()
            people = list(Person.objects.filter(pk__in=person_ids))

        total_created = total_merged = total_linked = 0
        for person in people:
            counts = import_orcid_works_for_person(person)
            total_created += counts["created"]
            total_merged += counts["merged"]
            total_linked += counts["authors_linked"]
            self.stdout.write(
                f"{person}: {counts['created']} created, "
                f"{counts['merged']} merged, "
                f"{counts['authors_linked']} authors linked"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {len(people)} people — "
                f"{total_created} publications created, "
                f"{total_merged} merged, "
                f"{total_linked} authorships linked."
            )
        )
