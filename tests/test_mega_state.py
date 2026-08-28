import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "scripts" / "mega_state.py"


def run_state(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STATE), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class MegaStateTests(unittest.TestCase):
    def test_records_and_summarizes_ordered_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            state_file = cwd / ".mega" / "state.jsonl"
            result = run_state(
                cwd,
                "record",
                "--file",
                str(state_file),
                "--plan",
                "PLAN.md",
                "--phase",
                "1",
                "--subphase",
                "1.1",
                "--kind",
                "test",
                "--status",
                "done",
                "--summary",
                "targeted tests passed",
                "--damage-radius",
                "large",
                "--branch",
                "feat/example",
                "--event-id",
                "evt-1",
                "--timestamp",
                "2026-08-28T00:00:00+00:00",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            validate = run_state(cwd, "validate", "--file", str(state_file))
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            summary = run_state(cwd, "summary", "--file", str(state_file))
            self.assertEqual(summary.returncode, 0, summary.stdout + summary.stderr)
            self.assertIn("targeted tests passed", summary.stdout)

    def test_duplicate_event_id_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            state_file = cwd / "state.jsonl"
            line = (
                '{"branch":"","cwd":"/tmp","damage_radius":"","event_id":"evt-1",'
                '"kind":"test","metadata":{},"phase":"1","plan":"PLAN.md",'
                '"related_event_ids":[],"status":"done","subphase":"1.1",'
                '"summary":"ok","timestamp":"2026-08-28T00:00:00+00:00"}\n'
            )
            state_file.write_text(line + line, encoding="utf-8")
            result = run_state(cwd, "validate", "--file", str(state_file))
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate event_id", result.stdout)

    def test_nonmonotonic_state_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            state_file = cwd / "state.jsonl"
            state_file.write_text(
                "\n".join(
                    [
                        '{"branch":"","cwd":"/tmp","damage_radius":"","event_id":"evt-2","kind":"test","metadata":{},"phase":"1","plan":"PLAN.md","related_event_ids":[],"status":"done","subphase":"1.1","summary":"later","timestamp":"2026-08-28T00:00:02+00:00"}',
                        '{"branch":"","cwd":"/tmp","damage_radius":"","event_id":"evt-1","kind":"test","metadata":{},"phase":"1","plan":"PLAN.md","related_event_ids":[],"status":"done","subphase":"1.1","summary":"earlier","timestamp":"2026-08-28T00:00:01+00:00"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = run_state(cwd, "validate", "--file", str(state_file))
            self.assertEqual(result.returncode, 1)
            self.assertIn("event order moved backwards", result.stdout)

    def test_missing_related_event_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            state_file = cwd / "state.jsonl"
            state_file.write_text(
                '{"branch":"","cwd":"/tmp","damage_radius":"","event_id":"evt-1","kind":"test","metadata":{},"phase":"1","plan":"PLAN.md","related_event_ids":["evt-missing"],"status":"done","subphase":"1.1","summary":"ok","timestamp":"2026-08-28T00:00:00+00:00"}\n',
                encoding="utf-8",
            )
            result = run_state(cwd, "validate", "--file", str(state_file))
            self.assertEqual(result.returncode, 1)
            self.assertIn("related_event_id not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
