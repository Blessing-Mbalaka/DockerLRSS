import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Assessment, ExamSubmission, Paper, PdfAnnotation, Qualification


User = get_user_model()


class MarkerJsonEndpointTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.qualification = Qualification.objects.create(
            name="Marker Test Qualification",
            saqa_id="MTQ123",
        )
        self.paper = Paper.objects.create(
            name="Marker Test Paper",
            qualification=self.qualification,
            total_marks=100,
        )
        self.assessment = Assessment.objects.create(
            eisa_id="EISA-MARKER1",
            qualification=self.qualification,
            paper="Marker Test Paper",
            paper_link=self.paper,
            paper_type="randomized",
            status="Released to students",
        )
        self.learner = User.objects.create_user(
            username="marker-json-learner",
            email="marker-json-learner@example.com",
            password="Pass12345",
            role="learner",
            qualification=self.qualification,
            student_number="MARKER-LRN-001",
            is_active=True,
        )
        self.marker = User.objects.create_user(
            username="marker-json-marker",
            email="marker-json-marker@example.com",
            password="Pass12345",
            role="assessor_marker",
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="marker-json-admin",
            email="marker-json-admin@example.com",
            password="Pass12345",
            role="admin",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
        self.internal_moderator = User.objects.create_user(
            username="marker-json-internal",
            email="marker-json-internal@example.com",
            password="Pass12345",
            role="internal_mod",
            is_active=True,
        )
        self.submission = ExamSubmission.objects.create(
            student=self.learner,
            student_number=self.learner.student_number,
            student_name="Marker Json Learner",
            assessment=self.assessment,
            paper=self.paper,
            attempt_number=1,
            pdf_file=SimpleUploadedFile(
                "learner_submission.pdf",
                b"%PDF-1.4\n% marker json test\n",
                content_type="application/pdf",
            ),
        )

    def assertJsonResponse(self, response):
        self.assertTrue(
            response["Content-Type"].startswith("application/json"),
            response["Content-Type"],
        )
        return response.json()

    def test_marker_dashboard_renders_submission_for_marker(self):
        self.client.force_login(self.marker)

        response = self.client.get(
            reverse("assessor_maker_dashboard"),
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.submission.student_number)
        self.assertContains(response, reverse("edit_marker_grade", args=[0]))

    def test_marker_javascript_endpoints_return_json(self):
        self.client.force_login(self.marker)

        grade_response = self.client.post(
            reverse("edit_marker_grade", args=[self.submission.id]),
            {
                "marks": "76",
                "total_marks": "100",
                "feedback": "Marker JSON test feedback.",
            },
            HTTP_HOST="127.0.0.1",
        )
        grade_payload = self.assertJsonResponse(grade_response)
        self.assertTrue(grade_payload["success"])

        list_response = self.client.get(
            reverse("list_annotations", args=[self.submission.id]),
            HTTP_HOST="127.0.0.1",
        )
        list_payload = self.assertJsonResponse(list_response)
        self.assertTrue(list_payload["success"])

        add_response = self.client.post(
            reverse("add_annotation", args=[self.submission.id]),
            data=json.dumps({"type": "tick", "page": 1, "x": 10, "y": 20}),
            content_type="application/json",
            HTTP_HOST="127.0.0.1",
        )
        add_payload = self.assertJsonResponse(add_response)
        self.assertTrue(add_payload["success"])

        log_response = self.client.get(
            reverse("grade_change_log", args=[self.submission.id]),
            HTTP_HOST="127.0.0.1",
        )
        log_payload = self.assertJsonResponse(log_response)
        self.assertTrue(log_payload["success"])

        quick_grade_response = self.client.post(
            reverse("quick_grade_submission", args=[self.submission.id]),
            {
                "marks": "80",
                "total_marks": "100",
                "feedback": "Quick grade JSON test.",
            },
            HTTP_HOST="127.0.0.1",
        )
        quick_grade_payload = self.assertJsonResponse(quick_grade_response)
        self.assertTrue(quick_grade_payload["success"])

        upload_response = self.client.post(
            reverse("upload_marked_paper", args=[self.submission.id]),
            {
                "marks": "82",
                "total_marks": "100",
                "feedback": "Upload marked paper JSON test.",
                "marked_paper": SimpleUploadedFile(
                    "marked.pdf",
                    b"%PDF-1.4\n% marked paper\n",
                    content_type="application/pdf",
                ),
            },
            HTTP_HOST="127.0.0.1",
        )
        upload_payload = self.assertJsonResponse(upload_response)
        self.assertTrue(upload_payload["success"])

    def test_superuser_marker_dashboard_json_endpoints_do_not_return_html(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("edit_marker_grade", args=[self.submission.id]),
            {"marks": "88", "total_marks": "100", "feedback": "Admin marker test."},
            HTTP_HOST="127.0.0.1",
        )

        payload = self.assertJsonResponse(response)
        self.assertTrue(payload["success"])

    def test_student_graded_assessments_page_resolves(self):
        self.client.force_login(self.learner)

        response = self.client.get(
            reverse("student_graded_assessments"),
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Graded Assessments")

    def test_internal_moderator_cannot_delete_marker_annotation(self):
        annotation = PdfAnnotation.objects.create(
            submission=self.submission,
            created_by=self.marker,
            role=self.marker.role,
            ann_type="comment",
            page=1,
            x=0.25,
            y=0.4,
            text="Marker-owned annotation",
        )

        self.client.force_login(self.internal_moderator)
        response = self.client.post(
            reverse("delete_annotations_bulk"),
            data=json.dumps({"ids": [annotation.id]}),
            content_type="application/json",
            HTTP_HOST="127.0.0.1",
        )

        payload = self.assertJsonResponse(response)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["deleted_count"], 0)
        self.assertEqual(payload["skipped_count"], 1)
        self.assertTrue(PdfAnnotation.objects.filter(id=annotation.id).exists())
