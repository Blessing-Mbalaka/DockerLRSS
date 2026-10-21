from pathlib import Path
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests


class DemoRegressionTests(TestCase):
    setUp = AssessmentReturnFlowTests.setUp

    def test_qdd_requires_report(self):
        self.assessment.status='QDD Review'
        self.assessment.save(update_fields=['status'])
        self.client.force_login(self.qdd)
        self.client.post(reverse('qdd_moderate_assessment',args=[self.assessment.eisa_id]),{'action':'approve'})
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status,'QDD Review')

    def test_qdd_report_preserves_moderator_and_is_visible_to_qcto(self):
        self.assessment.status='QDD Review'
        self.assessment.moderator_report='moderator_reports/original.docx'
        self.assessment.save(update_fields=['status','moderator_report'])
        self.client.force_login(self.qdd)
        response=self.client.post(reverse('qdd_moderate_assessment',args=[self.assessment.eisa_id]),{'action':'approve','qdd_report':SimpleUploadedFile('review.docx',b'demo report')})
        self.assertEqual(response.status_code,302)
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status,'Submitted to ETQA')
        self.assertEqual(self.assessment.moderator_report.name,'moderator_reports/original.docx')
        self.assertTrue(self.assessment.qdd_report)
        self.client.force_login(self.qcto)
        response=self.client.get(reverse('qcto_dashboard'))
        self.assertContains(response,self.assessment.qdd_report.url)
        self.assertContains(response,'Download QDD Report')
        self.assessment.status='Approved by ETQA'
        self.assessment.save(update_fields=['status'])
        self.assertContains(self.client.get(reverse('qcto_dashboard')),self.assessment.qdd_report.url)

    def test_qdd_invalid_report_does_not_forward(self):
        self.assessment.status='QDD Review'
        self.assessment.save(update_fields=['status'])
        self.client.force_login(self.qdd)
        self.client.post(reverse('qdd_moderate_assessment',args=[self.assessment.eisa_id]),{'action':'approve','qdd_report':SimpleUploadedFile('review.exe',b'bad')})
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status,'QDD Review')
        self.assertFalse(self.assessment.qdd_report)

    def test_templates_compile_and_student_has_no_trailing_code(self):
        from django.template.loader import get_template
        root = Path(__file__).resolve().parents[2]
        for name in ['qdd/_assessment_table.html','qdd/qdd_developer.html','administrator/qdd_developer.html','moderator/moderator_developer.html','qcto/assessment_review.html','qcto/qcto_dashboard.html','qcto/qcto_view_assessment.html','components/report_upload_validation.html','student/write_exam.html','etqa/etqa_assessment.html','etqa/achieved_assessments.html']:
            get_template('core/'+name)
        source=(root/'core/templates/core/student/write_exam.html').read_text(encoding='utf-8')
        self.assertEqual(source.split('</html>',1)[1].strip(),'')
        self.assertIn('answer_node_',source)

