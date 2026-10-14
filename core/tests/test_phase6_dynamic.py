from unittest import mock

from django.test import SimpleTestCase

from core import randomization_config as rc


class DynamicLettersTests(SimpleTestCase):
    def test_yaml_letters_win(self):
        self.assertEqual(rc.allowed_letters("Test Documentation", "1A"), ["A", "B"])

    def test_letters_derived_from_registry_when_not_in_yaml(self):
        modules = [{"code": "3A"}, {"code": "3B"}, {"code": "3C"}, {"code": "4A"}]
        with mock.patch(
            "core.qualification_registry.get_module_choices", return_value=modules
        ):
            self.assertEqual(rc.allowed_letters("New Qual", "3A"), ["A", "B", "C"])
            self.assertEqual(rc.randomization_status("New Qual", "3A"), "paired")
            self.assertEqual(rc.allowed_letters("New Qual", "4A"), ["A"])

    def test_unconfigured_when_nothing_known(self):
        with mock.patch("core.qualification_registry.get_module_choices", return_value=[]):
            self.assertEqual(rc.allowed_letters("Nope", "9A"), [])
            self.assertEqual(rc.randomization_status("Nope", "9A"), "unconfigured")
