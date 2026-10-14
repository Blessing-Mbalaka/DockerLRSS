from django.core.management.base import BaseCommand, CommandError

from core.email import check_smtp


class Command(BaseCommand):
    help = "Check that the configured SMTP server is reachable (e.g. port not blocked on the VPS)."

    def handle(self, *args, **options):
        ok, message = check_smtp()
        if not ok:
            raise CommandError(message)
        self.stdout.write(self.style.SUCCESS(message))
