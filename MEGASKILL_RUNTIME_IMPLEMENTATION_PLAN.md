# Megaskill Runtime, Decisions, And Delegation Implementation

## GOAL
- Implement and install task-scoped completion hooks, decision records and ADRs, and bounded subagent dispatch with actual close receipts.

## Acceptance Criteria
- Completion cannot leak across plans or IDs, use stale proof, or accept an unrelated blocker.
- Installed lifecycle handlers continue executable work and preserve user interruption and planning-only tasks.
- Decision CLI validates self-critique and promotes durable decisions into Markdown ADRs.
- Role delegation has scoped assignments, bounded concurrency, independent verification, and explicit close-before-handoff.
- All fixture tests pass; runtime canary proves supported behavior or identifies an exact runtime/trust blocker.

## Research
- Built-in options: existing Python state/evidence scripts and Codex 0.162.1 lifecycle hooks and close_agent tool.
- Off-the-shelf options: manager-led bounded delegation rather than a second agent framework.
- Official sources: https://learn.chatgpt.com/docs/hooks and https://learn.chatgpt.com/docs/agent-configuration/subagents, refreshed during this run; role names are our operating convention, not a claimed universal SOTA standard.

## Root-Cause Baseline
- Evidence inventory: config/state readback shows the existing checker uses substring matching and all-plan historical records; inspected user hooks lacked Stop; PCB transcript records checkpoint stopping and engineering/release blocker confusion.
- Proven causes: completion identity and lifecycle defects; voluntary invocation. Likely hypotheses: compaction drift and unmanaged completed children.
- Missing evidence: real event coverage and exact trust semantics on installed runtime require canaries; session histories cannot prove current live agent status.
- Mutation boundary: dedicated branch; reversible local changes; preserve hook entries and unrelated sessions.
- Remediation mapping: shared completion evaluator fixes identity/proof; Stop invokes it; role registry and native close receipts address orphaned children; ADR records explain choices.

## SOTA, Standards, And Best Practices
- Prior art: manager coordination, scoped parallel work, independent verification, lifecycle cleanup, and durable decision rationale.
- Official platform guidance: typed synchronous hook protocol, trust review, child lifecycle and actual close tools.
- Mature libraries: Python standard library JSON, locks, atomic replacement, argparse, unittest.
- Rejected approaches: prose-only enforcement, always-spawn-six, recursive fan-out, evidence from final prose, and falsely marking stopped children closed.
- Implementation decision: shared completion evaluator plus task/decision/agent CLIs; small bounded role pool.

## Dependency and Tooling Preflight
- Required tools: Python, Git, installed Codex, isolated runtime workspace.
- Existing tools found: 38 passing tests and Codex 0.162.1; browser smoke tooling will be checked for dashboard changes.
- Install or repair: no install is needed for fixture tests; inspect runtime trust through native config/UI.
- Real blockers: denied trust, credentials, unsupported hook surface or runtime outage.

## Deterministic Real-User Test
- Entry point: CLI registration -> proof run -> Stop fixture -> readback.
- Stable fixtures: two-subphase plan, exact IDs, artifact hashes, real close receipts.
- User-observable assertions: unfinished work continues; all proved work stops; unrelated sessions pass; child cleanup is demanded until actual closure.
- Command: python3 -m unittest discover -s tests -p 'test_*.py'; browser smoke for changed dashboard behavior.

## Fulfillment and Readback Proof
- Required mutation: implement scripts, install owned hook entries preserving existing entries, write ADRs.
- Readback surface: CLI output, hooks.json, runtime lifecycle receipts and native close result.
- Expected behavior: no false success, no unauthorized scope extension, no invented cleanup.
- Not-done conditions: installation without trust/invocation, failed checks, missing outcome proof.

## Armageddon Mode
- Attack scope: task identity, stale evidence, resolved blockers, malformed events, concurrency and continuation loops.
- Edge cases: wrong cwd, quoted invocation, cancellation, task replacement, child completion vs closure, counter overflow, unknown runtime.
- Must-fix: false completion, runaway continuation, replacing other hooks, or closing unrelated sessions.

## Generality Guardrail
- Existing mechanism: state/evidence ledgers and final gate.
- General mechanism: reuse shared storage and evaluator across CLI and hooks; role catalog applies across projects.
- Recurrence: high; no PCB-specific heuristic.

