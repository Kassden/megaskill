import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/mega_decision.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("mega_decision", SCRIPT)
decision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decision)


class MegaDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.plan = self.cwd / "PLAN.md"
        self.plan.write_text("# Plan\n## Phase 1: Build\n### Subphase 1.1: Decisions\n"
                             "### Subphase 1.10: Other\n", encoding="utf-8")
        self.ledger = self.cwd / ".mega/decisions.jsonl"

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.cwd,
                                text=True, capture_output=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("Traceback", result.stderr)
        return result

    def record_args(self, ident="dec-one", supersedes=None, durable=True):
        args = ["record", "--task-id", "task-one", "--plan", str(self.plan),
                "--phase", "1", "--subphase", "1.1", "--kind", "ui",
                "--decision-id", ident, "--question", "Tabs or sidebar?",
                "--decision", "Tabs", "--why", "Fits the three peer views",
                "--alternative", "Sidebar: uses scarce horizontal space",
                "--assumption", "Only three views remain",
                "--self-critique", "Tabs hide other views from discovery",
                "--disconfirming-evidence", "Task failures caused by hidden views would refute this",
                "--disconfirming-test", "Try three navigation tasks at 390px",
                "--tradeoffs", "Less navigation space, weaker discoverability",
                "--reversibility", "Swap navigation component without changing routes",
                "--follow-up", "Revisit if view count exceeds five"]
        if durable:
            args.append("--durable")
        if supersedes:
            args.extend(["--supersedes", supersedes])
        return args

    def record(self, ident="dec-one", **kwargs):
        return json.loads(self.cli(*self.record_args(ident, **kwargs)).stdout)

    def status(self, status, ident="dec-one", success=True, task="task-one", plan=None):
        return self.cli("status", "--decision-id", ident, "--task-id", task,
                        "--plan", str(plan or self.plan), "--status", status,
                        "--reason", "Reviewed navigation evidence", success=success)

    def accept(self, ident="dec-one"):
        self.status("challenged", ident)
        self.status("accepted", ident)

    def promote(self, ident="dec-one", success=True, *extra):
        return self.cli("promote", "--decision-id", ident, "--task-id", "task-one",
                        "--plan", str(self.plan), *extra, success=success)

    def fixture(self, rows):
        self.ledger.parent.mkdir(exist_ok=True)
        self.ledger.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_help_and_required_arguments(self):
        for command in (None, "record", "status", "promote", "validate", "summary"):
            args = [command, "--help"] if command else ["--help"]
            self.assertIn("usage:", self.cli(*args).stdout)
        self.cli("record", success=False)
        self.cli("no-such-command", success=False)

    def test_real_cli_round_trip_and_frontmatter(self):
        row = self.record()
        self.assertEqual(row["plan"], str(self.plan.resolve()))
        before = self.ledger.read_bytes()
        self.accept()
        self.assertTrue(self.ledger.read_bytes().startswith(before))
        receipt = json.loads(self.promote().stdout)
        output = Path(receipt["adr_path"])
        text = output.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        metadata = {key: json.loads(value) for key, value in
                    (line.split(": ", 1) for line in frontmatter.strip().splitlines())}
        self.assertEqual(metadata["task_id"], "task-one")
        self.assertEqual(metadata["status"], "accepted")
        self.assertEqual(metadata["plan_sha256"], row["plan_sha256"])
        for field in decision.TEXT_FIELDS:
            self.assertIn(row[field], text)
        self.cli("validate")
        rows = json.loads(self.cli("summary", "--json").stdout)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["adr_path"], str(output))
        self.assertIn("Fits the three peer views", self.cli("summary").stdout)

    def test_idempotent_promotion_and_modified_adr_fails(self):
        self.record()
        self.accept()
        receipt = json.loads(self.promote().stdout)
        before = self.ledger.read_bytes()
        self.assertTrue(json.loads(self.promote().stdout)["already_promoted"])
        self.assertEqual(before, self.ledger.read_bytes())
        Path(receipt["adr_path"]).write_text("edited", encoding="utf-8")
        self.assertIn("changed", self.promote(success=False).stderr)
        self.assertEqual(before, self.ledger.read_bytes())

    def test_acceptance_requires_challenge_and_no_backward_transition(self):
        self.record()
        self.assertIn("invalid transition", self.status("accepted", success=False).stderr)
        self.accept()
        self.status("executed")
        self.status("validated")
        self.status("challenged", success=False)
        self.cli("validate")

    def test_rejected_is_terminal(self):
        self.record()
        self.status("rejected")
        self.status("challenged", success=False)
        self.promote(success=False)

    def test_promotion_requires_accepted_and_durable(self):
        self.record(durable=False)
        self.promote(success=False)
        self.accept()
        self.assertIn("durable", self.promote(success=False).stderr)
        self.assertFalse((self.cwd / "docs").exists())

    def test_supersession_is_atomic_and_history_retained(self):
        self.record()
        self.accept()
        original = self.ledger.read_bytes()
        self.record("dec-two", supersedes="dec-one")
        self.status("challenged", "dec-two")
        self.status("accepted", "dec-two")
        self.assertTrue(self.ledger.read_bytes().startswith(original))
        rows = {row["decision_id"]: row for row in json.loads(self.cli("summary", "--json").stdout)}
        self.assertEqual(rows["dec-one"]["status"], "superseded")
        self.assertEqual(rows["dec-one"]["superseded_by"], "dec-two")
        self.assertEqual(rows["dec-two"]["supersedes"], "dec-one")
        self.promote(success=False)
        self.promote("dec-two")
        self.cli("validate")

    def test_invalid_supersession_targets(self):
        self.cli(*self.record_args("dec-two", supersedes="missing"), success=False)
        self.record()
        self.cli(*self.record_args("dec-two", supersedes="dec-one"), success=False)
        self.accept()
        args = self.record_args("dec-two", supersedes="dec-one")
        args[args.index("--task-id") + 1] = "other-task"
        self.assertIn("crosses", self.cli(*args, success=False).stderr)
        self.status("superseded", success=False)

    def test_competing_replacements_cannot_both_be_accepted(self):
        self.record()
        self.accept()
        self.record("dec-two", supersedes="dec-one")
        self.record("dec-three", supersedes="dec-one")
        self.accept("dec-two")
        self.status("challenged", "dec-three")
        before = self.ledger.read_bytes()
        self.status("accepted", "dec-three", success=False)
        self.assertEqual(before, self.ledger.read_bytes())

    def test_task_plan_and_subphase_identity_are_exact(self):
        self.record()
        self.status("challenged", task="task-one-extra", success=False)
        other = self.cwd / "OTHER.md"
        other.write_bytes(self.plan.read_bytes())
        self.status("challenged", plan=other, success=False)
        args = self.record_args("dec-two")
        args[args.index("--subphase") + 1] = "1.100"
        self.assertIn("exact subphase", self.cli(*args, success=False).stderr)
        self.plan.unlink()
        # Historical identity survives plan deletion; history does not rewrite its digest.
        self.cli("validate")

    def test_summary_filters_do_not_use_substrings(self):
        self.record()
        self.assertEqual(json.loads(self.cli("summary", "--task-id", "task", "--json").stdout), [])
        self.assertEqual(len(json.loads(self.cli("summary", "--kind", "ui", "--status", "proposed", "--json").stdout)), 1)

    def test_generated_id_unicode_and_long_rationale(self):
        args = self.record_args()
        position = args.index("--decision-id")
        del args[position:position + 2]
        rationale = "證據 supports this choice. " * 500
        args[args.index("--why") + 1] = rationale
        row = json.loads(self.cli(*args).stdout)
        self.assertTrue(row["decision_id"].startswith("dec-"))
        self.assertEqual(row["why"], rationale)
        self.accept(row["decision_id"])
        receipt = json.loads(self.promote(row["decision_id"]).stdout)
        self.assertIn(rationale, Path(receipt["adr_path"]).read_text())
        self.cli(*self.record_args(""), success=False)

    def test_invalid_required_field_fixtures(self):
        row = self.record()
        cases = {field: " " for field in decision.TEXT_FIELDS}
        cases.update({"alternatives": [], "assumptions": [], "kind": "unknown", "durable": "true",
                      "status": "accepted", "task_id": "../escape", "decision_id": "../../bad",
                      "schema_version": True, "timestamp": "yesterday", "plan": "relative.md",
                      "plan_sha256": "bad", "subphase": "10.1", "evidence_refs": [None],
                      "state_event_ids": "evt-1", "supersedes": [], "event": "unknown"})
        for field, value in cases.items():
            with self.subTest(field=field):
                self.fixture([{**row, field: value}])
                self.cli("validate", success=False)

    def test_missing_fields_and_duplicate_ids(self):
        row = self.record()
        for field in (*decision.TEXT_FIELDS, *decision.COMMON):
            with self.subTest(field=field):
                bad = dict(row)
                del bad[field]
                self.fixture([bad])
                self.cli("validate", success=False)
        self.fixture([row, row])
        self.assertIn("duplicate event_id", self.cli("validate", success=False).stderr)
        duplicate = {**row, "event_id": "devt-other"}
        self.fixture([row, duplicate])
        self.assertIn("duplicate decision_id", self.cli("validate", success=False).stderr)

    def test_corrupt_ledger_is_never_appended(self):
        self.ledger.parent.mkdir()
        for raw in ('{broken}\n', '[]\n', '\n', '{"event_id":"a","event_id":"b"}\n',
                    '{"schema_version":NaN}\n', '{}', '\xff'):
            with self.subTest(raw=raw):
                self.ledger.write_bytes(raw.encode("latin1"))
                before = self.ledger.read_bytes()
                self.cli("validate", success=False)
                self.cli(*self.record_args(), success=False)
                self.assertEqual(before, self.ledger.read_bytes())

    def test_empty_and_missing_ledgers(self):
        self.cli("validate", success=False)
        self.ledger.write_bytes(b"")
        self.cli("validate")
        self.assertEqual(json.loads(self.cli("summary", "--json").stdout), [])

    def test_rationale_cannot_be_changed_by_status_event(self):
        row = self.record()
        event = decision.event_for(row, "status", "challenged", "Review")
        event["why"] = "Rewritten rationale"
        self.fixture([row, event])
        self.assertIn("immutable", self.cli("validate", success=False).stderr)

    def test_backwards_timestamps_and_naive_time_fail(self):
        row = self.record()
        event = decision.event_for(row, "status", "challenged", "Review")
        for timestamp in ("2000-01-01T00:00:00+00:00", "2026-01-01T00:00:00"):
            self.fixture([row, {**event, "timestamp": timestamp}])
            self.cli("validate", success=False)

    def test_incomplete_supersession_fixture_fails(self):
        self.record()
        self.accept()
        self.record("dec-two", supersedes="dec-one")
        self.status("challenged", "dec-two")
        rows, _ = decision.read_records(self.ledger)
        event = decision.event_for(rows[-1], "status", "accepted", "Replacement approved")
        self.fixture(rows + [event])
        self.assertIn("incomplete supersession", self.cli("validate", success=False).stderr)

    def test_linked_proof_validation(self):
        state = self.cwd / "state.jsonl"
        evidence = self.cwd / "evidence.jsonl"
        state.write_text(json.dumps({"event_id": "evt-one", "task_id": "task-one", "plan": str(self.plan), "subphase": "1.1"}) + "\n")
        evidence.write_text(json.dumps({"evidence_id": "proof-one", "plan": str(self.plan), "phase": "1"}) + "\n")
        args = self.record_args() + ["--state-event-id", "evt-one", "--evidence-ref", "proof-one",
                                    "--state-file", str(state), "--evidence-file", str(evidence)]
        self.cli(*args)
        self.cli("validate", "--state-file", str(state), "--evidence-file", str(evidence))
        for proof in ({"event_id": "other"}, {"event_id": "evt-one", "task_id": "task-two"},
                      {"event_id": "evt-one", "subphase": "1.10"},
                      {"event_id": "evt-one", "plan": str(self.cwd / "OTHER.md")}):
            state.write_text(json.dumps(proof) + "\n")
            self.cli("validate", "--state-file", str(state), success=False)
        state.write_text("{broken}\n")
        self.cli("validate", "--state-file", str(state), success=False)
        self.cli("validate")  # Standalone validation remains available.

    def test_runtime_task_contract_and_proof_identity(self):
        row = self.record()
        task_file = self.cwd / ".mega/tasks/task-one.json"
        task_file.parent.mkdir()
        task = {"task_id": "task-one", "plan": row["plan"], "plan_hash": row["plan_sha256"],
                "status": "active", "mode": "execute", "obligations": [{"id": "1.1"}]}
        task_file.write_text(json.dumps(task))
        self.cli("validate", "--task-file", str(task_file))
        self.accept()
        self.promote()
        for changes in ({"task_id": "task-two"}, {"plan_hash": "0" * 64},
                        {"obligations": [{"id": "1.10"}]}, {"status": "cancelled"}, {"mode": "plan"}):
            task_file.write_text(json.dumps({**task, **changes}))
            self.status("executed", success=False)
            self.cli(*self.record_args("dec-two"), success=False)
        task_file.write_text(json.dumps(task))
        # New runtime proof events use event_id, plan_hash and obligation_id.
        proof = self.cwd / "proof.jsonl"
        event = {"event_id": "proof-event", "task_id": "task-one", "plan_hash": row["plan_sha256"], "obligation_id": "1.1"}
        proof.write_text(json.dumps(event) + "\n")
        self.cli(*self.record_args("dec-two"), "--evidence-ref", "proof-event", "--evidence-file", str(proof))
        for changes in ({"plan_hash": "0" * 64}, {"obligation_id": "1.10"}):
            proof.write_text(json.dumps({**event, **changes}) + "\n")
            self.cli("validate", "--evidence-file", str(proof), success=False)

    def test_registered_task_cli_to_promoted_adr_readback(self):
        from test_plan_check import valid_plan
        self.plan.write_text(valid_plan())
        registered = subprocess.run([sys.executable, str(SCRIPT.with_name("mega_task.py")),
                        "--root", str(self.cwd / ".mega"), "register", "--id", "task-one",
                        "--plan", str(self.plan), "--goal", "Review navigation choice"],
                        cwd=self.cwd, capture_output=True, text=True, timeout=15)
        self.assertEqual(registered.returncode, 0, registered.stdout + registered.stderr)
        contract = json.loads(registered.stdout)
        row = self.record()
        self.assertEqual(row["plan_sha256"], contract["plan_hash"])
        self.accept()
        self.promote()
        self.cli("validate", "--task-file", str(self.cwd / ".mega/tasks/task-one.json"))
        readback = json.loads(self.cli("summary", "--task-id", contract["task_id"], "--json").stdout)
        self.assertEqual(readback[0]["status"], "accepted")
        self.assertIn("## Self-critique", Path(readback[0]["adr_path"]).read_text())

    def test_subphase_must_be_under_its_phase_and_unique(self):
        for text in ("## Phase 1: First\n## Phase 2: Second\n### Subphase 1.1: Wrong\n",
                     "## Phase 1: First\n### Subphase 1.1: One\n### Subphase 1.1: Duplicate\n"):
            self.plan.write_text(text)
            self.cli(*self.record_args(), success=False)

    def test_output_collision_and_path_traversal(self):
        args = self.record_args("../bad")
        self.cli(*args, success=False)
        self.record()
        self.accept()
        output = self.cwd / "existing.md"
        output.write_text("User-owned document")
        self.promote("dec-one", False, "--output", str(output))
        self.assertEqual(output.read_text(), "User-owned document")
        self.promote("dec-one", False, "--output", str(self.ledger))

    def test_atomic_write_failure_preserves_original_and_cleans_temp(self):
        target = self.cwd / "result.md"
        target.write_bytes(b"original")
        with patch.object(decision.os, "replace", side_effect=OSError("injected failure")):
            with self.assertRaises(OSError):
                decision.atomic_write(target, b"new")
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(list(self.cwd.glob(".result.md.*")), [])

    def test_interrupted_promotion_can_adopt_identical_adr(self):
        self.record()
        self.accept()
        output = self.cwd / "recovered.md"
        args = decision.parser().parse_args(["promote", "--file", str(self.ledger),
                "--task-id", "task-one", "--plan", str(self.plan), "--decision-id", "dec-one",
                "--output", str(output)])
        before = self.ledger.read_bytes()
        with patch.object(decision, "append_events", side_effect=OSError("receipt interrupted")):
            with self.assertRaises(OSError):
                decision.run(args)
        self.assertTrue(output.exists())
        self.assertEqual(self.ledger.read_bytes(), before)
        original = output.read_bytes()
        self.promote("dec-one", True, "--output", str(output))
        self.assertEqual(original, output.read_bytes())
        self.cli("validate")

    def test_concurrent_writers_and_duplicate_race(self):
        processes = [subprocess.Popen([sys.executable, str(SCRIPT), *self.record_args(f"dec-{i}")],
                                      cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for i in range(8)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.cli("validate")
        self.assertEqual(len(json.loads(self.cli("summary", "--json").stdout)), 8)
        processes = [subprocess.Popen([sys.executable, str(SCRIPT), *self.record_args("dec-race")],
                                      cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(2)]
        for process in processes:
            process.communicate(timeout=20)
        self.assertEqual(sorted(process.returncode for process in processes), [0, 1])
        self.cli("validate")


if __name__ == "__main__":
    unittest.main()
