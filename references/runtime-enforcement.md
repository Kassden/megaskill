# Explicit outcome verification and optional observation

Keyword-derived review locks were removed on 2026-10-26 because they blocked
legitimate work and their own repair. The user then clarified that completion
retries should remain, with a direct user-controlled unlock. Stored modes and
historical authority records are metadata, not current system/developer/user
permissions. The separate permission resolver and blanket role ceilings remain
removed.

## Verify the actual outcome

Keep using the canonical plan, exact obligations, fresh test/readback proof and
independent review when warranted. These are explicit work-quality tools:

```sh
python3 scripts/mega_task.py register --id task-name --plan PLAN.md --goal "requested outcome" --session SESSION_ID --acceptance ACCEPTANCE.json
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind test --artifact src/changed.py -- python3 -m unittest
python3 scripts/mega_task.py prove --id task-name --obligation 1.1 --kind readback --artifact output.txt -- python3 scripts/assert_output.py
python3 scripts/mega_task.py done --id task-name --obligation 1.1 --proof TEST_EVENT_ID --proof READBACK_EVENT_ID
python3 scripts/mega_task.py evaluate --id task-name
python3 scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task task-name --verdict done
```

`ACCEPTANCE.json` maps each obligation to actual `text`, `json` or `review`
assertions. Exact text/JSON outcomes and input hashes prevent proxy proofs from
certifying the wrong result. Independent reviews retain reviewer identity,
substantive rationale, current source hashes and the actual native reviewer result.
Presence or keywords alone do not establish quality. Existing CLI validation,
proof freshness, task identity and child-closure checks remain available.

`acceptance --id TASK --file ACCEPTANCE.json --authority "USER REQUEST" --reason
"WHY"` explicitly revises acceptance and invalidates old done receipts. `reconcile`
updates an intentionally changed plan. `authorize` records explicit durable task
intent; it does not change host permissions. Preserve the original unfinished
goal unless the user explicitly changes it.

## No automatic permission system

`mega_hooks.py` separates scheduling from permissions. It never denies a tool,
injects review-only prohibitions, or assigns role permission ceilings. It records
native observations and evaluates registered execution outcomes at Stop. Unmet
authorized work receives a continuation with the original goal and next obligation.

Direct `continue`, `execute`, `resume`, `implement`, `keep going`, `unlock`, or
`remove the restriction` clears Megaskill's own legacy review/pause/conflict flags
and resets stalled retry counters for the same task. A short resume notice
explicitly expires older Megaskill review/status hints. It does not override
other controlling instructions, host permissions, plan hashes or outcome proof.
Direct resumption can promote a planning task's intent and reactivate its lifecycle;
it cannot silently certify a changed plan or fabricate acceptance.

Direct review, pause/cancel, status checkpoints and Interrupt suppress automatic
completion retries. They do not restrict tool permissions. Quoted failure text
does not become a scheduling command; child prompts cannot pause their parent.
Synthetic continuation prompts inherit their originating pause/resume state.
Native plan mode suppresses automatic implementation retries.

Fresh successful proof resets stall detection. Repeated proof UUIDs for the same
artifacts do not count as progress. The third unchanged attempt requests root-cause
diagnosis and independent review; another unchanged Stop yields a clear unfinished
notice. An explicit continue/execute always restarts this soft retry budget. No
permanent edit lock or special approval phrase is created.

Install only under the user's requested completion-loop scope, using the
ownership-aware installer. Keep user-disabled hook settings and native trust intact.
Native approval, sandbox, managed policy and trust settings are separate and
remain controlling. Do not modify those controls to work around a restriction.

When hooks are enabled, `mega_task.py runtime` reports native event coverage.
Configuration presence alone does not prove the current host invokes them. Ordinary final
verification does not require hook receipts. `final-gate --require-native-runtime`
adds that diagnostic requirement only when specifically wanted. The disposable
`mega_hook_canary.py` checks review -> direct resume -> synthetic continuation,
actual outcome rejection/completion and absence of tool denials in isolated state.

Reviewers should identify scope drift and missed outcomes using evidence.
Return findings to the parent, continue independent authorized work and close
owned agents after collecting results. A role name does not create a permission
ceiling, and a review finding must not lock unrelated tasks or sessions.
