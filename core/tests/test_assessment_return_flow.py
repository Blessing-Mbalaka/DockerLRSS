import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.automated_notifications import STATUS_TEMPLATES, build_user_notifications
from core.models import Assessment, Feedback, Qualification


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AssessmentReturnFlowTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.qualification = Qualification.objects.create(
            name="Workflow Qualification",
            saqa_id="WF123",
        )
        self.assessor = User.objects.create_user(
            username="assessor@example.com",
            email="assessor@example.com",
            password="Pass12345",
            role="assessor_dev",
            qualification=self.qualification,
            is_active=True,
        )
        self.moderator = User.objects.create_user(
            username="moderator@example.com",
            email="moderator@example.com",
            password="Pass12345",
            role="moderator",
            qualification=self.qualification,
            is_active=True,
        )
        self.qcto = User.objects.create_user(
            username="qcto@example.com",
            email="qcto@example.com",
            password="Pass12345",
            role="qcto",
            qualification=self.qualification,
            is_active=True,
        )
        self.assessment = Assessment.objects.create(
            eisa_id="EISA-FLOW1",
            qualification=self.qualification,
            paper="Paper 1",
            paper_type="admin_upload",
            created_by=self.assessor,
            status="Submitted to Moderator",
        )
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="Pass12345",
            role="admin",
            is_active=True,
        )
        self.etqa = User.objects.create_user(
            username="etqa@example.com",
            email="etqa@example.com",
            password="Pass12345",
            role="etqa",
            qualification=self.qualification,
            is_active=True,
        )
        self.qdd = User.objects.create_user(
            username="qdd@example.com",
            email="qdd@example.com",
            password="Pass12345",
            role="qdd",
            qualification=self.qualification,
            is_active=True,
        )
        self.assessment_center = User.objects.create_user(
            username="center@example.com",
            email="center@example.com",
            password="Pass12345",
            role="assessment_center",
            qualification=self.qualification,
            is_active=True,
        )

    def test_moderator_return_keeps_paper_available_for_assessor_corrections(self):
        self.client.force_login(self.moderator)

        response = self.client.post(
            reverse("moderate_assessment", args=[self.assessment.eisa_id]),
            {
                "action": "return",
                "return_comments": "Please fix question 3.",
            },
        )

        self.assertRedirects(response, reverse("moderator_review_list"))
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, "Returned for Changes")
        self.assertFalse(self.assessment.forward_to_moderator)
        self.assertEqual(self.assessment.moderator_notes, "Please fix question 3.")
        self.assertTrue(
            Feedback.objects.filter(
                assessment=self.assessment,
                to_user="Assessor/Developer",
                message="Please fix question 3.",
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["assessor@example.com"])

    def test_qcto_reject_returns_to_moderator_instead_of_archive(self):
        self.assessment.status = "Submitted to QCTO"
        self.assessment.forward_to_moderator = False
        self.assessment.save(update_fields=["status", "forward_to_moderator"])
        mail.outbox = []
        self.client.force_login(self.qcto)

        response = self.client.post(
            reverse("qcto_assessment_review"),
            {
                "eisa_id": self.assessment.eisa_id,
                "action": "reject",
                "qcto_notes": "Moderator must review the memo alignment.",
            },
        )

        self.assertRedirects(response, reverse("qcto_assessment_review"))
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, "Submitted to Moderator")
        self.assertTrue(self.assessment.forward_to_moderator)
        self.assertEqual(
            self.assessment.qcto_notes,
            "Moderator must review the memo alignment.",
        )
        self.assertTrue(
            Feedback.objects.filter(
                assessment=self.assessment,
                to_user="Moderator",
                message="Moderator must review the memo alignment.",
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["moderator@example.com"])

    def test_qcto_approval_still_requires_report_and_forwards_to_qdd(self):
        self.assessment.status = "Submitted to QCTO"
        self.assessment.save(update_fields=["status"])
        self.client.force_login(self.qcto)

        report = SimpleUploadedFile(
            "qcto_report.docx",
            b"test report",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(
            reverse("qcto_assessment_review"),
            {
                "eisa_id": self.assessment.eisa_id,
                "action": "approve",
                "qcto_notes": "Approved.",
                "qcto_report": report,
            },
        )

        self.assertRedirects(response, reverse("qcto_assessment_review"))
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, "QDD Review")
        self.assertEqual(self.assessment.qcto_notes, "Approved.")

    def test_qcto_approval_uses_existing_report_if_previous_submit_uploaded_it(self):
        self.assessment.status = "Submitted to QCTO"
        self.assessment.qcto_report.save(
            "existing_qcto_report.docx",
            SimpleUploadedFile(
                "existing_qcto_report.docx",
                b"existing report",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
        self.client.force_login(self.qcto)

        response = self.client.post(
            reverse("qcto_assessment_review"),
            {
                "eisa_id": self.assessment.eisa_id,
                "action": "approve",
                "qcto_notes": "Approved with existing report.",
            },
        )

        self.assertRedirects(response, reverse("qcto_assessment_review"))
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, "QDD Review")
        self.assertEqual(self.assessment.qcto_notes, "Approved with existing report.")

    def test_qdd_dashboard_shows_qdd_review_items_without_user_qualification(self):
        qdd_without_qualification = User.objects.create_user(
            username="qdd-unassigned@example.com",
            email="qdd-unassigned@example.com",
            password="Pass12345",
            role="qdd",
            is_active=True,
        )
        self.assessment.status = "QDD Review"
        self.assessment.save(update_fields=["status"])
        self.client.force_login(qdd_without_qualification)

        response = self.client.get(reverse("qdd_developer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.assessment.eisa_id)
        self.assertContains(response, "QDD Review")

    def test_qdd_notifications_show_qdd_review_items_without_user_qualification(self):
        qdd_without_qualification = User.objects.create_user(
            username="qdd-notifications@example.com",
            email="qdd-notifications@example.com",
            password="Pass12345",
            role="qdd",
            is_active=True,
        )
        self.assessment.status = "QDD Review"
        self.assessment.save(update_fields=["status"])

        notifications, _filters = build_user_notifications(qdd_without_qualification)

        self.assertIn(
            self.assessment.eisa_id,
            {note["eisa_id"] for note in notifications},
        )

    def test_qdd_user_cannot_use_qcto_review_page(self):
        self.assessment.status = "Submitted to QCTO"
        self.assessment.save(update_fields=["status"])
        self.client.force_login(self.qdd)

        response = self.client.get(reverse("qcto_assessment_review"))

        self.assertRedirects(response, reverse("qdd_developer_dashboard"))

    def test_qcto_review_page_shows_visible_return_comments_field(self):
        self.assessment.status = "Submitted to QCTO"
        self.assessment.save(update_fields=["status"])
        self.client.force_login(self.qcto)

        response = self.client.get(reverse("qcto_assessment_review"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="qcto-visible-notes-{self.assessment.id}"')
        self.assertContains(response, "Comments for returned corrections")
        self.assertContains(response, 'name="qcto_notes"')
        self.assertContains(response, 'name="qcto_report"')
        self.assertContains(response, 'name="action" value="approve"')
        self.assertContains(response, 'name="action" value="reject"')

    def test_all_configured_statuses_email_and_dashboard_notify_target_roles(self):
        role_users = {
            "admin": self.admin,
            "assessor_dev": self.assessor,
            "moderator": self.moderator,
            "qcto": self.qcto,
            "etqa": self.etqa,
            "qdd": self.qdd,
            "assessment_center": self.assessment_center,
        }

        for status, template in STATUS_TEMPLATES.items():
            with self.subTest(status=status):
                mail.outbox = []
                self.assessment.status = "draft"
                self.assessment.save(update_fields=["status"])
                mail.outbox = []

                self.assessment.status = status
                self.assessment.save(update_fields=["status"])

                expected_roles = template["recipient_roles"]
                expected_emails = sorted(
                    role_users[role].email
                    for role in expected_roles
                    if role in role_users
                )
                actual_emails = sorted(
                    recipient
                    for message in mail.outbox
                    for recipient in message.to
                )
                self.assertEqual(actual_emails, expected_emails)

                for role, user in role_users.items():
                    notifications, _filters = build_user_notifications(user)
                    statuses = {note["status"] for note in notifications}
                    if role in expected_roles:
                        self.assertIn(status, statuses)
                    else:
                        self.assertNotIn(status, statuses)

    def test_role_dashboards_render_workflow_notifications(self):
        dashboard_cases = [
            (self.assessor, "assessor_developer", "Returned for Changes"),
            (self.moderator, "moderator_developer", "Submitted to Moderator"),
            (self.qcto, "qcto_dashboard", "Submitted to QCTO"),
            (self.etqa, "etqa_dashboard", "Submitted to ETQA"),
            (self.qdd, "qdd_developer_dashboard", "QDD Review"),
            (self.assessment_center, "assessment_center", "Released to students"),
            (self.admin, "admin_dashboard", "Approved by ETQA"),
        ]

        for user, url_name, status in dashboard_cases:
            with self.subTest(role=user.role, status=status, dashboard=url_name):
                self.assessment.status = "draft"
                self.assessment.save(update_fields=["status"])
                self.assessment.status = status
                self.assessment.save(update_fields=["status"])

                self.client.force_login(user)
                response = self.client.get(reverse(url_name))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="assessment-notifications"')
                self.assertContains(response, self.assessment.eisa_id)
                self.assertContains(response, status)
