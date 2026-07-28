import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMIT_CHECK = ROOT / "scripts" / "mega_commit_check.py"
SCOPE_CHECK = ROOT / "scripts" / "mega_scope_check.py"
PLAN = ROOT / "tests" / "fixtures" / "valid-ui-plan.md"


def run_script(script: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class GitHelperTests(unittest.TestCase):
    def test_commit_check_reports_non_git_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(COMMIT_CHECK, Path(tmp))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not inside a git repository", result.stdout)
        self.assertIn("Fallback evidence", result.stdout)

    def test_scope_check_reports_non_git_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(SCOPE_CHECK, Path(tmp), str(PLAN))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not inside a git repository", result.stdout)
        self.assertIn("planned files", result.stdout)
        self.assertIn("Fallback evidence", result.stdout)

    def test_git_helpers_preserve_git_repo_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            subprocess.run(["git", "init"], cwd=tmp_path, check=True, text=True, capture_output=True)
            result = run_script(COMMIT_CHECK, tmp_path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no staged files", result.stdout)


if __name__ == "__main__":
    unittest.main()
