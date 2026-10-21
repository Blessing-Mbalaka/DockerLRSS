import json
import tempfile
from pathlib import Path
from io import StringIO
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from core.models import Qualification, AssessmentCentre, ExtractorPaper, ExtractorUserBox


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SeedProfileTests(TestCase):
    def profile(self, number="PROFILE001"):
        return {"qualification": "Maintenance Planner", "centre_name": "Profile Centre",
                "accounts": [{"email": "profile.centre@example.com", "password": "Test-only-password", "role": "assessment_center"},
                             {"email": "profile.learner@example.com", "password": "Test-only-password", "role": "learner", "student_number": number}]}

    def seed(self, profile, update=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            call_command("seed_demo_users", accounts_file=str(path), update_existing=update, stdout=StringIO())

    def test_profile_creates_centre_before_linked_users(self):
        self.seed(self.profile())
        centre = AssessmentCentre.objects.get(name="Profile Centre")
        for email in ["profile.centre@example.com", "profile.learner@example.com"]:
            user = get_user_model().objects.get(email=email)
            self.assertEqual(user.assessment_centre_id, centre.pk)
            self.assertEqual(user.qualification_id, centre.qualification_assigned_id)
            self.assertTrue(user.check_password("Test-only-password"))
        learner = get_user_model().objects.get(role="learner")
        self.assertEqual(learner.student_number, "PROFILE001")
        self.assertFalse(learner.is_staff)

    def test_missing_student_number_rolls_back_profile(self):
        with self.assertRaises(CommandError):
            self.seed(self.profile(""))
        self.assertFalse(get_user_model().objects.filter(email__startswith="profile.").exists())
        self.assertFalse(AssessmentCentre.objects.filter(name="Profile Centre").exists())

    def test_existing_accounts_are_preserved_without_update_flag(self):
        self.seed(self.profile())
        profile = self.profile()
        profile["accounts"][1]["password"] = "Changed-test-password"
        self.seed(profile)
        learner = get_user_model().objects.get(role="learner")
        self.assertTrue(learner.check_password("Test-only-password"))
        self.seed(profile, update=True)
        learner.refresh_from_db()
        self.assertTrue(learner.check_password("Changed-test-password"))


class ExtendedLetterTests(TestCase):
    def setUp(self):
        self.qual, _ = Qualification.objects.get_or_create(name="Maintenance Planner", defaults={"saqa_id": "101874"})
        self.user = get_user_model().objects.create_user(username="letter-user", email="letters@example.com", password="test", role="assessor_dev", qualification=self.qual)
        self.client.force_login(self.user)
        self.paper = ExtractorPaper.objects.create(module_name=self.qual.name, paper_number="1", paper_letter="A")

    def test_save_and_reload_multiletter_set(self):
        response = self.client.post(reverse("exam_save_paper_meta", args=[self.paper.pk]), {"module_name": self.qual.name, "paper_number": "1", "paper_letter": "aa", "title": "Maintenance Planner 1AA"})
        self.assertEqual(response.status_code, 302)
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.paper_letter, "AA")
        response = self.client.get(reverse("exam_paper", args=[self.paper.pk]))
        self.assertContains(response, 'data-current="AA"')
        self.assertContains(response, 'id="add-set-letter"')

    def test_invalid_set_letter_does_not_change_saved_metadata(self):
        for value in ["A1", "A" * 11, "<script>"]:
            with self.subTest(letter=value):
                response = self.client.post(reverse("exam_save_paper_meta", args=[self.paper.pk]), {"module_name": self.qual.name, "paper_number": "1", "paper_letter": value})
                self.assertEqual(response.status_code, 302)
                self.paper.refresh_from_db()
                self.assertEqual(self.paper.paper_letter, "A")

    def test_multiletter_pool_can_randomize(self):
        self.paper.paper_letter = "AA"
        self.paper.save(update_fields=["paper_letter"])
        for index, number in enumerate(["1.1.1", "2.1.1"]):
            ExtractorUserBox.objects.create(paper=self.paper, x=0, y=0, w=1, h=1, order_index=index, question_number=number, qtype="question", content="{}")
        response = self.client.post(reverse("assessor_pool_randomize"), {"module": self.qual.name, "letter": "AA", "mode": "base"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"), response.json())
