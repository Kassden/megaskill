"""Registry contracts and CLI proof; no native agents are spawned by these tests."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mega_agents.py"
SPEC = importlib.util.spec_from_file_location("mega_agents", SCRIPT)
agents = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agents)


def receipt(agent_id, status=None):
    return {"tool": "close_agent", "arguments": {"id": agent_id},
            "result": {"status": {"completed": "verified result"} if status is None else status}}


class MegaAgentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.root = self.workspace / ".mega"

    def assign(self, agent_id="child", **kwargs):
        values = dict(root=self.root, task_id="task", parent_session_id="parent",
                      agent_id=agent_id, role="executor", objective="bounded implementation",
                      edit_set=[], verification="python3 -m unittest")
        values.update(kwargs)
        return agents.assign(**values)

    def cli(self, command, *args, input=None):
        base = [sys.executable, str(SCRIPT), command]
        if command != "roles":
            base += ["--root", str(self.root), "--task-id", "task",
                     "--parent-session-id", "parent"]
        return subprocess.run(base + list(args), cwd=self.workspace, input=input,
                              text=True, capture_output=True)

    def test_cli_workflow_and_readback(self):
        result = self.cli("assign", "--agent-id", "child", "--role", "executor",
                          "--objective", "implement", "--edit", "src/a.py",
                          "--verification", "python3 -m unittest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "assigned")
        done = self.cli("complete", "--agent-id", "child")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "completed")
        before = (self.root / "agents.json").read_bytes()
        report = self.cli("cleanup")
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)["required_native_close_calls"],
                         [{"tool": "close_agent", "arguments": {"target": "child"}}])
        self.assertEqual((self.root / "agents.json").read_bytes(), before)
        closed = self.cli("close", "--agent-id", "child", "--receipt", "-",
                          input=json.dumps(receipt("child")))
        self.assertEqual(closed.returncode, 0, closed.stderr)
        listing = self.cli("list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        row = json.loads(listing.stdout)[0]
        self.assertEqual(row["status"], "closed")
        self.assertEqual(row["close_receipt"], receipt("child"))
        self.assertEqual(agents.cleanup(self.root, "task", "parent")["owned_ids"], [])
        self.assertEqual(agents.open_agents(self.root, "task"), [])

    def test_default_quota_includes_completed_children(self):
        for i in range(3):
            self.assign(str(i))
            agents.complete(self.root, "task", "parent", str(i))
        with self.assertRaisesRegex(ValueError, "quota"):
            self.assign("fourth")
        agents.close(self.root, "task", "parent", "0", receipt("0"))
        self.assign("fourth")
        self.assertEqual(len(agents.open_agents(self.root, "task")), 3)

    def test_quota_override_is_fixed_per_owner(self):
        self.assign("one", max_open=1)
        with self.assertRaisesRegex(ValueError, "fixed"):
            self.assign("two", max_open=2)
        with self.assertRaisesRegex(ValueError, "quota"):
            self.assign("two", max_open=1)

    def test_process_concurrency_cannot_exceed_quota_or_lose_rows(self):
        def attempt(i):
            return self.cli("assign", "--agent-id", str(i), "--role", "tester",
                            "--objective", "exercise", "--verification", "run tests")
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(attempt, range(12)))
        self.assertEqual(sum(r.returncode == 0 for r in results), 3)
        for result in results:
            if result.returncode != 0:
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("quota", json.loads(result.stderr)["error"])
        self.assertEqual(len(agents.open_agents(self.root, "task")), 3)

    def test_process_concurrency_rejects_overlapping_edit_sets(self):
        def attempt(i):
            return self.cli("assign", "--agent-id", str(i), "--role", "executor",
                            "--objective", "edit shared file", "--edit", "src/shared.py",
                            "--verification", "run tests")
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(attempt, range(6)))
        self.assertEqual(sum(r.returncode == 0 for r in results), 1)
        for result in results:
            if result.returncode != 0:
                self.assertEqual(result.returncode, 2)
                self.assertIn("overlap", result.stderr)

    def test_overlaps_include_directory_aliases_and_completed_rows(self):
        self.assign("one", edit_set=["src"])
        agents.complete(self.root, "task", "parent", "one")
        for path in ("src", "src/a.py", "other/../src/a.py", str(self.workspace / "src")):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "overlap"):
                self.assign("two", edit_set=[path], task_id="other", parent_session_id="else")
        self.assign("two", edit_set=["src2/a.py"])
        agents.close(self.root, "task", "parent", "one", receipt("one"))
        self.assign("three", edit_set=["src/a.py"])

    def test_reverse_directory_overlap_and_symlink_alias(self):
        (self.workspace / "src").mkdir()
        (self.workspace / "alias").symlink_to(self.workspace / "src", target_is_directory=True)
        self.assign("one", edit_set=["src/a.py"])
        for path in ("src", "alias/a.py"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "overlap"):
                self.assign("two", edit_set=[path])

    def test_ownership_exact_and_unknown_never_closed(self):
        self.assign("one")
        self.assign("two", task_id="task-extra")
        self.assign("three", parent_session_id="parent-extra")
        self.assertEqual(agents.cleanup(self.root, "task", "parent")["owned_ids"], ["one"])
        self.assertEqual([a["agent_id"] for a in agents.open_agents(self.root, "task")],
                         ["one", "three"])
        for task, parent, child in (("task-extra", "parent", "one"),
                                     ("task", "parent-extra", "one"),
                                     ("task", "parent", "unknown")):
            for change in (agents.complete, agents.close):
                args = (self.root, task, parent, child)
                if change is agents.close:
                    args += (receipt(child),)
                with self.subTest(task=task, parent=parent, change=change), self.assertRaises(ValueError):
                    change(*args)

    def test_duplicate_ids_and_recursion_rejected(self):
        self.assign("child")
        for changes in ({"task_id": "different"}, {"parent_session_id": "different"}):
            with self.assertRaisesRegex(ValueError, "already registered"):
                self.assign("child", **changes)
        with self.assertRaisesRegex(ValueError, "recursive"):
            self.assign("grandchild", parent_session_id="child")
        with self.assertRaisesRegex(ValueError, "recursive"):
            self.assign("parent")
        with self.assertRaisesRegex(ValueError, "recursive"):
            self.assign("self", parent_session_id="self")
        agents.close(self.root, "task", "parent", "child", receipt("child"))
        with self.assertRaisesRegex(ValueError, "recursive"):
            self.assign("grandchild", parent_session_id="child")

    def test_transitions_and_receipt_are_retained_and_idempotent(self):
        self.assign()
        agents.complete(self.root, "task", "parent", "child")
        agents.complete(self.root, "task", "parent", "child")
        proof = receipt("child")
        agents.close(self.root, "task", "parent", "child", proof)
        before = (self.root / "agents.json").read_bytes()
        agents.close(self.root, "task", "parent", "child", proof)
        self.assertEqual((self.root / "agents.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            agents.complete(self.root, "task", "parent", "child")
        with self.assertRaises(ValueError):
            agents.close(self.root, "task", "parent", "child", receipt("child", "shutdown"))

    def test_active_child_can_be_closed_with_native_result(self):
        self.assign()
        row = agents.close(self.root, "task", "parent", "child", receipt("child", "running"))
        self.assertEqual(row["status"], "closed")

    def test_invalid_receipts_do_not_change_state(self):
        self.assign()
        before = (self.root / "agents.json").read_bytes()
        invalid = [None, {}, "closed", {"closed": True}, receipt("wrong"),
                   receipt("child", "closed"), receipt("child", "not_found"),
                   receipt("child", {"completed": 1}), receipt("child", []),
                   {"tool": "wait_agent", "arguments": {"id": "child"},
                    "result": {"status": "shutdown"}},
                   {"tool": "close_agent", "arguments": {"id": "child"},
                    "result": {"status": "shutdown", "error": "failed"}}]
        for proof in invalid:
            with self.subTest(proof=proof), self.assertRaises(ValueError):
                agents.close(self.root, "task", "parent", "child", proof)
            self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_hooks_match_parent_and_never_invent_closed(self):
        self.assign()
        payload = {"hook_event_name": "SubagentStart", "session_id": "parent", "agent_id": "child"}
        self.assertTrue(agents.observe(payload, self.root, "task")["observed"])
        payload["hook_event_name"] = "SubagentStop"
        row = agents.observe(payload, self.root, "task")["agent"]
        self.assertEqual(row["status"], "completed")
        self.assertNotIn("close_receipt", row)
        self.assertEqual(len(agents.open_agents(self.root, "task")), 1)
        for change in ({"session_id": "else"}, {"agent_id": "unknown"}, {"task_id": "task-extra"}):
            before = (self.root / "agents.json").read_bytes()
            self.assertFalse(agents.observe({**payload, **change}, self.root, "task")["observed"])
            self.assertEqual((self.root / "agents.json").read_bytes(), before)
        payload["hook_event_name"] = "SubagentStart"
        self.assertEqual(agents.observe(payload, self.root, "task")["agent"]["status"], "assigned")
        agents.close(self.root, "task", "parent", "child", receipt("child"))
        self.assertFalse(agents.observe(payload, self.root, "task")["observed"])

    def test_read_only_queries_do_not_create_registry(self):
        self.assertEqual(agents.open_agents(self.root, "task"), [])
        self.assertEqual(agents.cleanup(self.root, "task", "parent")["owned_ids"], [])
        payload = {"hook_event_name": "SubagentStart", "session_id": "parent", "agent_id": "unknown"}
        self.assertFalse(agents.observe(payload, self.root, "task")["observed"])
        self.assertFalse(self.root.exists())

    def test_roles_are_on_demand(self):
        result = self.cli("roles")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(json.loads(result.stdout)),
                         {"thinker", "planner", "executor", "tester", "verifier", "orchestrator"})
        self.assertFalse(self.root.exists())
        self.assertEqual(self.assign(role="verifier")["role"], "verifier")
        self.assertEqual(len(agents.list_agents(self.root, "task", "parent")), 1)

    def test_bad_assignment_inputs_and_paths_fail_before_creation(self):
        invalid = [{"task_id": ""}, {"parent_session_id": " parent"}, {"agent_id": "a\n"},
                   {"objective": ""}, {"verification": None}, {"role": "wizard"},
                   {"role": []}, {"max_open": 0}, {"max_open": True}, {"max_open": "3"},
                   {"edit_set": "a.py"}, {"edit_set": [1]}, {"edit_set": ["../outside"]},
                   {"edit_set": ["*.py"]}, {"edit_set": [".mega/agents.json"]}]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.assign(**values)
        self.assertFalse(self.root.exists())

    def test_malformed_hooks_rejected(self):
        for payload in (None, [], {}, {"hook_event_name": "Stop"}, {"hook_event_name": []},
                        {"hook_event_name": "SubagentStop", "session_id": "p"}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                agents.observe(payload, self.root, "task")
        self.assertFalse(self.root.exists())

    def test_corrupt_registry_fails_closed_and_preserves_bytes(self):
        self.root.mkdir()
        for raw in ("{", "null", '{"version": 2,"agents": []}',
                    '{"version": 1,"agents": {}}', '{"version": 1,"agents": [{}]}'):
            (self.root / "agents.json").write_text(raw)
            with self.assertRaises(ValueError):
                agents.cleanup(self.root, "task", "parent")
            with self.assertRaises(ValueError):
                self.assign()
            self.assertEqual((self.root / "agents.json").read_text(), raw)

    def test_corrupt_record_unhashable_fields_fail_closed(self):
        self.assign()
        data = json.loads((self.root / "agents.json").read_text())
        for key in ("role", "status"):
            broken = json.loads(json.dumps(data))
            broken["agents"][0][key] = []
            (self.root / "agents.json").write_text(json.dumps(broken))
            with self.subTest(key=key), self.assertRaises(ValueError):
                agents.open_agents(self.root, "task")

    def tool_payload(self, tool="spawn_agent", inputs=None, response=None, **kwargs):
        return dict(hook_event_name="PostToolUse", session_id="parent", tool_name=tool,
                    tool_input={"agent_type": "worker", "message": "Implement\n scoped work"}
                    if inputs is None else inputs,
                    tool_response={"agent_id": "child", "nickname": "Worker"}
                    if response is None else response, **kwargs)

    def test_check_spawn_default_quota_and_exact_ownership(self):
        self.assertTrue(agents.check_spawn(self.root, "task", "parent")["allowed"])
        self.assertFalse(self.root.exists())
        for i in range(3):
            self.assign(str(i))
            agents.complete(self.root, "task", "parent", str(i))
        before = (self.root / "agents.json").read_bytes()
        check = agents.check_spawn(self.root, "task", "parent")
        self.assertFalse(check["allowed"])
        self.assertIn("quota", check["reason"])
        self.assertEqual(check["open_count"], 3)
        self.assertEqual((self.root / "agents.json").read_bytes(), before)
        self.assertTrue(agents.check_spawn(self.root, "other-task", "parent")["allowed"])
        self.assertTrue(agents.check_spawn(self.root, "task", "other-parent")["allowed"])
        for task in ("task", "other-task"):
            self.assertFalse(agents.check_spawn(self.root, task, "0")["allowed"])
        agents.close(self.root, "task", "parent", "0", receipt("0"))
        self.assertTrue(agents.check_spawn(self.root, "task", "parent")["allowed"])
        self.assertFalse(agents.check_spawn(self.root, "task", "0")["allowed"])

    def test_post_spawn_infers_brief_role_metadata_and_can_be_refined(self):
        payload = self.tool_payload(inputs={"agent_type": "explorer", "message": "Explore\n assumptions"})
        observed = agents.observe(payload, self.root, "task")
        self.assertTrue(observed["observed"])
        self.assertEqual(observed["role_metadata"]["role"], "thinker")
        row = observed["agent"]
        self.assertFalse(row["scope_confirmed"])
        self.assertEqual(row["objective"], "Explore assumptions")
        self.assertEqual(row["spawn_receipt"]["result"], payload["tool_response"])
        refined = self.assign(edit_set=["src/a.py"], role="executor")
        self.assertTrue(refined["scope_confirmed"])
        self.assertEqual(refined["edit_set"], [str((self.workspace / "src/a.py").resolve())])
        before = (self.root / "agents.json").read_bytes()
        agents.observe(payload, self.root, "task")
        self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_post_spawn_preserves_prior_assign_and_completed_or_closed_status(self):
        self.assign(role="verifier", edit_set=["tests/check.py"])
        for state in ("assigned", "completed", "closed"):
            if state == "completed":
                agents.complete(self.root, "task", "parent", "child")
            elif state == "closed":
                agents.close(self.root, "task", "parent", "child", receipt("child"))
            before = (self.root / "agents.json").read_bytes()
            result = agents.observe(self.tool_payload(), self.root, "task")
            self.assertEqual(result["agent"]["status"], state)
            self.assertEqual(result["agent"]["role"], "verifier")
            self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_post_spawn_native_prefix_and_close_target_or_id(self):
        for index, argument in enumerate(("target", "id")):
            child = str(index)
            spawn = self.tool_payload(tool="multi_agent_v1__spawn_agent", response={"agent_id": child})
            self.assertTrue(agents.observe(spawn, self.root, "task")["observed"])
            close_payload = self.tool_payload(tool="multi_agent_v1__close_agent",
                                             inputs={argument: child}, response={"status": "shutdown"})
            closed = agents.observe(close_payload, self.root, "task")
            self.assertEqual(closed["agent"]["status"], "closed")
            self.assertEqual(closed["agent"]["close_receipt"],
                             {"tool": "multi_agent_v1__close_agent", "arguments": {argument: child},
                              "result": {"status": "shutdown"}})
        self.assertEqual(agents.cleanup(self.root, "task", "parent")["owned_ids"], [])

    def test_installed_role_profile_names_are_inferred(self):
        for index, role in enumerate(agents.ROLES):
            child = str(index)
            payload = self.tool_payload(inputs={"agent_type": "megaskill-" + role},
                                        response={"agent_id": child})
            observed = agents.observe(payload, self.root, "task")
            self.assertEqual(observed["role_metadata"]["role"], role)
            self.assertEqual(observed["agent"]["role"], role)
            agents.close(self.root, "task", "parent", child, receipt(child))

    def test_post_close_unknown_and_wrong_owner_are_not_registered_or_closed(self):
        close_payload = self.tool_payload(tool="close_agent", inputs={"target": "child"},
                                         response={"status": "shutdown"})
        self.assertFalse(agents.observe(close_payload, self.root, "task")["observed"])
        self.assertFalse(self.root.exists())
        self.assign(task_id="other-task")
        before = (self.root / "agents.json").read_bytes()
        self.assertFalse(agents.observe(close_payload, self.root, "task")["observed"])
        self.assertFalse(agents.observe(self.tool_payload(), self.root, "task")["observed"])
        self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_post_close_requires_real_result_not_lifecycle_claim(self):
        self.assign()
        before = (self.root / "agents.json").read_bytes()
        for response in ({"closed": True}, {"status": "not_found"}, {"status": "closed"},
                         {"status": "shutdown", "error": "failed"}, {}):
            payload = self.tool_payload(tool="close_agent", inputs={"target": "child"}, response=response)
            with self.subTest(response=response), self.assertRaises(ValueError):
                agents.observe(payload, self.root, "task")
            self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_post_tool_malformed_unrelated_failed_and_ambiguous_inputs(self):
        unrelated = self.tool_payload(tool="Bash", inputs={}, response={})
        self.assertFalse(agents.observe(unrelated, self.root, "task")["observed"])
        failed = self.tool_payload(response={"error": "spawn failed"})
        self.assertFalse(agents.observe(failed, self.root, "task")["observed"])
        for payload in (self.tool_payload(inputs=[]), self.tool_payload(response=[]),
                        self.tool_payload(response={"agent_id": ""}),
                        self.tool_payload(tool="close_agent", inputs={"target": "a", "id": "b"}),
                        self.tool_payload(response={"agent_id": "a", "error": "failed"})):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                agents.observe(payload, self.root, "task")
        self.assertFalse(self.root.exists())

    def test_observed_excess_spawn_remains_visible_for_cleanup(self):
        for i in range(3):
            self.assign(str(i))
        self.assertFalse(agents.check_spawn(self.root, "task", "parent")["allowed"])
        observed = agents.observe(self.tool_payload(), self.root, "task")
        self.assertIn("quota", observed["agent"]["policy_violation"])
        self.assertEqual(agents.cleanup(self.root, "task", "parent")["owned_ids"],
                         ["0", "1", "2", "child"])
        self.assertFalse(agents.check_spawn(self.root, "task", "parent")["allowed"])

    def test_post_spawn_rejects_recursive_parent(self):
        self.assign()
        payload = self.tool_payload(response={"agent_id": "grandchild"})
        payload["session_id"] = "child"
        with self.assertRaisesRegex(ValueError, "recursive"):
            agents.observe(payload, self.root, "task")
        self.assertEqual(len(agents.open_agents(self.root, "task")), 1)

    def test_target_receipt_cli_supported(self):
        self.assign()
        proof = receipt("child")
        proof["arguments"] = {"target": "child"}
        result = self.cli("close", "--agent-id", "child", "--receipt", "-", input=json.dumps(proof))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["close_receipt"], proof)

    def test_current_native_previous_status_wire_schema(self):
        statuses = ("pending_init", "running", "interrupted", "shutdown",
                    {"completed": "native result"}, {"completed": None}, {"errored": "native error"})
        for index, status in enumerate(statuses):
            child = str(index)
            self.assign(child)
            payload = self.tool_payload(tool="close_agent", inputs={"target": child},
                                        response={"previous_status": status})
            row = agents.observe(payload, self.root, "task")["agent"]
            self.assertEqual(row["status"], "closed")
            self.assertEqual(row["close_receipt"]["result"], {"previous_status": status})
        self.assign("open")
        before = (self.root / "agents.json").read_bytes()
        for status in ("not_found", {"errored": None}, {"completed": False}, "closed"):
            payload = self.tool_payload(tool="close_agent", inputs={"target": "open"},
                                        response={"previous_status": status})
            with self.subTest(status=status), self.assertRaises(ValueError):
                agents.observe(payload, self.root, "task")
            self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_current_wire_close_exact_task_and_parent(self):
        self.assign()
        payload = self.tool_payload(tool="close_agent", inputs={"target": "child"},
                                    response={"previous_status": {"completed": None}})
        before = (self.root / "agents.json").read_bytes()
        for task, parent in (("task-other", "parent"), ("task", "parent-other")):
            payload["session_id"] = parent
            self.assertFalse(agents.observe(payload, self.root, task)["observed"])
            self.assertEqual((self.root / "agents.json").read_bytes(), before)

    def test_main_hook_adapter_pre_and_post_native_tools(self):
        # All native results here are fixtures; exercise the actual adapter in an isolated process.
        code = '''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mega_task import register
from mega_hooks import handle
workspace = Path(sys.argv[2])
root = workspace / '.mega'
plan = workspace / 'PLAN.md'
plan.write_text('### Subphase 1.1: Work\\n')
register(root, 'task', plan, 'bounded work', session='parent')
def call(event, **fields):
    return handle(dict(session_id='parent', cwd=str(workspace), hook_event_name=event, **fields))
for i in range(3):
    assert call('PreToolUse', tool_name='spawn_agent', tool_input={}) == {}
    assert call('PostToolUse', tool_name='multi_agent_v1__spawn_agent',
                tool_input={'agent_type':'megaskill-verifier', 'message':'check evidence'},
                tool_response={'agent_id':str(i)}) == {}
assert call('PreToolUse', tool_name='spawn_agent', tool_input={}) == {}
from mega_agents import check_spawn
assert check_spawn(root, 'task', 'parent')['allowed'] is False
assert call('PostToolUse', tool_name='close_agent', tool_input={'target':'0'},
            tool_response={'previous_status':{'completed':None}}) == {}
assert call('PreToolUse', tool_name='spawn_agent', tool_input={}) == {}
assert call('PostToolUse', tool_name='Bash', tool_input={'command':'true'}, tool_response=0) == {}
rows = json.loads((root / 'agents.json').read_text())['agents']
assert rows[0]['status'] == 'closed'
assert rows[0]['close_receipt']['arguments'] == {'target':'0'}
assert all(row['role'] == 'verifier' for row in rows)
print(json.dumps({'quota_reported_without_tool_lock': True, 'closed_from_previous_status': True, 'records':len(rows)}))
'''
        result = subprocess.run([sys.executable, "-c", code, str(SCRIPT.parent), str(self.workspace)],
                                env={**os.environ, "MEGA_BINDINGS_DIR": str(self.workspace / "bindings")},
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["quota_reported_without_tool_lock"])

    def test_cli_invalid_inputs_are_errors_without_tracebacks(self):
        self.assign()
        for result in (self.cli("close", "--agent-id", "child"),
                       self.cli("close", "--agent-id", "child", "--receipt", "-", input="{"),
                       self.cli("close", "--agent-id", "child", "--receipt", "-", input="null"),
                       self.cli("close", "--agent-id", "child", "--receipt", "/missing/receipt.json"),
                       self.cli("complete", "--agent-id", "wrong")):
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(agents.open_agents(self.root, "task")[0]["status"], "assigned")


if __name__ == "__main__":
    unittest.main()
