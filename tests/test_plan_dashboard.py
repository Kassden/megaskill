import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "scripts" / "mega_plan_dashboard.py"


def valid_plan() -> str:
    from test_plan_check import valid_plan as base_valid_plan

    return base_valid_plan().replace("# Valid UI Plan", "# Dashboard Plan")


def load_dashboard_module():
    spec = importlib.util.spec_from_file_location("mega_plan_dashboard", DASHBOARD)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PlanDashboardTests(unittest.TestCase):
    def test_generates_dashboard_from_plan_state_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            plan = cwd / "PLAN.md"
            state = cwd / "state.jsonl"
            evidence = cwd / "evidence.jsonl"
            output = cwd / "dashboard.html"
            plan.write_text(valid_plan(), encoding="utf-8")
            state.write_text(
                '{"branch":"feat/example","cwd":"/tmp","damage_radius":"moderate","event_id":"evt-1","kind":"test","metadata":{},"phase":"Phase 1","plan":"PLAN.md","related_event_ids":[],"status":"done","subphase":"Subphase 1.1","summary":"browser smoke passed","timestamp":"2026-08-28T00:00:00+00:00"}\n',
                encoding="utf-8",
            )
            evidence.write_text(
                '{"command":"npx playwright test","cwd":"/tmp","exit_code":0,"note":"browser proof","phase":"1.1","state_event_id":"evt-1","timestamp":"2026-08-28T00:00:01+00:00"}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(DASHBOARD),
                    str(plan),
                    "--state",
                    str(state),
                    "--evidence",
                    str(evidence),
                    "--output",
                    str(output),
                    "--no-open",
                    "--generated-at",
                    "2026-08-28T00:00:02+00:00",
                ],
                cwd=cwd,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("Dashboard Plan", html)
            self.assertIn("Current Source Of Truth", html)
            self.assertIn("Regression Radius", html)
            self.assertIn("Deterministic Real-User Test", html)
            self.assertIn("Fulfillment And Readback", html)
            self.assertIn("Armageddon Mode", html)
            self.assertIn("Generality Guardrail", html)
            self.assertIn("browser smoke passed", html)
            self.assertIn("npx playwright test", html)
            self.assertIn("evt-1", html)

    def test_no_open_suppresses_browser_launch(self):
        module = load_dashboard_module()
        args = type("Args", (), {"no_open": True, "open": False, "interactive": True})()
        self.assertFalse(module.should_open(args))

    def test_open_targets_generated_file_uri(self):
        module = load_dashboard_module()
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            plan = cwd / "PLAN.md"
            output = cwd / "dashboard.html"
            plan.write_text(valid_plan(), encoding="utf-8")
            args = type(
                "Args",
                (),
                {
                    "plan": str(plan),
                    "state": str(cwd / "missing-state.jsonl"),
                    "evidence": str(cwd / "missing-evidence.jsonl"),
                    "output": str(output),
                    "generated_at": "2026-08-28T00:00:00+00:00",
                    "no_open": False,
                    "open": True,
                    "interactive": False,
                },
            )()
            with mock.patch.object(module.webbrowser, "open") as opened:
                written = module.write_dashboard(args)
                if module.should_open(args):
                    module.webbrowser.open(written.resolve().as_uri())
            opened.assert_called_once_with(output.resolve().as_uri())


if __name__ == "__main__":
    unittest.main()
