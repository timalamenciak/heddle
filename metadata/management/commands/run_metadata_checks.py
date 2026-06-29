from django.core.management.base import BaseCommand

from metadata.services import run_all_checks


class Command(BaseCommand):
    help = "Run all enabled metadata checks over every Person and Organization record."

    def handle(self, *args, **options):
        counts = run_all_checks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {counts['people_checked']} people, "
                f"{counts['orgs_checked']} orgs. "
                f"{counts['opened']} issues opened, "
                f"{counts['resolved']} resolved."
            )
        )
