import json
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from .models import Qualification, Assessment, AssessmentWritingSession, AssessmentWritingIncident
from .writing_sessions import writing_session, writing_monitor

class WritingRecoveryTests(TestCase):
    def setUp(self):
        self.q = Qualification.objects.create(name='Writing Recovery Test Qualification', saqa_id='writing-recovery-test')
        self.user = get_user_model().objects.create_user(username='learner', email='learner@test.test', role='learner', qualification=self.q)
        self.assessment = Assessment.objects.create(eisa_id='test', paper='Test', qualification=self.q, status='active')
        self.factory = RequestFactory()

    def call(self, method='get', data=None, user=None):
        req = getattr(self.factory, method)('/', data=json.dumps(data), content_type='application/json') if method == 'post' else self.factory.get('/')
        req.user = user or self.user
        return writing_session(req, self.assessment.pk)

    def test_save_resume_and_conflict(self):
        self.assertEqual(self.call().status_code, 200)
        response = self.call('post', {'answers': {'answer_1': 'Recovered answer'}, 'revision': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(self.call().content)['answers']['answer_1'], 'Recovered answer')
        self.assertEqual(self.call('post', {'answers': {}, 'revision': 0}).status_code, 409)

    def test_incident_does_not_submit(self):
        from .models import ExamSubmission
        self.assertEqual(self.call('post', {'incident': 'tab_hidden'}).status_code, 200)
        self.assertEqual(AssessmentWritingIncident.objects.count(), 1)
        self.assertFalse(ExamSubmission.objects.exists())

    def test_wrong_qualification_and_learner_monitor_denied(self):
        self.user.qualification = None
        self.user.save()
        self.assertEqual(self.call().status_code, 403)
        req = self.factory.get('/'); req.user = self.user
        self.assertEqual(writing_monitor(req).status_code, 403)

    def test_invalid_payload(self):
        self.assertEqual(self.call('post', {'answers': [], 'revision': 0}).status_code, 400)
