from io import BytesIO
from decimal import Decimal
from unittest.mock import patch
from datetime import date
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader, PdfWriter
from core.models import Assessment, AssessmentCentre, Batch, ExamSubmission, Paper, ExtractorPaper, ExtractorUserBox, QuestionUse
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests
from core.paper_utils import build_randomized_from_pool_only, RandomizationPoolError
from core.word_pdf import lock_pdf


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ControlledReleaseTests(TestCase):
    setUp = AssessmentReturnFlowTests.setUp

    def user(self, role, **kwargs):
        return get_user_model().objects.create_user(username=role, email=role+'@example.test',
            password='test123', role=role, qualification=self.qualification, **kwargs)

    def submission(self):
        learner = self.user('learner', student_number='LEARNER-01')
        self.paper = Paper.objects.create(name='Test paper', qualification=self.qualification)
        return ExamSubmission.objects.create(student=learner, assessment=self.assessment, paper=self.paper, attempt_number=1,
            marks=70, total_marks=100, internal_marks=71, external_marks=72,
            internal_total_marks=100, external_total_marks=100)

    def test_graded_results_hidden_until_etqa_manual_release(self):
        s = self.submission()
        self.client.force_login(s.student)
        self.assertEqual(self.client.get(reverse('student_results')).context['results'], [])
        self.assertEqual(self.client.get(reverse('student_graded_assessments')).context['graded_results'], [])
        self.client.force_login(self.user('etqa'))
        self.client.post(reverse('etqa_results_release'), {'submission_id': s.pk, 'offline_confirmed': 'yes'})
        s.refresh_from_db(); self.assertTrue(s.results_are_released)
        self.client.force_login(s.student)
        self.assertEqual(len(self.client.get(reverse('student_results')).context['results']), 1)

    def test_release_requires_both_moderation_stages_and_offline_confirmation(self):
        s = self.submission(); s.external_marks = None; s.save()
        self.client.force_login(self.user('etqa'))
        url=reverse('etqa_results_release')
        self.client.post(url, {'submission_id': s.pk, 'offline_confirmed': 'yes'})
        s.refresh_from_db(); self.assertIsNone(s.results_release_at)
        s.external_marks=72; s.save()
        self.client.post(url, {'submission_id': s.pk})
        s.refresh_from_db(); self.assertIsNone(s.results_release_at)

    def test_learner_cannot_release_or_see_etqa_pages(self):
        s=self.submission(); self.client.force_login(s.student)
        for name in ['etqa_results_release','etqa_reports','etqa_centre_release']:
            self.assertEqual(self.client.get(reverse(name)).status_code,403)
        self.assertEqual(self.client.post(reverse('etqa_results_release'),{'submission_id':s.pk,'offline_confirmed':'yes'}).status_code,403)

    def test_regrading_holds_previously_released_results(self):
        s=self.submission(); s.results_release_at=timezone.now(); s.save()
        self.assertTrue(s.results_are_released)
        s.external_marks=Decimal('80'); s.save(update_fields=['external_marks'])
        s.refresh_from_db(); self.assertIsNone(s.results_release_at)

    def test_centre_only_gets_its_released_encrypted_pdf(self):
        centre=AssessmentCentre.objects.create(name='Centre', qualification_assigned=self.qualification)
        centre_user=self.user('assessment_center', assessment_centre=centre)
        other=AssessmentCentre.objects.create(name='Other', qualification_assigned=self.qualification)
        batch=Batch.objects.create(center=centre, qualification=self.qualification, assessment=self.assessment,
            assessment_date=date.today(), submitted_to_center=True)
        self.client.force_login(centre_user)
        url=reverse('centre_protected_paper',args=[batch.pk])
        self.assertEqual(self.client.get(url).status_code,404)
        self.client.force_login(self.user('etqa'))
        writer=PdfWriter(); writer.add_blank_page(width=595,height=842); buf=BytesIO(); writer.write(buf)
        with patch('core.centre_release_views.word_for_assessment',return_value=b'word'), patch('core.centre_release_views.convert_word_to_pdf',return_value=buf.getvalue()):
            self.client.post(reverse('etqa_centre_release'), {'batch_id':batch.pk,'pdf_password':'demo-password','offline_confirmed':'yes'})
        batch.refresh_from_db(); self.assertIsNotNone(batch.paper_release_at)
        self.assertIn('demo-password',mail.outbox[-1].body)
        self.assertEqual(mail.outbox[-1].to,[centre_user.email])
        reader=PdfReader(BytesIO(bytes(batch.locked_paper_pdf))); self.assertTrue(reader.is_encrypted)
        self.assertEqual(reader.decrypt('wrong'),0); self.assertNotEqual(reader.decrypt('demo-password'),0)
        self.client.force_login(centre_user); self.assertEqual(self.client.get(url).status_code,200)
        centre_user.assessment_centre=other; centre_user.save()
        self.assertEqual(self.client.get(url).status_code,404)

    def test_email_failure_keeps_centre_paper_unreleased(self):
        centre=AssessmentCentre.objects.create(name='Centre', qualification_assigned=self.qualification)
        self.user('assessment_center',assessment_centre=centre)
        batch=Batch.objects.create(center=centre, qualification=self.qualification, assessment=self.assessment,
            assessment_date=date.today(),submitted_to_center=True)
        self.client.force_login(self.user('etqa'))
        with patch('core.centre_release_views.word_for_assessment',return_value=b'word'), patch('core.centre_release_views.convert_word_to_pdf',return_value=b'pdf'), patch('core.centre_release_views.lock_pdf',return_value=b'locked'), patch('core.centre_release_views.send_mail',side_effect=RuntimeError('offline')):
            self.client.post(reverse('etqa_centre_release'),{'batch_id':batch.pk,'pdf_password':'demo-password','offline_confirmed':'yes'})
        batch.refresh_from_db(); self.assertIsNone(batch.paper_release_at); self.assertIsNone(batch.locked_paper_pdf)

    def test_report_centre_access_denied_and_etqa_downloads_all_roles(self):
        self.assessment.assessor_report.save('report.docx', ContentFile(b'report'))
        self.client.force_login(self.user('etqa'))
        self.assertContains(self.client.get(reverse('etqa_reports')),'Assessor Developer')
        url=reverse('workflow_report_download',args=[self.assessment.pk,'assessor'])
        self.assertEqual(self.client.get(url).status_code,200)
        self.client.force_login(self.user('assessment_center'))
        self.assertEqual(self.client.get(url).status_code,403)

    def test_assessor_report_is_required_even_with_memo(self):
        self.assessment.paper_type='randomized'; self.assessment.memo=None
        self.assessment.memo_file='memos/test.docx'; self.assessment.status='draft'; self.assessment.save()
        self.client.force_login(self.assessor)
        self.client.post(reverse('assessor_randomized_snapshot',args=[self.assessment.pk]),{'action':'forward_moderator'})
        self.assessment.refresh_from_db(); self.assertEqual(self.assessment.status,'draft')

    def test_question_used_once_per_set_but_available_in_another_set(self):
        source=ExtractorPaper.objects.create(title='Source', module_name=self.qualification.name, paper_number='1',paper_letter='A')
        box=ExtractorUserBox.objects.create(paper=source,x=0,y=0,w=1,h=1,qtype='question',question_number='1',marks='5',content='Example')
        def output(number):
            return Paper.objects.create(name='Output',qualification=self.qualification,structure_json={'randomization':{'set_number':number}})
        first=output('1'); build_randomized_from_pool_only(first,self.qualification.name,'A',base_extractor=source)
        self.assertEqual(QuestionUse.objects.filter(box=box,set_number='1').count(),1)
        second=output('1')
        with self.assertRaises(RandomizationPoolError):
            build_randomized_from_pool_only(second,self.qualification.name,'A',base_extractor=source)
        self.assertEqual(second.nodes.count(),0)
        third=output('2'); build_randomized_from_pool_only(third,self.qualification.name,'A',base_extractor=source)
        self.assertEqual(QuestionUse.objects.filter(box=box).count(),2)

    def test_cover_and_overlay_data_are_saved_in_submission(self):
        from core.models import ExamNode
        learner=self.user('learner',student_number='COVER-001',identity_number='123456')
        paper=Paper.objects.create(name='Paper',qualification=self.qualification)
        node=ExamNode.objects.create(paper=paper,node_type='question',number='1',marks='5',text='Question')
        self.assessment.paper_link=paper; self.assessment.status='Released to students'; self.assessment.save()
        self.client.force_login(learner)
        response=self.client.get(reverse('write_exam',args=[self.assessment.pk]))
        self.assertContains(response,'123456')
        self.client.post(reverse('submit_exam',args=[self.assessment.pk]),{'answer_node_'+str(node.pk):'Answer',
            'cover_0':'Learner Name','cover_2':'987654', 'notes_node_'+str(node.pk):'[{"text":"Written note"}]'})
        s=ExamSubmission.objects.get(student=learner)
        self.assertEqual(s.learner_cover['Identity number'],'987654')
        self.assertIn('Written note',str(s.writing_notes))
        with s.pdf_file.open('rb') as pdf:
            text=''.join(page.extract_text() for page in PdfReader(pdf).pages)
        self.assertIn('987654',text); self.assertIn('Written note',text)

    def test_new_release_pages_render(self):
        self.submission(); self.client.force_login(self.user('etqa'))
        for name in ['etqa_results_release','etqa_reports','etqa_centre_release']:
            self.assertEqual(self.client.get(reverse(name)).status_code,200)

    def test_release_page_handles_legacy_submission_without_paper(self):
        s=self.submission(); s.paper=None; s.assessment=None; s.save()
        self.client.force_login(self.user('etqa'))
        self.assertContains(self.client.get(reverse('etqa_results_release')),'Paper no longer available')

    def test_cover_metadata_comes_from_captured_cover(self):
        from core.models import ExamNode
        from core.learner_cover import cover_defaults
        s=self.submission(); self.assessment.paper_link=self.paper; self.assessment.save()
        ExamNode.objects.create(paper=self.paper,node_type='cover_page',content=[{'type':'table','rows':[['NQF LEVEL','4'],['CREDITS','173'],['DURATION','2 HOURS']]}])
        data=cover_defaults(s.student,self.assessment)
        self.assertEqual(data['NQF level'],'4'); self.assertEqual(data['Credits'],'173'); self.assertEqual(data['Duration'],'3 hours')

    def test_legacy_randomizer_also_rejects_reuse_in_same_set(self):
        from core.utils.extractor.bank import build_test_from_boxes
        source=ExtractorPaper.objects.create(title='Legacy',module_name=self.qualification.name,paper_letter='A')
        box=ExtractorUserBox.objects.create(paper=source,x=0,y=0,w=1,h=1,qtype='question',question_number='1')
        build_test_from_boxes(self.qualification.name,'First',[box],'1')
        with self.assertRaises(ValueError): build_test_from_boxes(self.qualification.name,'Duplicate',[box],'1')
        build_test_from_boxes(self.qualification.name,'Another set',[box],'2')
        self.assertEqual(QuestionUse.objects.filter(box=box).count(),2)

    def test_unreleased_marked_pdf_cannot_be_opened_by_learner(self):
        from django.test import RequestFactory
        from core.media_access import protected_media
        s=self.submission(); s.marked_paper.save('marked.pdf',ContentFile(b'%PDF-demo'))
        request=RequestFactory().get('/media/'+s.marked_paper.name); request.user=s.student
        self.assertEqual(protected_media(request,s.marked_paper.name,document_root=self.media_root).status_code,403)
        s.results_release_at=timezone.now();s.save()
        response=protected_media(request,s.marked_paper.name,document_root=self.media_root)
        self.assertEqual(response.status_code,200);response.close()

    def test_missing_word_converter_fails_without_rebuilding_pdf(self):
        from core.word_pdf import convert_word_to_pdf, ConversionUnavailable
        with override_settings(LIBREOFFICE_BINARY=''), patch('core.word_pdf.shutil.which',return_value=None), patch('core.word_pdf.Path.is_file',return_value=False):
            with self.assertRaises(ConversionUnavailable): convert_word_to_pdf(b'word')
