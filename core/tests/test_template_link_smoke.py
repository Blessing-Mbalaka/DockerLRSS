from pathlib import Path
from django.test import TestCase
from django.urls import reverse,resolve
from django.template.loader import render_to_string
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests
from core.models import Paper,ExamNode
from django.contrib.auth import get_user_model
from html.parser import HTMLParser
from urllib.parse import urlsplit

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('a','form'):
            u=attrs.get('href' if tag=='a' else 'action','')
            if u.startswith('/') and not u.startswith(('/static/','/media/','//')):self.urls.append(u)

class PageSmokeTests(TestCase):
    setUp=AssessmentReturnFlowTests.setUp
    def assert_page(self,name,args=None):
        response=self.client.get(reverse(name,args=args),follow=True)
        self.assertEqual(response.status_code,200,(name,response.status_code))
        parser=Links();parser.feed(response.content.decode())
        for url in parser.urls:
            with self.subTest(page=name,url=url):resolve(urlsplit(url).path)
        print('PASS page:',name,'links:',len(parser.urls))

    def test_staff_pages_and_rendered_links(self):
        for user,names in [
            (self.admin,['admin_dashboard','administrator_dashboards','administrator_paperbank','administrator_uploads','user_management','manage_qualifications','assessment_centres','upload_assessment','assessment_archive','review_saved_selector']),
            (self.assessor,['assessor_developer','assessment_archive','upload_assessment','assessor_reports']),
            (self.moderator,['moderator_developer','moderator_review_list']),
            (self.qcto,['qcto_dashboard','qcto_assessment_review','qcto_archive','qcto_reports','qcto_compliance']),
            (self.qdd,['qdd_developer_dashboard']),
            (self.etqa,['etqa_dashboard','etqa_assessment_view','achieved_assessments']),
        ]:
            self.client.force_login(user)
            for name in names:
                with self.subTest(role=user.role,page=name):self.assert_page(name)

    def test_real_string_paper_links_and_learner_pages(self):
        paper=Paper.objects.create(name='Demo audit paper',qualification=self.qualification,created_by=self.assessor)
        self.assessment.paper_link=paper
        self.assessment.status='Released to students'
        self.assessment.save(update_fields=['paper_link','status'])
        ExamNode.objects.create(paper=paper,node_type='question',number='1',text='Demo question',marks='5')
        paper.refresh_from_db()
        for name in ['load_saved_paper','randomize_paper_structure','write_paper_simple','submit_paper_simple','student_registration','save_blocks','save-blocks']:
            path=reverse(name,args=[paper.pk])
            self.assertEqual(str(next(iter(resolve(path).kwargs.values()))),str(paper.pk))
        self.client.force_login(self.admin)
        self.assert_page('load_saved_paper',[paper.pk])
        self.assert_page('administrator_uploads')
        learner=get_user_model().objects.create_user(username='audit-learner',email='audit-learner@example.com',password='test',role='learner',qualification=self.qualification,student_number='AUDIT001',first_name='Demo',last_name='Learner')
        self.client.force_login(learner)
        for name,args in [('student_dashboard',None),('papers_demo',None),('write_paper_simple',[paper.pk]),('write_exam',[self.assessment.pk])]:
            with self.subTest(page=name):self.assert_page(name,args)

    def test_upload_table_uses_existing_extraction_action(self):
        html=render_to_string('partials/uploads_table.html',{'uploads':[self.assessment],'upload_type':'raw'})
        self.assertIn(reverse('assessor_developer'),html)
        self.assertIn('value="open_pipeline"',html)
        self.assertIn('name="assessment_id"',html)

    def test_templates_compile(self):
        from django.template import engines
        root=Path(__file__).resolve().parents[2]
        for p in (root/'core/templates').rglob('*.html'):
            if '_old_styled' not in str(p):
                with self.subTest(template=str(p)):
                    engines['django'].from_string(p.read_text(encoding='utf-8'))

