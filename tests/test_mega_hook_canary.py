import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/mega_hook_canary.py'


class CanaryTests(unittest.TestCase):
    def test_repeatable_unlock_retry_and_explicit_outcome_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = []
            for name in ('first', 'second'):
                workspace = Path(tmp) / name
                result = subprocess.run([sys.executable, str(SCRIPT), '--workspace', str(workspace)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout); results.append(report)
                self.assertFalse(report['tool_denials'])
                self.assertFalse(report['review_only_injections'])
                self.assertTrue(report['explicit_resume_unlock'])
                self.assertTrue(report['completion_retries'])
                self.assertEqual((workspace / '1.2.txt').read_text(), 'verified 1.2')
            self.assertEqual(results[0], results[1])

    def test_retired_enforcement_cannot_be_reenabled_by_canary(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--execute'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('native runtime automation is separate', result.stderr)

    def test_refuses_nonempty_workspace_and_bad_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp); (path / 'user-data').write_text('keep')
            result = subprocess.run([sys.executable, str(SCRIPT), '--workspace', tmp], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((path / 'user-data').read_text(), 'keep')
            result = subprocess.run([sys.executable, str(SCRIPT), '--timeout', '0'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
