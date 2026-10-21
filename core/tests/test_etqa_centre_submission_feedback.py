from datetime import date
from django.test import TestCase, override_settings
from django.urls import reverse
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests
from core.models import AssessmentCentre, Batch


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EtqaCentreSubmissionFeedbackTests(TestCase):
    def setUp(self):
        AssessmentReturnFlowTests.setUp(self)
        self.centre = AssessmentCentre.objects.create(name="Feedback Centre", qualification_assigned=self.qualification)
        self.batch = Batch.objects.create(center=self.centre, qualification=self.qualification, assessment=self.assessment, assessment_date=date(2026,10,24))
        self.client.force_login(self.etqa)

    def test_submission_sets_flag_and_renders_confirmation_toast(self):
        response = self.client.post(reverse("submit_to_center", args=[self.batch.pk]), follow=True)
        self.batch.refresh_from_db()
        self.assertTrue(self.batch.submitted_to_center)
        self.assertContains(response, "submitted to Feedback Centre for 24 Oct 2026.")
        self.assertContains(response, 'showToast("')
        self.assertContains(response, "Submitted to centre")
        self.assertContains(response, "Recent Centre Batches")

    def test_status_remains_visible_after_refresh(self):
        self.batch.submitted_to_center = True
        self.batch.save(update_fields=["submitted_to_center"])
        response = self.client.get(reverse("etqa_dashboard"))
        self.assertContains(response, "Submitted to centre")
        self.assertContains(response, self.assessment.eisa_id)

    def test_resubmission_does_not_create_duplicate_and_explains_status(self):
        self.batch.submitted_to_center = True
        self.batch.save(update_fields=["submitted_to_center"])
        response = self.client.post(reverse("submit_to_center", args=[self.batch.pk]), follow=True)
        self.assertContains(response, "already submitted to Feedback Centre")
        self.assertEqual(Batch.objects.count(), 1)

    def test_get_does_not_submit_batch(self):
        response = self.client.get(reverse("submit_to_center", args=[self.batch.pk]))
        self.assertEqual(response.status_code, 405)
        self.batch.refresh_from_db()
        self.assertFalse(self.batch.submitted_to_center)
