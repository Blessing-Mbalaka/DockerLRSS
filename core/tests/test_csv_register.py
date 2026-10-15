from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import CustomUser, OfflineStudent, Qualification


class CsvRegisterUploadTests(TestCase):
    def setUp(self):
        self.qual = Qualification.objects.create(name="Q1")
        self.user = CustomUser.objects.create_user(
            username="a@x.com", email="a@x.com", password="pw-12345", role="admin"
        )
        self.client.force_login(self.user)

    def _upload(self, text):
        f = SimpleUploadedFile("r.csv", text.encode(), content_type="text/csv")
        resp = self.client.post(reverse("upload_student_register"), {"register_file": f})
        return [str(m) for m in get_messages(resp.wsgi_request)]

    def test_blank_rows_do_not_error(self):
        msgs = self._upload(
            "student_number,first_name,last_name,email,qualification,status\n"
            "S1,A,B,a@b.com,Q1,present\n"
            ",,,,,\n"
            "\n"
            ",,,,,\n"
        )
        self.assertEqual(OfflineStudent.objects.count(), 1)
        self.assertFalse(any("error" in m.lower() for m in msgs), msgs)

    def test_partial_row_reports_one_error_and_is_not_saved(self):
        msgs = self._upload(
            "student_number,first_name,last_name,email,qualification,status\n"
            "S2,,B,a@b.com,Q1,present\n"
        )
        self.assertEqual(OfflineStudent.objects.count(), 0)
        self.assertTrue(any("first_name" in m for m in msgs), msgs)
