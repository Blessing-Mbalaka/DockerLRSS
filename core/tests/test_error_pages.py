from django.test import TestCase, override_settings


class BrandedErrorTests(TestCase):
    @override_settings(DEBUG=True)
    def test_404_branded_in_debug(self):
        resp = self.client.get("/definitely-not-a-page/")
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "Page Not Found", status_code=404)
        self.assertNotContains(resp, "Django tried these URL patterns", status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_404_branded_without_debug(self):
        resp = self.client.get("/definitely-not-a-page/")
        self.assertContains(resp, "Page Not Found", status_code=404)

    @override_settings(DEBUG=True, BRANDED_ERRORS=False)
    def test_can_disable_branding(self):
        resp = self.client.get("/definitely-not-a-page/")
        self.assertContains(resp, "Django tried these URL patterns", status_code=404)
