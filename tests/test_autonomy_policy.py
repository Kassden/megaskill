import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_CHECK = ROOT / "scripts" / "mega_plan_check.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("mega_plan_check", PLAN_CHECK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AutonomyPolicyTests(unittest.TestCase):
    def test_good_playwright_install_fixture_passes(self):
        module = load_module()
        text = (FIXTURES / "peptomart-playwright-install-good.md").read_text(encoding="utf-8")
        self.assertEqual(module.validate(text), [])

    def test_dashboard_playwright_loophole_fixture_fails(self):
        module = load_module()
        text = (FIXTURES / "dashboard-playwright-loophole-bad.md").read_text(encoding="utf-8")
        errors = module.validate(text)
        self.assertTrue(any("verification loophole" in error for error in errors))

    def test_non_git_artifact_fixture_documents_fallback(self):
        text = (FIXTURES / "nongit-artifact-evidence.md").read_text(encoding="utf-8")
        self.assertIn("Fallback evidence", text)
        self.assertIn("record hashes or file sizes", text)

    def test_happy_path_armageddon_fixture_fails(self):
        module = load_module()
        text = (FIXTURES / "armageddon-happy-path-bad.md").read_text(encoding="utf-8")
        errors = module.validate(text)
        self.assertTrue(any("weak verification language" in error for error in errors))

    def test_missing_generality_fixture_fails(self):
        module = load_module()
        text = (FIXTURES / "generality-missing-bad.md").read_text(encoding="utf-8")
        errors = module.validate(text)
        self.assertIn("missing required section: ## Generality Guardrail", errors)


if __name__ == "__main__":
    unittest.main()
