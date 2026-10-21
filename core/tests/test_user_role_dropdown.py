from django.test import TestCase, override_settings
from django.urls import reverse
from core.tests.test_assessment_return_flow import AssessmentReturnFlowTests
from core.models import AssessmentCentre


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RoleDropdownRegressionTests(TestCase):
    setUp = AssessmentReturnFlowTests.setUp

    def test_user_rows_supply_controls_required_by_role_script(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("user_management"))
        self.assertContains(response, 'class="form-select form-select-sm role-centre mt-2"')
        self.assertContains(response, 'data-prev="assessor_dev"')

    def test_normal_role_update_persists(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("update_user_role", args=[self.assessor.pk]), {"role": "moderator"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assessor.refresh_from_db()
        self.assertEqual(self.assessor.role, "moderator")

    def test_centre_role_without_centre_preserves_previous_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("update_user_role", args=[self.assessor.pk]), {"role": "assessment_center"})
        self.assertEqual(response.status_code, 400)
        self.assessor.refresh_from_db()
        self.assertEqual(self.assessor.role, "assessor_dev")

    def test_centre_role_saves_centre_and_qualification(self):
        centre = AssessmentCentre.objects.create(name="Role Assignment Centre", qualification_assigned=self.qualification)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("update_user_role", args=[self.assessor.pk]), {"role": "assessment_center", "assessment_centre": centre.pk})
        self.assertEqual(response.status_code, 200)
        self.assessor.refresh_from_db()
        self.assertEqual(self.assessor.assessment_centre_id, centre.pk)
        self.assertEqual(self.assessor.qualification_id, self.qualification.pk)
