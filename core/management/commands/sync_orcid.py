from django.core.management.base import BaseCommand

from core.models import Person
from core.orcid_service import sync_person_orcid


class Command(BaseCommand):
    help = "Sync ORCID public records for people with an ORCID iD. No tokens used or stored."

    def add_arguments(self, parser):
        parser.add_argument(
            "--person-id",
            type=str,
            default=None,
            metavar="UUID",
            help="Sync a single person by UUID instead of all people with an ORCID.",
        )

    def handle(self, *args, **options):
        if options["person_id"]:
            try:
                people = [Person.objects.get(pk=options["person_id"])]
            except Person.DoesNotExist:
                self.stderr.write(f"Person {options['person_id']} not found.")
                return
        else:
            people = list(Person.objects.filter(orcid__isnull=False).exclude(orcid=""))

        if not people:
            self.stdout.write("No people with ORCID iDs found.")
            return

        synced = 0
        total_suggestions = 0
        errors = 0

        for person in people:
            try:
                suggestions = sync_person_orcid(person)
                total_suggestions += len(suggestions)
                synced += 1
                self.stdout.write(f"  Synced {person} — {len(suggestions)} suggestion(s)")
            except Exception as exc:  # noqa: BLE001
                errors += 1
                self.stderr.write(f"  Error syncing {person}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {synced} synced, {errors} error(s),"
                f" {total_suggestions} suggestion(s) created."
            )
        )
