# Bounded subagent dispatch

This implements runtime plan subphase 2.2. Select responsibilities on demand:
thinker explores assumptions; planner defines work; executor implements; tester
exercises behavior; verifier checks outcomes independently; orchestrator coordinates
dependencies. These are operating conventions, not six required children or native
agent profiles. The parent can perform any responsibility itself. Give a verifier
acceptance criteria and evidence to check independently of the executor's claims.

[Official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
describes parent orchestration, thread closure, inherited permissions, and the native
`agents.max_concurrent_threads_per_session` setting. The registry's default limit of
three is a local policy and does not change native configuration or grant permissions.
[Official hook documentation](https://learn.chatgpt.com/docs/hooks) specifies that
subagent hooks use the parent's `session_id` and the child's `agent_id`.

## Storage and ownership

Pass `root = workspace / ".mega"`, not the workspace itself. Storage is
`root/agents.json`, schema `{"version": 1, "agents": [...]}`. Writers hold an exclusive
stdlib `fcntl.flock` on the stable `root/.agents.lock` inode across read, validation,
and atomic replacement. Readers see an entire old or new snapshot. CLI reads,
`open_agents`, and `cleanup` never create directories, lock files, or registry files.
Requires POSIX (including macOS and Linux).

Each assignment stores `agent_id`, `task_id`, `parent_session_id`, `role`, `objective`,
`edit_set`, `verification`, `max_open`, and `status`. Ownership is the exact task and
parent pair. IDs cannot be reassigned, even after closure. Registered child IDs can
never serve as parents, and an existing parent cannot become a child; no recursive
spawn is permitted, including by the orchestrator responsibility.

The quota counts every unclosed child owned by the pair, including completed children.
`max_open` defaults to 3, is configurable at the first assignment, and cannot change
for that pair later. `check_spawn(root, task_id, parent_session_id)` returns a read-only
`allowed` boolean and `reason` for the main PreToolUse hook to allow or deny a native
spawn. It counts prior explicit assignments and PostToolUse-inferred assignments
equally. Registered children are denied even after closure. Literal edit paths resolve against the workspace, stay inside
it and outside `.mega`, and must not overlap any open assignment in the registry,
including other tasks/parents. Equal files, directory/descendant paths, `..` aliases,
and symlink aliases overlap. An empty edit set declares no edit ownership. It is not
a sandbox: native permissions and a child's adherence to its brief remain separate.

Before dispatch, invoke `check_spawn` through the main PreToolUse hook, issue a
narrowly scoped native spawn from the parent, and observe its PostToolUse result.
Unknown returned child IDs are registered to the exact task and parent with an
inferred role, brief objective, empty edit set, and `scope_confirmed: false`.
An explicit `role`, or an `agent_type` matching a responsibility (including installed
`megaskill-thinker`, `megaskill-planner`, etc. profile names), selects that role;
`explorer` maps to thinker and other native profiles default to executor. These are
inferences, not confirmed permissions. Call `assign` on that same ID and owner to
confirm its objective, edit set, role and verification. This refinement does not
consume another slot. Prior explicit assignments are preserved by observation.

The registry never spawns or closes agents itself. Main hooks translate the spawn
check into a native PreToolUse denial. The check is a snapshot, not a reservation
across the native call; serialize dispatch in the parent and configure the native
thread cap to 3. A PostToolUse handler cannot undo a spawn that already ran. If
concurrent or unguarded native calls exceed the registry quota, observation retains
the actual child with `policy_violation` so cleanup can include it, and further
spawn checks deny. A Start hook may precede assignment; it ignores unknown IDs until
PostToolUse obtains the authoritative spawn result.

## CLI interface

All successful commands print one JSON value and exit 0. Validation, storage, and
receipt errors exit 2; handled errors print `{"error": "..."}` to stderr. Missing
arguments use argparse's standard usage error. No command calls native agent tools.

```text
python3 scripts/mega_agents.py roles
python3 scripts/mega_agents.py assign --root WORKSPACE/.mega \
  --task-id TASK --parent-session-id PARENT --agent-id NATIVE_CHILD_ID \
  --role {thinker,planner,executor,tester,verifier,orchestrator} \
  --objective "Scoped outcome" --verification "Exact verification command" \
  [--edit src/file.py ...] [--max-open 3]
python3 scripts/mega_agents.py list --root WORKSPACE/.mega \
  --task-id TASK --parent-session-id PARENT
python3 scripts/mega_agents.py complete --root WORKSPACE/.mega \
  --task-id TASK --parent-session-id PARENT --agent-id NATIVE_CHILD_ID
python3 scripts/mega_agents.py cleanup --root WORKSPACE/.mega \
  --task-id TASK --parent-session-id PARENT
python3 scripts/mega_agents.py close --root WORKSPACE/.mega \
  --task-id TASK --parent-session-id PARENT --agent-id NATIVE_CHILD_ID \
  --receipt native-close-receipt.json
```

`--root` defaults to `Path.cwd() / ".mega"` on each scoped command. Repeat `--edit`
for each literal path; omit it for no edits. `--receipt -` reads JSON from stdin.
`roles` returns the responsibility-to-description object. `assign`, `complete`,
and `close` return the resulting record; `list` returns all exactly owned records,
including closed ones. `cleanup` returns:

```json
{
  "task_id": "TASK",
  "parent_session_id": "PARENT",
  "owned_ids": ["NATIVE_CHILD_ID"],
  "required_native_close_calls": [
    {"tool": "close_agent", "arguments": {"target": "NATIVE_CHILD_ID"}}
  ]
}
```

Execute those calls through the parent runtime, then record each actual receipt
with `close`. Cleanup does not mutate status or close anything. Unknown IDs and
other owners are never included. Before handoff, read cleanup again and require
`owned_ids: []`.

## Completion and native close receipts

`assigned -> completed` records work stopping. Both states still consume quota and
edit ownership. Either may transition to `closed` only with a successful native
close result bound to this child. Closing an active child can represent cancellation;
it does not prove the assignment was fulfilled. Repeated `complete` is idempotent.
Repeated `close` with the same receipt is idempotent; replacing a closed receipt or
completing a closed child is rejected.

The receipt file wraps the exact native call arguments and unmodified JSON result:

```json
{
  "tool": "close_agent",
  "arguments": {"target": "NATIVE_CHILD_ID"},
  "result": {"previous_status": {"completed": "Native result text"}}
}
```

Copy `result` from the **actual `close_agent` response**, never from `wait_agent`,
SubagentStop, or a claimed `closed: true` flag. Current wire shape is exactly
`{"previous_status": STATUS}`, with arguments `{"target": CHILD}`. Legacy
`{"status": STATUS}` and arguments `{"id": CHILD}` are also accepted. STATUS is
`pending_init`, `running`, `shutdown`, `interrupted`, `{"completed": STRING_OR_NULL}`,
or `{"errored": STRING}`. Mixed/ambiguous target/id arguments and result status keys
are rejected. Both `close_agent` and `multi_agent_v1__close_agent` tool names are
supported and retained exactly in the receipt. A native close
can return the status preceding shutdown; `running` in this response does not mean
the registry should remain open. `not_found`, errors, arbitrary success booleans,
and unknown result schemas fail closed. Retain the complete wrapper in
`close_receipt`. If the runtime's schema changes, update this adapter against an
actual result before accepting it.

JSON validation checks structure and exact ID binding; a caller-supplied receipt
file cannot authenticate that a native tool was invoked. The PostToolUse adapter
can directly retain the native `tool_input` and `tool_response` as the call/result
receipt, then record closure. This script has no runtime closure capability and
does not invent a result. Tests use explicit fixtures, not live closure evidence.

## Callable hook interface

```python
open_agents(root: Path, task_id: str) -> list
observe(payload: dict, root: Path, task_id: str) -> dict
check_spawn(root: Path, task_id: str, parent_session_id: str) -> dict
```

`open_agents` returns unclosed records with the exact task ID across its parents.
Callers enforcing a parent-specific gate must also filter `parent_session_id`.
It is a registry snapshot, not a global runtime inventory. Corrupt storage raises
`ValueError`; filesystem errors raise `OSError`. Never treat these as an empty list.

`observe` accepts official `hook_event_name` (`SubagentStart`, `SubagentStop`, or `PostToolUse`),
`session_id` (parent), and `agent_id` (child). Select `task_id` from the active task
contract. If an optional payload `task_id` exists it must exactly match. Other hook
fields are allowed. Lifecycle observation returns `{"observed": true, "agent": RECORD}` for a matching
open assignment; unknown/wrong-owner/closed children return
`{"observed": false, "reason": STRING}` without changing storage. Malformed payloads
raise `ValueError`.

Start records `assigned` (including a resumed completed child); Stop records
`completed`; both retain `last_observation` with event and UTC timestamp. Neither
records closure. Stop can be followed by continuation or resume, so this status is
an observation and does not replace independent verification of the outcome.
Delayed hooks cannot resurrect a closed record. Lifecycle hooks cannot prove closure
or discover unknown ownership.

For PostToolUse, use the parent's `session_id`, canonical `tool_name`, JSON-object
`tool_input` and `tool_response`. Both canonical names and the `multi_agent_v1__`
prefix are supported for spawn and close. Spawn reads the native response's
`agent_id` and retains `spawn_receipt` with its actual input and result. An unknown
spawn returns `role_metadata: {role, description, scope_confirmed: false}` in addition
to the record; message/prompt contributes a whitespace-normalized 240-character
objective. No edit ownership is inferred from prose. Prior assignments remain
unchanged, and replayed/delayed results cannot reopen a closed child. A failed spawn
without `agent_id` returns `observed: false`.

Close reads `target` or `id` and validates the actual `tool_response` through the
same receipt validator used by the CLI. Only an exactly owned record can become
closed. Unknown or other-owner IDs return `observed: false` and remain untouched.
Unrelated PostToolUse tools also return `observed: false` without requiring an
agent-shaped input/response. Unsupported close result shapes raise `ValueError`
and leave the child open. Ordinary Start/Stop observations never invent closure.

`check_spawn` returns `{"allowed": BOOL, "reason": STRING, "open_count": INT,
"max_open": INT}` for a parent, or `{"allowed": false, "reason": STRING}` when
recursive spawning is denied. It is read-only, including for absent registries;
invalid inputs or corrupt storage raise errors rather than allowing fan-out.

## Proof

```text
python3 -m unittest discover -s tests -p 'test_mega_agents.py' -v
```

Fixtures exercise the complete CLI/readback workflow, process races against the
three-child quota and overlapping edit sets, completed-child retention, path aliases,
exact ownership, no recursion, both close wire variants and retained receipts,
pre-spawn decisions, PostToolUse registration/refinement and closure, unrelated tools,
read-only cleanup, corruption, and invalid inputs. No native children are created.
# Shared checkout ownership

The orchestrator owns branch changes and integration. A child in a shared checkout must not switch or create branches, stage unrelated files, or commit unless explicitly assigned. The parent's declared dedicated branch already provides task isolation. Use a separate worktree when filesystem isolation is required; a fresh conversation alone does not isolate files.

