from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.urls import reverse, resolve


class AuthorPermissionTests(TestCase):
    def setUp(self):
        self.moderator = get_user_model().objects.create_user(username="reviewer", role="moderator", is_staff=True)

    def test_moderator_staff_flag_does_not_grant_authoring(self):
        self.client.force_login(self.moderator)
        routes = [("assessor_developer", []), ("assessor_developer_paper", [999]),
                  ("upload_assessment", []), ("assessor_pool_data", []),
                  ("assessor_pool_block_create", []), ("assessor_pool_randomize", []),
                  ("exam_create_box", [999]), ("exam_save_paper_meta", [999])]
        for name, args in routes:
            with self.subTest(route=name):
                url = reverse(name, args=args)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_legacy_extractor_urls_are_protected(self):
        self.client.force_login(self.moderator)
        for url in ["/paper/999/", "/administrator/traditional-pipeline/paper/999/", "/upload/"]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_anonymous_authoring_redirects_to_login(self):
        self.assertEqual(self.client.get(reverse("assessor_developer")).status_code, 302)

    def test_snapshot_report_and_memo_forms_are_author_only(self):
        context = {"assessment": {"id": 1, "eisa_id": "TEST", "assessor_report": "report.pdf"},
                   "has_memo": True, "dashboard_url": "/", "can_edit_snapshot": False}
        html = render_to_string("core/assessor-developer/randomized_snapshot.html", context)
        self.assertNotIn('value="upload_assessor_report"', html)
        self.assertNotIn('value="upload_memo"', html)
        context["can_edit_snapshot"] = True
        html = render_to_string("core/assessor-developer/randomized_snapshot.html", context)
        self.assertIn('value="upload_assessor_report"', html)
        self.assertIn('value="upload_memo"', html)
