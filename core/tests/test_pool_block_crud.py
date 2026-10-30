import json
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Assessment, ExtractorPaper, ExtractorUserBox, Qualification


class _EditButtonParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.edit_buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "edit-box" in attrs.get("class", "").split():
            self.edit_buttons.append(attrs)


class _AdminPoolControlsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pool_modal = None
        self.has_editor_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "assessorPoolModal":
            self.pool_modal = attrs
        if tag == "form" and attrs.get("data-role") == "pool-block-form":
            self.has_editor_form = True


class PoolBlockCrudTests(TestCase):
    def setUp(self):
        # post_migrate already seeds this qualification from the registry.
        self.qualification, _ = Qualification.objects.get_or_create(
            name="Maintenance Planner", defaults={"saqa_id": "101874"}
        )
        self.other_qualification = Qualification.objects.create(
            name="Other Qualification", saqa_id="QP999"
        )
        self.user = get_user_model().objects.create_user(
            email="assessor@example.com",
            username="assessor",
            password="testpass123",
            role="assessor_dev",
            qualification=self.qualification,
        )
        self.paper = ExtractorPaper.objects.create(
            title="Maintenance Planner A",
            module_name=self.qualification.name,
            paper_letter="A",
        )
        Assessment.objects.create(
            eisa_id="EISA-POOL-1",
            qualification=self.qualification,
            paper="A",
            module_name=self.qualification.name,
            module_number="A",
            extractor_paper=self.paper,
            created_by=self.user,
        )
        self.box = ExtractorUserBox.objects.create(
            paper=self.paper,
            x=10,
            y=20,
            w=100,
            h=40,
            order_index=1,
            question_number="1.1",
            marks="5",
            qtype="question",
            content_type="text",
            content=json.dumps({"items": [{"type": "text", "text": "Original"}]}),
        )
        self.client.force_login(self.user)

    def test_admin_dashboard_exposes_pool_crud_controls(self):
        admin = get_user_model().objects.create_user(
            email="pool-admin@example.com",
            username="pool-admin",
            password="testpass123",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        parser = _AdminPoolControlsParser()
        parser.feed(response.content.decode())
        self.assertIsNotNone(parser.pool_modal)
        self.assertEqual(
            parser.pool_modal["data-create-url"],
            reverse("assessor_pool_block_create"),
        )
        self.assertEqual(
            parser.pool_modal["data-update-url-template"],
            reverse("assessor_pool_block_update", args=[0]),
        )
        self.assertEqual(
            parser.pool_modal["data-delete-url-template"],
            reverse("assessor_pool_block_delete", args=[0]),
        )
        self.assertTrue(parser.has_editor_form)

    def test_admin_can_delete_an_accidentally_captured_pool_block(self):
        admin = get_user_model().objects.create_user(
            email="delete-admin@example.com",
            username="delete-admin",
            password="testpass123",
            role="admin",
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("assessor_pool_block_delete", args=[self.box.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertFalse(ExtractorUserBox.objects.filter(id=self.box.id).exists())

    def test_create_pool_block_attaches_it_to_selected_source_paper(self):
        response = self.client.post(
            reverse("assessor_pool_block_create"),
            {
                "paper_id": self.paper.id,
                "question_number": "1.2",
                "parent_number": "1",
                "qtype": "question_part",
                "marks": "8",
                "content_text": "Created in the pool modal",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        created = ExtractorUserBox.objects.get(id=payload["entry"]["id"])
        self.assertEqual(created.paper, self.paper)
        self.assertEqual(created.question_number, "1.2")
        self.assertEqual(created.marks, "8")
        self.assertEqual(json.loads(created.content)["items"][0]["text"], "Created in the pool modal")

    def test_update_pool_block_changes_marks_and_content(self):
        response = self.client.post(
            reverse("assessor_pool_block_update", args=[self.box.id]),
            {
                "question_number": "1.1",
                "parent_number": "1",
                "qtype": "question",
                "marks": "12",
                "content_text": "Updated in the pool modal",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.box.refresh_from_db()
        self.assertEqual(self.box.marks, "12")
        self.assertEqual(json.loads(self.box.content)["items"][0]["text"], "Updated in the pool modal")

    def test_delete_pool_block_removes_it(self):
        response = self.client.post(
            reverse("assessor_pool_block_delete", args=[self.box.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ExtractorUserBox.objects.filter(id=self.box.id).exists())

    def test_pool_data_marks_structured_content_as_read_only(self):
        self.box.content_type = "mixed"
        self.box.content = json.dumps(
            {
                "items": [
                    {"type": "text", "text": "Question text"},
                    {"type": "table", "html": "<table><tr><td>A</td></tr></table>"},
                ]
            }
        )
        self.box.save(update_fields=["content_type", "content"])

        response = self.client.get(reverse("assessor_pool_data"))

        self.assertEqual(response.status_code, 200)
        entry = response.json()["modules"][0]["letters"][0]["entries"][0]
        self.assertFalse(entry["content_editable"])
        self.assertEqual(entry["content_text"], "")

    def test_pool_data_keeps_empty_source_paper_available_for_create(self):
        self.box.delete()

        response = self.client.get(reverse("assessor_pool_data"))

        self.assertEqual(response.status_code, 200)
        letter = response.json()["modules"][0]["letters"][0]
        self.assertEqual(letter["count"], 0)
        self.assertEqual(letter["entries"], [])
        self.assertEqual(
            letter["source_papers"],
            [
                {
                    "id": self.paper.id,
                    "title": self.paper.title,
                    "qualification_name": self.qualification.name,
                }
            ],
        )

    def test_pool_data_identifies_entry_qualification(self):
        response = self.client.get(reverse("assessor_pool_data"))

        self.assertEqual(response.status_code, 200)
        entry = response.json()["modules"][0]["letters"][0]["entries"][0]
        self.assertEqual(entry["qualification_name"], self.qualification.name)

    def test_matching_legacy_pool_without_assessment_link_can_be_managed(self):
        legacy_paper = ExtractorPaper.objects.create(
            title="Legacy Maintenance Planner A",
            module_name=self.qualification.name,
            paper_letter="A",
        )

        response = self.client.post(
            reverse("assessor_pool_block_create"),
            {
                "paper_id": legacy_paper.id,
                "question_number": "4",
                "marks": "6",
                "content_text": "Legacy pool block",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            ExtractorUserBox.objects.filter(paper=legacy_paper, question_number="4").exists()
        )

    def test_linked_qualification_overrides_a_misleading_module_name(self):
        mismatched_paper = ExtractorPaper.objects.create(
            title="Mismatched paper",
            module_name=self.qualification.name,
            paper_letter="B",
        )
        Assessment.objects.create(
            eisa_id="EISA-MISMATCH",
            qualification=self.other_qualification,
            paper="B",
            module_name=self.qualification.name,
            module_number="B",
            extractor_paper=mismatched_paper,
        )
        mismatched_box = ExtractorUserBox.objects.create(
            paper=mismatched_paper,
            x=0,
            y=0,
            w=1,
            h=1,
            order_index=1,
            question_number="7",
            marks="2",
            qtype="question",
        )

        pool_response = self.client.get(reverse("assessor_pool_data"))
        update_response = self.client.post(
            reverse("assessor_pool_block_update", args=[mismatched_box.id]),
            {"question_number": "7", "marks": "99"},
        )

        visible_ids = {
            entry["id"]
            for module in pool_response.json()["modules"]
            for letter in module["letters"]
            for entry in letter["entries"]
        }
        visible_paper_ids = {
            paper["id"]
            for module in pool_response.json()["modules"]
            for letter in module["letters"]
            for paper in letter["source_papers"]
        }
        self.assertNotIn(mismatched_box.id, visible_ids)
        self.assertNotIn(mismatched_paper.id, visible_paper_ids)
        self.assertEqual(update_response.status_code, 403)

    def test_non_privileged_user_without_qualification_cannot_read_pools(self):
        no_qualification_user = get_user_model().objects.create_user(
            email="unassigned@example.com",
            username="unassigned",
            password="testpass123",
            role="assessor_dev",
        )
        self.client.force_login(no_qualification_user)

        response = self.client.get(reverse("assessor_pool_data"))

        self.assertEqual(response.status_code, 403)

    def test_linked_paper_without_qualification_does_not_use_legacy_fallback(self):
        linked_unassigned_paper = ExtractorPaper.objects.create(
            title="Linked but unassigned",
            module_name=self.qualification.name,
            paper_letter="C",
        )
        Assessment.objects.create(
            eisa_id="EISA-UNASSIGNED",
            qualification=None,
            paper="C",
            module_name=self.qualification.name,
            module_number="C",
            extractor_paper=linked_unassigned_paper,
        )
        linked_box = ExtractorUserBox.objects.create(
            paper=linked_unassigned_paper,
            x=0,
            y=0,
            w=1,
            h=1,
            order_index=1,
            question_number="8",
            marks="2",
            qtype="question",
        )

        response = self.client.post(
            reverse("assessor_pool_block_update", args=[linked_box.id]),
            {"question_number": "8", "marks": "100", "qtype": "question"},
        )

        self.assertEqual(response.status_code, 403)
        linked_box.refresh_from_db()
        self.assertEqual(linked_box.marks, "2")

    def test_moderator_cannot_read_or_update_authoring_pools(self):
        moderator = get_user_model().objects.create_user(
            email="moderator@example.com",
            username="moderator",
            password="testpass123",
            role="moderator",
        )
        self.client.force_login(moderator)

        pool_response = self.client.get(reverse("assessor_pool_data"))
        update_response = self.client.post(
            reverse("assessor_pool_block_update", args=[self.box.id]),
            {"question_number": "1.1", "marks": "11", "qtype": "question"},
        )

        self.assertEqual(pool_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)
        self.box.refresh_from_db()
        self.assertNotEqual(self.box.marks, "11")

    def test_assessor_cannot_mutate_another_qualifications_pool(self):
        other_paper = ExtractorPaper.objects.create(
            title="Other A",
            module_name=self.other_qualification.name,
            paper_letter="A",
        )
        Assessment.objects.create(
            eisa_id="EISA-POOL-2",
            qualification=self.other_qualification,
            paper="A",
            module_name=self.other_qualification.name,
            module_number="A",
            extractor_paper=other_paper,
        )
        other_box = ExtractorUserBox.objects.create(
            paper=other_paper,
            x=0,
            y=0,
            w=1,
            h=1,
            order_index=1,
            question_number="2",
            marks="3",
            qtype="question",
        )

        create_response = self.client.post(
            reverse("assessor_pool_block_create"),
            {"paper_id": other_paper.id, "question_number": "3", "marks": "4"},
        )
        update_response = self.client.post(
            reverse("assessor_pool_block_update", args=[other_box.id]),
            {"question_number": "2", "marks": "99"},
        )
        delete_response = self.client.post(
            reverse("assessor_pool_block_delete", args=[other_box.id])
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        other_box.refresh_from_db()
        self.assertEqual(other_box.marks, "3")


class ExtractorPaperBoxEditingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="admin@example.com",
            username="admin",
            password="testpass123",
            role="admin",
            is_staff=True,
        )
        self.paper = ExtractorPaper.objects.create(title="Editable paper")
        self.box = ExtractorUserBox.objects.create(
            paper=self.paper,
            x=0,
            y=0,
            w=10,
            h=10,
            order_index=1,
            question_number="1",
            marks="5",
            qtype="question",
        )
        self.client.force_login(self.user)

    def test_saved_box_renders_an_actionable_edit_button(self):
        response = self.client.get(reverse("exam_paper", args=[self.paper.id]))

        self.assertEqual(response.status_code, 200)
        parser = _EditButtonParser()
        parser.feed(response.content.decode())
        self.assertEqual(len(parser.edit_buttons), 1)
        self.assertEqual(parser.edit_buttons[0].get("type"), "button")

    def test_existing_update_endpoint_saves_edited_marks(self):
        response = self.client.post(
            reverse("exam_update_box", args=[self.paper.id, self.box.id]),
            {
                "x": "0",
                "y": "0",
                "w": "10",
                "h": "10",
                "question_number": "1",
                "marks": "15",
                "qtype": "question",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.box.refresh_from_db()
        self.assertEqual(self.box.marks, "15")

    def test_marks_only_update_preserves_structured_content(self):
        original_content = json.dumps(
            {
                "items": [
                    {"type": "text", "text": "Question"},
                    {"type": "table", "html": "<table><tr><td>A</td></tr></table>"},
                    {"type": "image", "images": ["/media/example.png"]},
                ]
            }
        )
        self.box.content_type = "mixed"
        self.box.content = original_content
        self.box.save(update_fields=["content_type", "content"])

        response = self.client.post(
            reverse("exam_update_box", args=[self.paper.id, self.box.id]),
            {
                "x": "0",
                "y": "0",
                "w": "10",
                "h": "10",
                "question_number": "1",
                "marks": "20",
                "qtype": "question",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.box.refresh_from_db()
        self.assertEqual(self.box.marks, "20")
        self.assertEqual(self.box.content_type, "mixed")
        self.assertEqual(self.box.content, original_content)
