from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests
from core.models import Paper, ExamNode, ExamSubmission


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LearnerCreationSubmissionTests(TestCase):
    setUp = AssessmentReturnFlowTests.setUp

    def create_learner(self, number=None):
        self.client.force_login(self.admin)
        data = {"name": "Demo Learner", "email": "created-learner@example.com",
                "role": "learner", "qualification": self.qualification.pk}
        if number is not None:
            data["student_number"] = number
        with patch("core.views.send_account_creation_email", return_value=True):
            return self.client.post(reverse("user_management"), data)

    def test_user_management_requires_student_number(self):
        response = self.create_learner()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(get_user_model().objects.filter(email="created-learner@example.com").exists())

    def test_created_learner_can_submit_assessment(self):
        self.create_learner("DEMO-001")
        learner = get_user_model().objects.get(email="created-learner@example.com")
        self.assertEqual(learner.student_number, "DEMO-001")
        self.assertEqual(learner.role, "learner")
        self.assertFalse(learner.is_staff)
        paper = Paper.objects.create(name="Demo submission", qualification=self.qualification)
        node = ExamNode.objects.create(paper=paper, node_type="question", number="1", text="Question", marks="5")
        self.assessment.paper_link = paper
        self.assessment.status = "Released to students"
        self.assessment.save(update_fields=["paper_link", "status"])
        self.client.force_login(learner)
        response = self.client.post(reverse("submit_exam", args=[self.assessment.pk]),
                                    {"answer_node_" + str(node.pk): "My demo answer"})
        self.assertEqual(response.status_code, 302)
        submission = ExamSubmission.objects.get(student=learner, assessment=self.assessment)
        self.assertTrue(submission.pdf_file)

    def test_duplicate_student_number_is_rejected(self):
        self.assessor.student_number = "TAKEN-001"
        self.assessor.save(update_fields=["student_number"])
        self.create_learner("TAKEN-001")
        self.assertFalse(get_user_model().objects.filter(email="created-learner@example.com").exists())

    def test_missing_number_does_not_label_learner_as_staff(self):
        learner = get_user_model().objects.create_user(username="no-number", email="no-number@example.com",
                                                       password="test", role="learner", qualification=self.qualification)
        self.client.force_login(learner)
        response = self.client.post(reverse("submit_exam", args=[self.assessment.pk]), {})
        text = " ".join(str(m) for m in get_messages(response.wsgi_request))
        self.assertIn("no student number", text)
        self.assertNotIn("staff/superuser", text)
        self.assertFalse(ExamSubmission.objects.filter(student=learner).exists())
        response = self.client.post(reverse("submit_exam", args=[self.assessment.pk]), {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
