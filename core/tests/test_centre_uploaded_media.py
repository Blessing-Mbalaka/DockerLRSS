from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from django.http import HttpResponse
from core.media_access import protected_media


class CentreUploadedMediaTests(SimpleTestCase):
    def check(self, role, path, offline=True):
        request=RequestFactory().get('/media/'+path)
        request.user=SimpleNamespace(is_authenticated=True,is_superuser=False,role=role,pk=4)
        submission=SimpleNamespace(student_id=None,is_offline=offline,results_are_released=False,
            pdf_file=SimpleNamespace(name='uploads/answer.pdf'))
        with patch('core.media_access.ExamSubmission.objects') as submissions, \
             patch('core.media_access.Assessment.objects') as assessments, \
             patch('core.media_access.ExtractorPaper.objects') as sources, \
             patch('core.media_access.serve',return_value=HttpResponse(b'%PDF-answer')):
            submissions.filter.return_value.first.return_value=submission
            assessments.filter.return_value.exists.return_value=False
            sources.filter.return_value.exists.return_value=False
            return protected_media(request,path).status_code

    def test_centre_can_view_or_download_original_offline_upload(self):
        self.assertEqual(self.check('assessment_center','uploads/answer.pdf'),200)

    def test_centre_does_not_gain_access_to_unreleased_marked_paper(self):
        self.assertEqual(self.check('assessment_center','marked/result.pdf'),403)

    def test_other_learner_cannot_open_offline_upload(self):
        self.assertEqual(self.check('learner','uploads/answer.pdf'),403)

    def test_centre_does_not_gain_access_to_online_learner_original(self):
        self.assertEqual(self.check('assessment_center','uploads/answer.pdf',offline=False),403)
