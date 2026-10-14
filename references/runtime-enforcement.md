# Runtime completion enforcement

The canonical Markdown plan describes work. A versioned `.mega/tasks/TASK.json` contract captures exact task identity, mode, plan hash and acceptance obligations. Per-session bindings under `~/.codex/megaskill/sessions/` restore the original workspace after cwd changes. JSONL task events are append-only. Concurrent writes use file locks and atomic contract replacement.

## Execute a registered task

```sh
python3 scripts/mega_task.py register --id task-name --plan PLAN.md --goal "requested outcome" --session SESSION_ID
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind test --artifact src/changed.py -- python3 -m unittest
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind readback --artifact output.txt -- python3 scripts/assert_output.py
python3 scripts/mega_task.py done --id task-name --obligation 1.1 --proof TEST_EVENT_ID --proof READBACK_EVENT_ID
python3 scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task task-name --verdict done
```

Choose input/artifact files covering the relevant proof surface. Hashes detect changes to those files, not every possible unlisted dependency. A proof command must assert the desired result; a successful `true` or directory listing is insufficient semantic evidence. Manual/external attestations require explicit provenance and reviewer judgment. Agent-writable ledgers are a reliability mechanism, not protection against an adversarial agent.

`block --obligation ID --blocker-class credentials --attempted "attempt and observed result" --reason ... --evidence ... --resolution ...` scopes an external blocker. Allowed classes are credentials, approval, external_outage, platform and product_decision. Installing/configuring available tooling is executable work. `unblock`, `reopen`, `pause`, `cancel`, and `resume` record explicit lifecycle. Supply JSON obligations at registration for dependencies or alternate proof policies. `reconcile --authority ... --reason ...` validates an intentional plan revision and requires fresh proof; it cannot silently preserve old completion across edits.

## Lifecycle handlers

UserPromptSubmit binds explicit execution requests and restores current goals on follow-ups. SessionStart restores context after startup/resume/compact. Pre/PostCompact report the persisted contract rather than treating transcript prose as authoritative. Stop invokes the shared completion evaluator. SubagentStart/Stop and tool observations track child lifecycle; Stop requires cleanup. PreToolUse checks assignment quotas and plan prerequisites on supported tool paths. PostToolUse observes actual spawn/close receipts. Interrupt records pause and cannot restart a user interruption.

An attempted premature Stop returns a scoped continuation prompt. Three unchanged continuation attempts are allowed; the next stops with `enforcement_failed` and unfinished obligations. Proof/lifecycle progress, not repeated narration, resets the retry state. The policy cannot override user cancellation, quota/runtime errors, disabled or untrusted hooks, runtime timeouts, or another hook's explicit stopping decision.

Install with `python3 scripts/mega_hooks_install.py --apply`. Inspect and trust the exact new definitions through native `/hooks`; the installer never modifies trusted hashes or disables other controls. `--status` checks installed entries; it does not prove trust. Uninstall removes only entries it owns and preserves unrelated subsequent changes. Restart/resume with the updated config, and run `mega_hook_canary.py` for protocol proof before a live runtime canary.

The six role TOMLs are shipped under `agents/roles/` and installed as `~/.codex/agents/megaskill-ROLE.toml`. The native `[agents].max_concurrent_threads_per_session = 3` cap complements the task registry and applies to new configurations/sessions; a paused older session is not proof its children are closed.
