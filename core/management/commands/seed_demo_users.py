import csv
import json
import secrets
from pathlib import Path
from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from core.models import Qualification, AssessmentCentre
from core.qualification_registry import sync_registry_to_db


class Command(BaseCommand):
    help = "Create demo role accounts and centres without flushing existing data or sending email."

    def add_arguments(self, parser):
        parser.add_argument("--credentials-file", default=str(Path(settings.BASE_DIR) / "var" / "demo-credentials.csv"))
        parser.add_argument("--accounts-file", help="Private JSON profile containing qualification, centre and accounts.")
        parser.add_argument("--update-existing", action="store_true", help="Update only accounts explicitly listed in the private profile.")


    def handle(self, *args, **options):
        if options.get("accounts_file"):
            return self.seed_profile(options)
        sync_registry_to_db()
        User = get_user_model()
        rows = []
        targets = [("admin", None, None, "demo.admin@example.com"),
                   ("qdd", None, None, "demo.qdd@example.com")]
        for name, code in [("Maintenance Planner", "mp"), ("Quality Controller", "qc"), ("Chemical Plant Operator", "cpo")]:
            qual = Qualification.objects.get(name=name)
            centre, _ = AssessmentCentre.objects.get_or_create(name="Demo " + name + " Centre",
                         defaults={"location": "Demo", "qualification_assigned": qual})
            if centre.qualification_assigned_id != qual.pk:
                raise CommandError("Existing demo centre has a different qualification; no reassignment was made.")
            for role in ["assessor_dev", "moderator", "qcto", "etqa", "assessment_center", "learner", "assessor_marker", "internal_mod", "external_mod"]:
                targets.append((role, qual, centre, "demo." + code + "." + role + "@example.com"))
        for role, qual, centre, email in targets:
            if User.objects.filter(email=email).exists():
                continue
            password = secrets.token_urlsafe(15)
            learner = role == "learner"
            user = User.objects.create_user(username=email, email=email, password=password,
                    first_name="Demo", last_name=role.replace("_", " ").title(), role=role,
                    qualification=qual, assessment_centre=centre if role in {"learner", "assessment_center"} else None,
                    student_number=("DEMO-" + str(qual.saqa_id)) if learner else None,
                    is_active=True, is_staff=not learner, is_superuser=role == "admin")
            rows.append({"email": email, "password": password, "role": role,
                         "qualification": qual.name if qual else "All",
                         "assessment_centre": centre.name if centre and role in {"learner", "assessment_center"} else "",
                         "student_number": user.student_number or ""})
        target = Path(options["credentials_file"]).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.exists() and target.stat().st_size > 0
        if rows:
            with target.open("a", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                if not existing:
                    writer.writeheader()
                writer.writerows(rows)
            try:
                target.chmod(0o600)
            except OSError:
                pass
        self.stdout.write(self.style.SUCCESS("Created " + str(len(rows)) + " demo users. Credentials: " + str(target)))

    @transaction.atomic
    def seed_profile(self, options):
        profile_path = Path(options["accounts_file"]).resolve()
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError("Cannot load private account profile: " + str(exc))
        accounts = profile.get("accounts", [])
        roles = dict(get_user_model().ROLE_CHOICES)
        emails = set()
        for account in accounts:
            email = str(account.get("email", "")).strip().lower()
            if not email or email in emails or not account.get("password") or account.get("role") not in roles:
                raise CommandError("Each profile account needs a unique email, password, and valid role.")
            emails.add(email)
        sync_registry_to_db()
        qual = Qualification.objects.get(name=profile["qualification"])
        centre, _ = AssessmentCentre.objects.get_or_create(
            name=profile.get("centre_name") or "Demo " + qual.name + " Centre",
            defaults={"location": "Demo", "qualification_assigned": qual})
        if centre.qualification_assigned_id != qual.pk:
            raise CommandError("Profile centre belongs to a different qualification; no reassignment was made.")
        User = get_user_model()
        created = updated = skipped = 0
        for account in accounts:
            email = account["email"].strip().lower()
            user = User.objects.filter(email=email).first()
            if user is not None and not options["update_existing"]:
                skipped += 1
                continue
            role = account["role"]
            number = str(account.get("student_number", "")).strip() if role == "learner" else None
            if role == "learner":
                if not number or len(number) > 50:
                    raise CommandError("A learner needs a student number of 1 to 50 characters.")
                duplicate = User.objects.filter(student_number=number)
                if user is not None:
                    duplicate = duplicate.exclude(pk=user.pk)
                if duplicate.exists():
                    raise CommandError("The learner student number already belongs to another account.")
            is_new = user is None
            if is_new:
                user = User(username=email, email=email)
            user.role = role
            user.qualification = qual
            user.assessment_centre = centre if role in {"assessment_center", "learner"} else None
            user.student_number = number
            user.first_name = "Demo"
            user.last_name = role.replace("_", " ").title()
            user.is_active = True
            user.is_staff = role != "learner"
            user.is_superuser = False
            user.set_password(account["password"])
            user.save()
            if is_new:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"Profile seeded: {created} created, {updated} updated, {skipped} unchanged; qualification: {qual.name}; centre: {centre.name}. No emails sent."))
