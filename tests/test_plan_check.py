import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_CHECK = ROOT / "scripts" / "mega_plan_check.py"
PLAN_INIT = ROOT / "scripts" / "mega_plan_init.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mega_plan_check", PLAN_CHECK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_plan() -> str:
    return """# Valid UI Plan

## GOAL
- Ship a browser UI change with proof.

## Acceptance Criteria
- Browser route renders on desktop and mobile.

## Research
- Built-in options: use existing npm scripts.
- Off-the-shelf options: use Playwright.
- Official / standards sources: check framework docs.

## Dependency and Tooling Preflight
- Required verification tools: Playwright browser smoke and screenshots.
- Existing tooling found: none yet.
- Install or repair commands: npm install and npx playwright install chromium.
- Browser/runtime binaries: Chromium.
- Real blockers that would prevent setup: approval, credential, external outage, incompatible platform.

## Regression Guardrails
- Planned edit surface:
  - `src/page.tsx`
- Protected behaviors: routing.
- Likely consumers: web users.
- Damage radius: Moderate.
- Proof plan: Playwright browser smoke and screenshot checks.

## Phase 1: UI

### Subphase 1.1: Render Route
- Commit: render route safely.
- Tests: npx playwright test.
- Success Criteria: desktop and mobile smoke pass.
- Planned Touch Files:
  - `src/page.tsx`
- Checklist:
  - [ ] Change route.
  - [ ] Run Playwright.
"""


class PlanCheckTests(unittest.TestCase):
    def test_valid_plan_passes(self):
        module = load_module()
        self.assertEqual(module.validate(valid_plan()), [])

    def test_missing_dependency_preflight_fails(self):
        module = load_module()
        text = valid_plan().replace(
            "## Dependency and Tooling Preflight\n"
            "- Required verification tools: Playwright browser smoke and screenshots.\n"
            "- Existing tooling found: none yet.\n"
            "- Install or repair commands: npm install and npx playwright install chromium.\n"
            "- Browser/runtime binaries: Chromium.\n"
            "- Real blockers that would prevent setup: approval, credential, external outage, incompatible platform.\n\n",
            "",
        )
        errors = module.validate(text)
        self.assertIn("missing required section: ## Dependency and Tooling Preflight", errors)

    def test_ui_plan_without_browser_proof_fails(self):
        module = load_module()
        text = valid_plan().replace("Playwright browser smoke and screenshots", "unit tests")
        text = text.replace("npx playwright install chromium", "npm install")
        text = text.replace("Playwright browser smoke and screenshot checks", "unit checks")
        text = text.replace("npx playwright test", "npm test")
        text = text.replace("Run Playwright", "Run unit tests")
        errors = module.validate(text)
        self.assertTrue(any("UI/browser-facing plan" in error for error in errors))

    def test_skip_when_tooling_absent_loophole_fails(self):
        module = load_module()
        text = valid_plan() + "\n- Use Playwright only if already available; otherwise use Node probes.\n"
        errors = module.validate(text)
        self.assertTrue(any("verification loophole" in error for error in errors))

    def test_plan_init_output_passes_plan_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "plan.md"
            init_result = subprocess.run(
                [
                    sys.executable,
                    str(PLAN_INIT),
                    "Generated Plan",
                    "--goal",
                    "Ship with proof",
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(init_result.returncode, 0, init_result.stderr)
            check_result = subprocess.run(
                [sys.executable, str(PLAN_CHECK), str(output)],
                text=True,
                capture_output=True,
            )
        self.assertEqual(check_result.returncode, 0, check_result.stdout + check_result.stderr)


if __name__ == "__main__":
    unittest.main()
