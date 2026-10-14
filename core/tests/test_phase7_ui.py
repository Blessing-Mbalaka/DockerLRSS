from pathlib import Path

from django.test import SimpleTestCase

TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "core"


class Phase7TemplateTests(SimpleTestCase):
    def read(self, rel):
        return (TEMPLATES / rel).read_text(encoding="utf-8")

    def test_remove_red_text_is_red(self):
        html = self.read("assessor-developer/randomized_snapshot.html")
        idx = html.index("Remove Red Text")
        self.assertIn("btn-outline-danger", html[idx - 200 : idx])

    def test_return_buttons_use_reject_style(self):
        for rel in ("qdd/_assessment_table.html", "moderator/moderator_developer.html"):
            html = self.read(rel)
            idx = html.index("Return\n")
            chunk = html[idx - 300 : idx]
            self.assertIn("btn-danger", chunk, rel)
            self.assertIn("fa-times", chunk, rel)

    def test_assessment_center_list_has_no_word_download(self):
        html = self.read("assessment-center/assessment_center.html")
        self.assertNotIn("format=docx", html)

    def test_archive_nav_commented_out(self):
        for name in ("assessor_dashboard", "assessor_developer", "assessor_reports", "view_assessment"):
            html = self.read(f"assessor-developer/{name}.html")
            pre = html.split("url 'assessment_archive'")[0]
            self.assertGreater(pre.rfind("{% comment %}"), pre.rfind("{% endcomment %}"), name)
