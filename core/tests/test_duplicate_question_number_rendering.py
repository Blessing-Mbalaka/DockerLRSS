from types import SimpleNamespace

from django.test import TestCase
from django.template.loader import render_to_string

from core.models import Assessment, CustomUser, Paper, Qualification
from core.templatetags.exam_extras import question_heading, render_student_block, strip_question_prefix


class DuplicateQuestionNumberRenderingTests(TestCase):
    def setUp(self):
        self.qualification = Qualification.objects.create(
            name="Duplicate Qual",
            saqa_id="DQ-001",
        )
        self.user = CustomUser.objects.create_user(
            username="dup-render-user",
            email="dup-render@example.com",
            password="pass1234",
            role="admin",
        )
        self.paper = Paper.objects.create(
            name="Duplicate Number Paper",
            qualification=self.qualification,
            created_by=self.user,
            total_marks=50,
        )
        self.assessment = Assessment.objects.create(
            eisa_id="EISA-DUP-001",
            qualification=self.qualification,
            paper=self.paper.name,
            paper_link=self.paper,
            status="Released to students",
            created_by=self.user,
        )
        self.paper_context = SimpleNamespace(
            id=1,
            name=self.paper.name,
            qualification=self.qualification,
            total_marks=self.paper.total_marks,
        )
        self.assessment_context = SimpleNamespace(id=1, name="Duplicate Assessment")

    def test_write_paper_simple_template_strips_duplicate_prefix_from_question_text(self):
        questions = [
            {
                "id": "node-1",
                "number": "1.1",
                "marks": "5",
                "text": "1.1 Explain lockout procedures.",
                "content": [
                    {
                        "type": "question_text",
                        "text": "1.1 Explain lockout procedures.",
                    }
                ],
            }
        ]

        html = render_to_string(
            "core/student/write_paper_simple.html",
            {
                "paper": self.paper_context,
                "assessment": self.assessment_context,
                "questions": questions,
                "attempt_number": 1,
            },
        )

        self.assertIn("Question 1.1", html)
        self.assertIn("Explain lockout procedures.", html)
        self.assertNotIn("Question 1.1.1", html)
        self.assertNotIn(">1.1 Explain lockout procedures.<", html)

    def test_render_student_block_strips_duplicate_prefix_from_runs(self):
        block = {
            "type": "question_text",
            "text": "1.2 Styled safety question",
            "runs": [
                {"text": "1.2 "},
                {"text": "Styled safety question", "is_bold": True},
            ],
        }

        html = str(render_student_block(block, "1.2"))

        self.assertIn("Styled safety question", html)
        self.assertNotIn("1.2 Styled safety question", html)

    def test_exam_pdf_template_strips_duplicate_prefix_from_node_text(self):
        answers = [
            SimpleNamespace(
                question_number="2.3",
                node=SimpleNamespace(text="2.3 Describe PPE checks before use."),
                marks="10",
                answer="Inspect straps, seals, and expiry dates.",
            )
        ]

        html = render_to_string(
            "core/student/exam_pdf_template.html",
            {
                "paper": self.paper_context,
                "assessment": self.assessment_context,
                "student_name": "Test Student",
                "student_number": "STU-001",
                "attempt_number": 1,
                "submission_date": None,
                "answers": answers,
                "total_questions": len(answers),
            },
        )

        self.assertIn("2.3.", html)
        self.assertIn("Describe PPE checks before use.", html)
        self.assertNotIn("2.3 Describe PPE checks before use.", html)

    def test_strip_question_prefix_handles_question_label_prefixes(self):
        self.assertEqual(
            strip_question_prefix("Question 2.3 Describe PPE checks before use.", "2.3"),
            "Describe PPE checks before use.",
        )
        self.assertEqual(
            strip_question_prefix("Q 2.3 Describe PPE checks before use.", "2.3"),
            "Describe PPE checks before use.",
        )
        self.assertEqual(
            strip_question_prefix("Question No. 2.3 Describe PPE checks before use.", "2.3"),
            "Describe PPE checks before use.",
        )

    def test_strip_question_prefix_handles_wrapped_number_prefixes(self):
        self.assertEqual(
            strip_question_prefix("(2.3) Describe PPE checks before use.", "2.3"),
            "Describe PPE checks before use.",
        )
        self.assertEqual(
            strip_question_prefix("[2.3] Describe PPE checks before use.", "2.3"),
            "Describe PPE checks before use.",
        )

    def test_strip_question_prefix_handles_number_only_text(self):
        self.assertEqual(strip_question_prefix("2.3", "2.3"), "")
        self.assertEqual(strip_question_prefix("2.3 ", "2.3"), "")
        self.assertEqual(strip_question_prefix("(2.3)", "2.3"), "")

    def test_exam_pdf_template_strips_question_label_prefix_from_node_text(self):
        answers = [
            SimpleNamespace(
                question_number="2.3",
                node=SimpleNamespace(text="Question 2.3 Describe PPE checks before use."),
                marks="10",
                answer="Inspect straps, seals, and expiry dates.",
            )
        ]

        html = render_to_string(
            "core/student/exam_pdf_template.html",
            {
                "paper": self.paper_context,
                "assessment": self.assessment_context,
                "student_name": "Test Student",
                "student_number": "STU-001",
                "attempt_number": 1,
                "submission_date": None,
                "answers": answers,
                "total_questions": len(answers),
            },
        )

        self.assertIn("2.3.", html)
        self.assertIn("Describe PPE checks before use.", html)
        self.assertNotIn("Question 2.3 Describe PPE checks before use.", html)

    def test_exam_pdf_template_hides_duplicate_when_node_text_is_number_only(self):
        answers = [
            SimpleNamespace(
                question_number="1.1.2",
                node=SimpleNamespace(text="1.1.2"),
                marks="10",
                answer="Concise answer text.",
            )
        ]

        html = render_to_string(
            "core/student/exam_pdf_template.html",
            {
                "paper": self.paper_context,
                "assessment": self.assessment_context,
                "student_name": "Test Student",
                "student_number": "STU-001",
                "attempt_number": 1,
                "submission_date": None,
                "answers": answers,
                "total_questions": len(answers),
            },
        )

        self.assertIn("1.1.2.", html)
        self.assertNotIn("1.1.2. 1.1.2", html)

    def test_question_heading_falls_back_to_table_html_when_text_blank(self):
        node = SimpleNamespace(
            text="",
            content=[
                {
                    "type": "table",
                    "html": "<table><thead><tr><th>2.1.3 Analyse sample results and data collected from service delivered or manufacturing process 2.1.3 Constructive Response</th></tr></thead></table>",
                }
            ],
        )

        heading = question_heading(node, "2.1.3")

        self.assertIn(
            "Analyse sample results and data collected from service delivered or manufacturing process",
            heading,
        )
        self.assertNotEqual(heading, "Question")
        self.assertNotIn("2.1.3 Constructive Response", heading)

    def test_exam_pdf_template_uses_content_fallback_when_node_text_blank(self):
        answers = [
            SimpleNamespace(
                question_number="2.1.1",
                node=SimpleNamespace(
                    text="",
                    content=[
                        {
                            "type": "table",
                            "html": "<table><thead><tr><th>2.1.1 Identify tools and method to use in processing information during manufacturing and service rendering2.1.1 Multiple Choice Question</th></tr></thead></table>",
                        }
                    ],
                ),
                marks="5",
                answer="Student answer text.",
            )
        ]

        html = render_to_string(
            "core/student/exam_pdf_template.html",
            {
                "paper": self.paper_context,
                "assessment": self.assessment_context,
                "student_name": "Test Student",
                "student_number": "STU-001",
                "attempt_number": 1,
                "submission_date": None,
                "answers": answers,
                "total_questions": len(answers),
            },
        )

        self.assertIn("2.1.1.", html)
        self.assertIn(
            "Identify tools and method to use in processing information during manufacturing and service rendering",
            html,
        )
        self.assertNotIn("2.1.1. Question", html)
        self.assertNotIn("rendering2.1.1", html)