## Regression Guardrails
- Damage radius: systemic.
- Branch strategy: separate branch megaskill/completion-enforcement.
- Planned edit surface: scripts/, tests/, references/, hooks/, evals/, docs/adr/, SKILL.md, README.md, agent-plan-template, previous proposal plans, and this plan. User hooks.json owned additions only for installation.
- Protected behaviors: approvals, existing hooks, root-cause gate, plan-only behavior, unrelated sessions.
- Proof plan: targeted/full tests, CLI smoke, independent verifier and runtime canary; browser smoke for any dashboard behavior changes.
- Planned touch files:
  - `.gitignore`
  - `MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md`
  - `MEGASKILL_COMPLETION_ENFORCEMENT_REPAIR_PLAN.md`
  - `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`
  - `README.md`
  - `SKILL.md`
  - `scripts/mega_store.py`
  - `scripts/mega_task.py`
  - `scripts/mega_completion.py`
  - `scripts/mega_state.py`
  - `scripts/mega_decision.py`
  - `scripts/mega_agents.py`
  - `scripts/mega_hooks.py`
  - `scripts/mega_hooks_install.py`
  - `scripts/mega_hook_canary.py`
  - `scripts/mega_plan_check.py`
  - `scripts/mega_plan_dashboard.py`
  - `scripts/mega_plan_init.py`
  - `tests/test_completion_runtime.py`
  - `tests/test_mega_state.py`
  - `tests/test_mega_decision.py`
  - `tests/test_mega_agents.py`
  - `tests/test_mega_hooks.py`
  - `tests/test_mega_hooks_install.py`
  - `tests/test_mega_hook_canary.py`
  - `tests/test_plan_dashboard.py`
  - `references/runtime-enforcement.md`
  - `references/decision-records.md`
  - `references/subagent-dispatch.md`
  - `references/agent-plan-template.md`
  - `references/final-handoff-template.md`
  - `hooks/megaskill-hooks.json`
  - `evals/evals.json`
  - `docs/adr/ADR-001-completion-enforcement.md`
  - `docs/adr/ADR-002-bounded-delegation.md`
  - `agents/roles/thinker.toml`
  - `agents/roles/planner.toml`
  - `agents/roles/executor.toml`
  - `agents/roles/tester.toml`
  - `agents/roles/verifier.toml`
  - `agents/roles/orchestrator.toml`

## Phase 1: Core execution
### Subphase 1.1: Task contracts and completion repair
- Commit: fix(megaskill): enforce scoped current completion proof
- Tests: legacy tests plus identity/stale evidence fixtures.
- Success Criteria: shared evaluator enforces scoped explicit completion and outcomes.
- Planned Touch Files: scripts/mega_store.py, scripts/mega_task.py, scripts/mega_completion.py, scripts/mega_state.py, scripts/mega_evidence.py, tests/test_completion_runtime.py.
- Checklist:
  - [x] Implement contracts, lifecycle, proof and scoped blockers.
  - [x] Repair legacy gate and test old behavior intentionally retained.

## Phase 2: Decisions and delegation
### Subphase 2.1: Decision records and ADRs
- Commit: feat(megaskill): add decision records and ADR promotion
- Tests: decision validation, supersession, CLI readback.
- Success Criteria: rationale, alternatives, self-critique and decision lifecycle are usable.
- Planned Touch Files: scripts/mega_decision.py, tests/test_mega_decision.py, references/decision-records.md, docs/adr/.
- Checklist:
  - [x] Implement decision CLI and linked records.
  - [x] Document and record durable policy ADRs.
### Subphase 2.2: Bounded role dispatch and cleanup
- Commit: feat(megaskill): track role assignments and actual agent closure
- Tests: ownership, quota, assignment, completion and close receipt fixtures.
- Success Criteria: completed children still require native close; concurrency bounded; unknown agents never auto-closed.
- Planned Touch Files: scripts/mega_agents.py, tests/test_mega_agents.py, references/subagent-dispatch.md.
- Checklist:
  - [x] Implement registry, scoped assignments and cleanup commands.
  - [x] Use actual native close tool for this task's children.

## Phase 3: Runtime deployment
### Subphase 3.1: Hooks, installation and integration
- Commit: feat(megaskill): install lifecycle completion enforcement
- Tests: protocol, merging/rollback, loop control, runtime canary.
- Success Criteria: owned hooks installed; exact runtime support/trust status verified.
- Planned Touch Files: scripts/mega_hooks.py, scripts/mega_hooks_install.py, scripts/mega_hook_canary.py, hooks/megaskill-hooks.json, tests/test_mega_hooks.py, tests/test_mega_hooks_install.py, SKILL.md, README.md, references/, scripts/mega_plan_dashboard.py, scripts/mega_plan_init.py, scripts/mega_plan_check.py, previous proposal plans, evals/.
- Checklist:
  - [x] Implement and test adapters, install reversibly and check trust.
  - [x] Integrate workflow and dashboard, run realistic canaries and independent review.
  - [x] Close owned agents and read back the empty cleanup registry; final proof/gate and delivery are recorded below.

## Delivery Evidence
- Native Codex 0.162.1 lifecycle canaries: actual live-canary session receipts show premature-stop continuation and subsequent complete verdict; both files contain exact requested bytes. Protocol replay records are excluded from live proof.
- Independent verifier cleared the reproduced identity, cancellation, corruption, stale proof, blocker, mode and parent-ownership cases after fixes. All five children created for this task were closed through native tools; registry cleanup is empty.
- Dashboard browser readback shows ADRs, runtime acceptance and child lifecycle; desktop/mobile geometry has no document overflow after table containment fix.
- User hook file has ten owned synchronous definitions; exact definitions were reviewed/trusted through native UI. Six role profiles match shipped templates, and native concurrent-thread cap is three. Unrelated hook enabled states are preserved.
- Final contract evidence, verification outputs and gate results are in `.mega/tasks/runtime-repair.events.jsonl`, `.mega/evidence.jsonl`, and `.mega/receipts/`. Local-only runtime coverage is proven; existing sessions may need resume/restart to load the new configuration.
