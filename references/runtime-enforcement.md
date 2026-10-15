# Runtime completion enforcement

The canonical Markdown plan describes work. A versioned `.mega/tasks/TASK.json` contract captures exact task identity, mode, plan hash and acceptance obligations. Per-session bindings under `~/.codex/megaskill/sessions/` restore the original workspace after cwd changes. JSONL task events are append-only. Concurrent writes use file locks and atomic contract replacement.

## Execute a registered task

```sh
python3 scripts/mega_task.py register --id task-name --plan PLAN.md --goal "requested outcome" --session SESSION_ID --acceptance ACCEPTANCE.json
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind test --artifact src/changed.py -- python3 -m unittest
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind readback --artifact output.txt -- python3 scripts/assert_output.py
python3 scripts/mega_task.py done --id task-name --obligation 1.1 --proof TEST_EVENT_ID --proof READBACK_EVENT_ID
python3 scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task task-name --verdict done
```

Choose input/artifact files covering the relevant proof surface. Hashes detect changes to those files, not every possible unlisted dependency. A proof command must assert the desired result; a successful `true` or directory listing is insufficient semantic evidence. Manual/external attestations require explicit provenance and reviewer judgment. Agent-writable ledgers are a reliability mechanism, not protection against an adversarial agent.

## Outcome assertions (required for certification)

`ACCEPTANCE.json` maps every exact obligation ID to a nonempty list of assertions.
Paths must be absolute. `text` checks compare exact UTF-8 text; `json` checks
traverse a nonempty list of object keys and compare value and type; `review`
checks require a passing independent review with rationale. Example:

```json
{"1.1": [{"kind": "json", "description": "No unrouted connections remain",
  "path": "/project/.mega/pcb-result.json", "inputs": ["/project/board.kicad_pcb"],
  "pointer": ["unrouted"], "equals": 0}]}
```

JSON reports must include `inputs`, mapping every declared source input's absolute
path to its current SHA-256. Proof receipts must cover the outcome file and every
source input. Canonical symlink aliases are equivalent. For `text`, use `equals`
with the entire requested output. For `review`, omit `pointer`/`equals`; the report
contains `verdict: "pass"`, `reviewer_session_id`, `rationale`, and current `inputs`.
All sessions that have executed/rebound the task are excluded as reviewers.
The review must evaluate the requested visual/content criteria, not merely image
existence or CSS animation presence. The script validates linkage, not the truth
of a claimed reviewer identity or the quality of their judgment; retain the actual
native reviewer result or explicit human approval as provenance.

New execute-mode CLI registrations require `--acceptance`. To migrate an existing
task, run `acceptance --id TASK --file ACCEPTANCE.json --authority "USER REQUEST"
--reason "WHY"`; all old done receipts are invalidated. `reconcile` removes a
policy if its obligation set changes. API `evaluate(..., require_outcomes=False)`
is retained only for historical artifact analysis and labels that assurance;
CLI evaluation, Stop and task-based final gates require outcome checks. State-only
`final-gate --verdict done` cannot certify a requested outcome. Do not generate a
trivial text sentinel as a substitute for a requested engineering result.

Registration/binding cannot silently replace an unfinished bound task, even if a
new task ID is used. An explicit user scope replacement can use
`--replace-authority`, retaining the previous goal and authority in the binding.

## Observe the actual host

`mega_task.py runtime --id TASK [--session SESSION]` is read-only. Each native hook
invocation records event, session, time and handler digest under the binding
directory's `receipts/`. It records early-return paths, not prompts or secrets.
Verification requires prompt, tool and Stop observations at the current revision
within 15 minutes (last 500 receipts). Prompt/tool-only evidence is distinguished
from Stop coverage. A first successful Stop at a changed revision continues once
to permit strict final-gate readback. Paused/status bypasses are separately audited.

Missing receipts never mean the hook is healthy. Inspect the exact session's
native `/hooks`, trust, enablement and host support. Local hook code cannot force
an unsupported or disabled host to invoke it, nor override quota, timeout or user
interruption. Do not claim a global/local canary proves another session. Current
[official managed-configuration guidance](https://learn.chatgpt.com/docs/enterprise/managed-configuration)
also distinguishes supported hooks with local versus cloud orchestration; a local
execution environment alone is not proof that orchestration invokes local hooks.

`block --obligation ID --blocker-class credentials --attempted "attempt and observed result" --reason ... --evidence ... --resolution ...` scopes an external blocker. Allowed classes are credentials, approval, external_outage, platform and product_decision. Installing/configuring available tooling is executable work. `unblock`, `reopen`, `pause`, `cancel`, and `resume` record explicit lifecycle. Supply JSON obligations at registration for dependencies or alternate proof policies. `reconcile --authority ... --reason ...` validates an intentional plan revision and requires fresh proof; it cannot silently preserve old completion across edits.

## Lifecycle handlers

UserPromptSubmit binds explicit execution requests and restores current goals on follow-ups. SessionStart restores context after startup/resume/compact. Pre/PostCompact report the persisted contract rather than treating transcript prose as authoritative. Stop invokes the shared completion evaluator. SubagentStart/Stop and tool observations track child lifecycle; Stop requires cleanup. PreToolUse checks assignment quotas and plan prerequisites on supported tool paths. PostToolUse observes actual spawn/close receipts. Interrupt records pause and cannot restart a user interruption.

An attempted premature Stop returns a scoped continuation prompt. Three unchanged continuation attempts are allowed; the next stops with `enforcement_failed` and unfinished obligations. Proof/lifecycle progress, not repeated narration, resets the retry state. The policy cannot override user cancellation, quota/runtime errors, disabled or untrusted hooks, runtime timeouts, or another hook's explicit stopping decision.

Install with `python3 scripts/mega_hooks_install.py --apply`. Inspect and trust the exact new definitions through native `/hooks`; the installer never modifies trusted hashes or disables other controls. `--status` checks installed entries; it does not prove trust. Uninstall removes only entries it owns and preserves unrelated subsequent changes. Restart/resume with the updated config, and run `mega_hook_canary.py` for protocol proof before a live runtime canary.

The six role TOMLs are shipped under `agents/roles/` and installed as `~/.codex/agents/megaskill-ROLE.toml`. The native `[agents].max_concurrent_threads_per_session = 3` cap complements the task registry and applies to new configurations/sessions; a paused older session is not proof its children are closed.
