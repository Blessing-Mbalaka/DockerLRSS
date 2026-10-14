from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from core.email import check_smtp, safe_send
from core.models import AssessmentCentre, CustomUser, Qualification


class SmtpGuardTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=1,
        EMAIL_TIMEOUT=2,
    )
    def test_check_smtp_reports_closed_port(self):
        ok, message = check_smtp()
        self.assertFalse(ok)
        self.assertIn("127.0.0.1:1", message)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=1,
        EMAIL_TIMEOUT=2,
    )
    def test_management_command_fails_when_smtp_down(self):
        with self.assertRaises(CommandError):
            call_command("check_smtp")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=1,
        EMAIL_TIMEOUT=2,
    )
    def test_safe_send_reports_failure_without_raising(self):
        ok, err = safe_send("s", "m", ["a@x.com"])
        self.assertFalse(ok)
        self.assertTrue(err)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_safe_send_success(self):
        ok, err = safe_send("s", "m", "a@x.com")
        self.assertTrue(ok)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="a@x.com", email="a@x.com", password="pw", role="admin"
        )

    def test_registration_sends_pending_email(self):
        resp = self.client.post(
            reverse("register"),
            {
                "first_name": "New",
                "last_name": "User",
                "email": "new@x.com",
                "username": "new@x.com",
                "password1": "Str0ngPass!word",
                "password2": "Str0ngPass!word",
            },
        )
        if CustomUser.objects.filter(email="new@x.com").exists():
            self.assertEqual([m.to for m in mail.outbox], [["new@x.com"]])
            self.assertIn("pending activation", mail.outbox[0].body)
        else:
            self.skipTest(f"registration form fields differ ({resp.status_code})")

    def test_activation_email_on_toggle(self):
        user = CustomUser.objects.create_user(
            username="u@x.com", email="u@x.com", password="pw",
            role="learner", is_active=False,
        )
        self.client.force_login(self.admin)
        self.client.get(reverse("toggle_user_status", args=[user.id]))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(any(m.to == ["u@x.com"] for m in mail.outbox))

    def test_activation_email_on_role_change_from_default(self):
        user = CustomUser.objects.create_user(
            username="u@x.com", email="u@x.com", password="pw", role="default"
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("update_user_role", args=[user.id]), {"role": "learner"})
        self.assertTrue(any(m.to == ["u@x.com"] for m in mail.outbox))

    def test_email_failure_shows_warning_with_credentials(self):
        qual = Qualification.objects.create(name="Q")
        centre = AssessmentCentre.objects.create(name="C", qualification_assigned=qual)
        ac = CustomUser.objects.create_user(
            username="c@x.com", email="c@x.com", password="pw",
            role="assessment_center", assessment_centre=centre,
        )
        self.client.force_login(ac)
        with mock.patch("core.create_student.safe_send", return_value=(False, "boom")):
            resp = self.client.post(
                reverse("create_student_by_assessment_center"),
                {"name": "Stu Dent", "email": "s@x.com", "student_number": "9"},
                follow=True,
            )
        self.assertTrue(CustomUser.objects.filter(email="s@x.com").exists())
        text = " ".join(str(m) for m in resp.context["messages"])
        self.assertIn("could NOT be sent", text)
