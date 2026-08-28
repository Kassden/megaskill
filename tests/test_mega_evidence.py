import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "scripts" / "mega_evidence.py"


class MegaEvidenceTests(unittest.TestCase):
    def test_records_state_event_id_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            evidence = cwd / "evidence.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(EVIDENCE),
                    "record",
                    "--file",
                    str(evidence),
                    "--phase",
                    "1.1",
                    "--command",
                    "python -m pytest",
                    "--exit-code",
                    "0",
                    "--state-event-id",
                    "evt-1",
                ],
                cwd=cwd,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(record["state_event_id"], "evt-1")

    def test_old_evidence_records_still_summarize(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            evidence = cwd / "evidence.jsonl"
            evidence.write_text(
                '{"command":"python -m pytest","cwd":"/tmp","exit_code":0,"note":"","phase":"1.1","timestamp":"2026-08-28T00:00:00+00:00"}\n',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(EVIDENCE), "summary", "--file", str(evidence)],
                cwd=cwd,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("python -m pytest", result.stdout)


if __name__ == "__main__":
    unittest.main()
