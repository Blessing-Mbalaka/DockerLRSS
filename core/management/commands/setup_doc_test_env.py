"""
Management command: setup_doc_test_env
========================================
One-shot setup for the end-to-end documentation test run:
  1. Syncs qualification YAML → DB (ensures 'Test Documentation' exists)
  2. Assigns 'Test Documentation' qualification to all seed_test_ accounts
  3. Reports a summary

Usage:
    python manage.py setup_doc_test_env
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Sync qualifications and assign Test Documentation qual to all seed test users."

    def handle(self, *args, **options):
        from core.qualification_registry import sync_registry_to_db
        from core.models import Qualification

        # ── 1. Sync YAML → DB ─────────────────────────────────────────────
        self.stdout.write("Syncing qualification registry to database…")
        sync_registry_to_db()
        all_quals = list(Qualification.objects.values_list("name", flat=True))
        self.stdout.write(self.style.SUCCESS(f"  Qualifications in DB: {all_quals}"))

        # ── 2. Get the target qualification ───────────────────────────────
        try:
            qual = Qualification.objects.get(name="Test Documentation")
        except Qualification.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    "'Test Documentation' not found in DB even after sync. "
                    "Check core/config/qualifications.yaml."
                )
            )
            return

        self.stdout.write(f"  Using qualification: {qual} (pk={qual.pk})")

        # ── 3. Assign to all seed test users ──────────────────────────────
        self.stdout.write("Assigning qualification to seed test users…")
        qs = User.objects.filter(username__startswith="seed_test_")
        updated = qs.update(qualification=qual)
        self.stdout.write(
            self.style.SUCCESS(f"  Updated {updated} seed test users → '{qual.name}'")
        )

        # ── 4. Summary by role ────────────────────────────────────────────
        self.stdout.write("\nBreakdown by role:")
        from django.db.models import Count
        for row in (
            qs.values("role")
            .annotate(n=Count("id"))
            .order_by("role")
        ):
            self.stdout.write(f"  {row['role']:25s} {row['n']:4d}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Setup complete. Ready to run generate_workflow_docs.py"))
