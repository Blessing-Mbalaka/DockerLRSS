from types import SimpleNamespace

from django.test import TestCase
from django.template.loader import render_to_string

from core.models import Assessment, CustomUser, Paper, Qualification
from core.templatetags.exam_extras import render_student_block


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