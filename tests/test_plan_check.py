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

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: deterministic browser smoke with screenshots for UI proof.
- Official docs, standards, specs, or platform guidance: Playwright and framework docs.
- Mature libraries, frameworks, or built-in mechanisms: Playwright test runner.
- Best-practice constraints to integrate: stable fixtures and user-observable assertions.
- Rejected approaches: manual screenshots without assertions.
- Implementation decision: use Playwright browser smoke.

## Dependency and Tooling Preflight
- Required verification tools: Playwright browser smoke and screenshots.
- Existing tooling found: none yet.
- Install or repair commands: npm install and npx playwright install chromium.
- Browser/runtime binaries: Chromium.
- Real blockers that would prevent setup: approval, credential, external outage, incompatible platform.

## Deterministic Real-User Test
- Entry point: `/dashboard`.
- User workflow: load dashboard and open the primary panel.
- Stable inputs or fixtures: recorded fixture data.
- User-observable assertions: panel title and status are visible.
- Command: npx playwright test.
- Evidence to record: Playwright output and screenshot.

## Fulfillment and Readback Proof
- Requested final user-visible result: dashboard route renders changed UI.
- Required write/mutation operation: update route code.
- Readback surface: browser screenshot and DOM assertion.
- Expected content, rows, fields, counts, or behavior: visible panel status assertion.
- Command or tool call evidence: npx playwright test.
- Not-done conditions: route-only proof without visible assertion.

## Armageddon Mode
- Damage-scaled attack scope: moderate UI attack scope.
- Edge cases to try: narrow viewport, long text, empty fixture, failed network.
- Failure modes to simulate: disabled controls and network error.
- Optimization opportunities to inspect: repeated requests and layout churn.
- Must-fix threshold: broken primary workflow, console error, or overlapping text.
- Evidence to record: screenshots, console logs, and test output.

## Generality Guardrail
- Existing mechanism to reuse: existing dashboard test helpers.
- Similar existing use cases: other dashboard route smoke tests.
- Recurrence likelihood: high for future UI workflows.
- General mechanism to create if none exists: shared Playwright smoke helper.
- Specific use case implementation through the mechanism: dashboard route uses shared helper.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface:
  - `src/page.tsx`
- Protected behaviors: routing.
- Likely consumers: web users.
- Damage radius: Moderate.
- Branch strategy: Current branch is acceptable for this moderate route change after checking status.
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

    def test_missing_sota_standards_section_fails(self):
        module = load_module()
        text = valid_plan().replace(
            "## SOTA, Standards, And Best Practices\n"
            "- Current SOTA / prior art: deterministic browser smoke with screenshots for UI proof.\n"
            "- Official docs, standards, specs, or platform guidance: Playwright and framework docs.\n"
            "- Mature libraries, frameworks, or built-in mechanisms: Playwright test runner.\n"
            "- Best-practice constraints to integrate: stable fixtures and user-observable assertions.\n"
            "- Rejected approaches: manual screenshots without assertions.\n"
            "- Implementation decision: use Playwright browser smoke.\n\n",
            "",
        )
        errors = module.validate(text)
        self.assertIn("missing required section: ## SOTA, Standards, And Best Practices", errors)

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

    def test_missing_deterministic_user_test_fails(self):
        module = load_module()
        text = valid_plan().replace(
            "## Deterministic Real-User Test\n"
            "- Entry point: `/dashboard`.\n"
            "- User workflow: load dashboard and open the primary panel.\n"
            "- Stable inputs or fixtures: recorded fixture data.\n"
            "- User-observable assertions: panel title and status are visible.\n"
            "- Command: npx playwright test.\n"
            "- Evidence to record: Playwright output and screenshot.\n\n",
            "",
        )
        errors = module.validate(text)
        self.assertIn("missing required section: ## Deterministic Real-User Test", errors)

    def test_creation_without_write_and_readback_fails(self):
        module = load_module()
        text = valid_plan().replace(
            "- Requested final user-visible result: dashboard route renders changed UI.\n"
            "- Required write/mutation operation: update route code.\n"
            "- Readback surface: browser screenshot and DOM assertion.\n"
            "- Expected content, rows, fields, counts, or behavior: visible panel status assertion.\n"
            "- Command or tool call evidence: npx playwright test.\n"
            "- Not-done conditions: route-only proof without visible assertion.",
            "- Requested final user-visible result: created a new sheet.\n"
            "- Required write/mutation operation: create the sheet from template.\n"
            "- Readback surface: Drive export.\n"
            "- Expected content, rows, fields, counts, or behavior: exported CSV opens.\n"
            "- Command or tool call evidence: googleDriveWorkflow.\n"
            "- Not-done conditions: missing sheet link.",
        )
        errors = module.validate(text)
        self.assertTrue(any("creation/copy/routing" in error for error in errors))

    def test_happy_path_only_fails(self):
        module = load_module()
        text = valid_plan() + "\n- Verification is happy path only.\n"
        errors = module.validate(text)
        self.assertTrue(any("weak verification language" in error for error in errors))

    def test_missing_branch_strategy_fails(self):
        module = load_module()
        text = valid_plan().replace("- Branch strategy: Current branch is acceptable for this moderate route change after checking status.\n", "")
        errors = module.validate(text)
        self.assertIn("## Regression Guardrails must include Branch strategy", errors)

    def test_large_regression_risk_requires_dedicated_branch(self):
        module = load_module()
        text = valid_plan().replace("- Damage radius: Moderate.", "- Damage radius: Large.")
        text = text.replace(
            "- Branch strategy: Current branch is acceptable for this moderate route change after checking status.",
            "- Branch strategy: current branch because it is convenient.",
        )
        errors = module.validate(text)
        self.assertTrue(any("large/systemic regression risk" in error for error in errors))

    def test_large_regression_risk_accepts_named_branch(self):
        module = load_module()
        text = valid_plan().replace("- Damage radius: Moderate.", "- Damage radius: Large.")
        text = text.replace(
            "- Branch strategy: Current branch is acceptable for this moderate route change after checking status.",
            "- Branch strategy: Create dedicated branch `mega/high-risk-ui-change` before editing.",
        )
        errors = module.validate(text)
        self.assertEqual([], errors)

    def test_incident_remediation_without_root_cause_gate_fails(self):
        module = load_module()
        fixture = ROOT / "tests" / "fixtures" / "root-cause-gate-missing-bad.md"
        errors = module.validate(fixture.read_text(encoding="utf-8"))
        self.assertTrue(any("Root-Cause Baseline" in error for error in errors))

    def test_incident_remediation_with_root_cause_gate_passes(self):
        module = load_module()
        fixture = ROOT / "tests" / "fixtures" / "root-cause-gate-good.md"
        errors = module.validate(fixture.read_text(encoding="utf-8"))
        self.assertEqual([], errors)

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
