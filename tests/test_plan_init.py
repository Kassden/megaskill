import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_INIT = ROOT / "scripts" / "mega_plan_init.py"
PLAN_CHECK = ROOT / "scripts" / "mega_plan_check.py"


class PlanInitTests(unittest.TestCase):
    def test_plan_init_can_create_dashboard_without_opening(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            plan = cwd / "generated.md"
            dashboard = cwd / "generated.html"
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLAN_INIT),
                    "Generated Dashboard Plan",
                    "--goal",
                    "Ship generated dashboard with readback proof",
                    "--output",
                    str(plan),
                    "--dashboard",
                    str(dashboard),
                    "--no-open",
                ],
                cwd=cwd,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(plan.exists())
            self.assertTrue(dashboard.exists())
            check = subprocess.run(
                [sys.executable, str(PLAN_CHECK), str(plan)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn("Generated Dashboard Plan", dashboard.read_text(encoding="utf-8"))

    def test_dashboard_requires_output_plan_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(PLAN_INIT),
                    "Generated Dashboard Plan",
                    "--goal",
                    "Ship generated dashboard with readback proof",
                    "--dashboard",
                    "--no-open",
                ],
                cwd=Path(tmp),
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--dashboard requires --output", result.stdout)


if __name__ == "__main__":
    unittest.main()
