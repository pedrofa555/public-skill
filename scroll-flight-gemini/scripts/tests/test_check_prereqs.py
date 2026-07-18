import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from check_prereqs import collect_prerequisites


class CheckPrerequisitesTests(unittest.TestCase):
    def test_reports_api_key_presence_without_value(self):
        secret = "do-not-print-this-value"
        report = collect_prerequisites({"GEMINI_API_KEY": secret})
        self.assertTrue(report["optionalApiKeyPresent"])
        self.assertNotIn(secret, repr(report))

    def test_api_is_optional_and_app_access_is_manual(self):
        report = collect_prerequisites({})
        self.assertFalse(report["optionalApiKeyPresent"])
        self.assertEqual(report["geminiAppAccess"], "confirm-manually")


if __name__ == "__main__":
    unittest.main()
