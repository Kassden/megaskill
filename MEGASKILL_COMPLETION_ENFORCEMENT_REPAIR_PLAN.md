# Megaskill Completion Gate Repair And Hook Enforcement Plan

Implementation update (2026-10-14): superseded for execution by `MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md`, which also includes ADRs and bounded agent lifecycle. Task contracts, current proof, hooks and reversible installation are implemented and undergoing independent verification; consult that plan and its evidence for runtime status rather than interpreting this proposal's unchecked historical checklist as current completion state.

## GOAL
- Make unfinished authorized Megaskill execution continue automatically, and permit a final handoff only when the requested outcome has current evidence, remaining work is externally blocked, or the user has stopped or narrowed the task.
- Deliver one reusable completion evaluator, persistent execution contracts, and tested Codex lifecycle adapters that invoke the evaluator independently of the agent remembering to do so.
- This document is a proposal. The current request authorizes writing and validating the plan; its implementation checklist remains pending.

## Acceptance Criteria
- [ ] Completion belongs to an exact task, plan revision, workspace, and subphase; unrelated or historical records cannot satisfy it.
- [ ] Subphase `1.10` cannot satisfy `1.1`; later invalidation overrides earlier success; zero recognized subphases cannot pass a whole-plan gate.
- [ ] Completion requires the latest explicit completion event plus successful linked verification and required fulfillment/readback evidence for the current relevant artifact state.
- [ ] Blockers have lifecycle, scope, evidence, and resolution requirements. One blocked branch does not stop independent executable work.
- [ ] A live Codex Stop hook demonstrably continues a deliberately incomplete task without a new human prompt and allows an actually complete task to finish.
- [ ] Planning, review, status queries, cancellations, and user interruptions retain their intended stopping behavior.
- [ ] Resume, compaction, cwd changes, and concurrent sessions preserve task identity and authorization boundaries.
- [ ] Subagents are checked against assigned obligations; the parent remains responsible for integration and final acceptance.
- [ ] Existing hooks remain intact. Installation, trust status, runtime support, failure behavior, and rollback are visible and tested.
- [ ] Repeated continuation without progress terminates with an explicit enforcement failure and unfinished-work report, never a fabricated success.
- [ ] The repair is linked to the ADR proposal through stop-decision records without requiring the entire ADR system first.

## Research
- Local evidence, refreshed 2026-10-06: `codex --version` reports `0.160.1`. User `hooks.json` has UserPromptSubmit and PreToolUse handlers, but no Stop handler. Other config/plugin layers still require inspection before rollout.
- Read `SKILL.md`, `references/execution-contract.md`, `references/final-handoff-template.md`, `scripts/mega_state.py`, `scripts/mega_evidence.py`, and `tests/test_mega_state.py` before implementation.
- Official source: [OpenAI Hooks documentation](https://learn.chatgpt.com/docs/hooks), fetched 2026-10-06. Stop blocking produces a continuation prompt; SubagentStop offers child continuation. SessionStart/UserPromptSubmit can inject context. PostCompact exists. Non-managed hooks require trust. Matching handlers run concurrently. Background handlers cannot enforce decisions. A matching `continue: false` overrides Stop continuation. Interrupt cannot be prevented or restarted by its hook. Transcript format is unstable. Tool coverage and failures need release-specific testing.
- Built-in options: synchronous local command hooks, the existing state/evidence commands, Python unittest, JSONL, atomic file replacement, and advisory file locks.
- Off-the-shelf options: use Codex's lifecycle mechanism before introducing a separate supervisor. A supervisor is a conditional fallback for unsupported clients, not the initial implementation.
- Unknown: actual hook loading, child event identity, compaction context delivery, final-message visibility, and error behavior in each installed client. Resolve these with canaries; do not extrapolate CLI results to app, IDE, or cloud clients.

## Root-Cause Baseline
- Trigger scope: recurring reports of early final handoff and partial fulfillment in Megaskill sessions.
- Evidence inventory: current instructions already require continuation and final-gate invocation. Source inspection shows the evaluator scans all records, matches normalized substrings, accepts any historical success, and does not reject an empty subphase parse. Blocker selection has no plan filter or lifecycle. Existing evidence records lack task IDs and artifact revision binding.
- Reproduced facts: an unrelated-plan `1.10` test satisfies `1.1`; an earlier success survives a later failed subphase event; zero parsed subphases passes `done`; an unrelated blocker permits a blocked whole-plan exit. Reproduce through actual CLI fixtures in Phase 1, not only mocked functions.
- Session evidence: `01a0c7dc-234a-7802-98a4-5877bf78a21f` later acknowledged recovery remained unfinished after observe-mode deployment. Review its full authorization and timeline before classifying a stop as wrongful. Do not label user interruptions, denied approval, or justified live-system boundaries as drop-offs.
- Proven failure classes: F1 identity leakage; F2 stale or overly broad completion; F3 vacuous plan acceptance; F4 stale/unrelated blocker acceptance; F5 voluntary gate invocation with no Stop entry in the inspected user file.
- Likely hypotheses: H1 compaction loses obligations; H2 subagent checkpoints are mistaken for parent completion; H3 deployment/monitoring evidence substitutes for the requested behavior. These need behavioral fixtures and session evidence.
- Missing-evidence policy: no population failure rate has been established; client hook coverage and the user's intended affected sessions remain uncertain. Keep audit labels factual, inferred, interrupted, blocked, or unclassifiable.
- Mutation boundary: this turn changes only this plan. Future implementation uses isolated fixtures and a dedicated branch before changing evaluators or runtime configuration. Live-system recovery is outside this plan.
- Remediation mapping: Phase 1 addresses F1-F4; Phase 2 addresses H1 and identity persistence; Phase 3 addresses F5/H2; Phase 4 addresses H3 and proof freshness; Phase 5 proves deployment and operational behavior.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: runtime lifecycle checks complement durable task state and independent outcome verification. Local explicit decisions provide predictable enforcement without adding another model call per hook.
- Official / standards sources: use the fetched official hook reference and refresh it against the installed release during implementation. Treat hook output as a typed protocol and validate it with fixtures.
- Mature libraries / built-in mechanisms: standard-library argparse/json/hashlib/unittest plus POSIX advisory locking on this macOS installation. Declare platform support and reject an unsupported writer platform explicitly.
- Best-practice constraints: small context packets, versioned contracts, exact identifiers, atomic writes, idempotent events, bounded retries, scoped permissions, and outcome readback.
- Rejected approaches: more emphatic prose alone; final-message keyword matching as the verdict; automatic deployment from a continuation prompt; blanket blocking of every stop; a new full workflow engine; claiming hooks are tamper-proof or universally fail-closed.
- Implementation decision: build one evaluator in `scripts/mega_completion.py`; both `mega_state.py final-gate` and `mega_hooks.py` call it. Keep scripts/skills and runtime installation distinct. Agent-writable evidence improves reliability but is not a security boundary against deliberate falsification.

## Completion Contract
- Store versioned task contracts at `.mega/tasks/<task_id>.json`, with schema version, task ID, goal, mode, workspace identity, canonical plan path, plan revision/hash, authorization references, acceptance obligations, proof policy, lifecycle, and assigned agent IDs.
- Modes: `plan`, `review`, `execute`, `monitor`. Whole-plan continuation applies to execute mode. A planning goal completes when its requested plan is validated; it does not authorize implementation.
- Store session-to-task bindings under `.mega/sessions/<session_id>.json`. Do not use one workspace-wide active pointer. For hook child events, key assignments with the available parent session ID and exact child agent ID.
- Give each acceptance obligation and subphase an explicit stable ID. Use legacy numeric IDs with exact equality during migration; titles and summaries are descriptive only.
- Bind state/evidence to task ID, plan revision, workspace, obligation/subphase ID, actor, and immutable event ID. Shared append operations use a lock and a sequence number; timestamps are informative rather than ordering authority.
- Completion is a latest explicit `subphase:done` transition supported by linked successful receipts. A later edit, failure, reopen, or proof invalidation resets affected obligations. `archived`, one passing test, and prose mentioning an ID do not imply completion.
- Plan edits require an explicit revision/reconciliation event. A hash mismatch stops completion evaluation until reconciled. Carry forward unchanged obligations only when their IDs, requirements, and relevant proof inputs are unchanged; acceptance reductions require user authority.
- Validate the plan structure through the shared parser. Reject missing, malformed, duplicate, and empty whole-plan subphase sets. Support an explicitly declared single-step task contract without pretending it is a parsed whole plan.
- Reuse `.mega/state.jsonl` and `.mega/evidence.jsonl`; retain legacy records for readback. A dry-run migration reports ambiguous records and never promotes them to verified completion automatically.
- Blocker records include ID, exact affected obligations, class, attempted alternatives, evidence IDs, external resolution condition, and open/resolved state. Latest state wins. Allow a blocked handoff only when every remaining required obligation is blocked or depends on blocked work and no authorized independent work is executable.
- Evaluator result: `complete`, `continue`, `blocked`, `paused`, `invalid`, or `enforcement_failed`, with unmet IDs, evidence diagnostics, next eligible action, and stop-decision ID. A budget/runtime failure cannot become `complete`.

## Hook Enforcement Design
- Activation: UserPromptSubmit identifies explicit Megaskill invocation and injects the registration command and contract requirements. The agent registers a concrete task/mode. An explicit execute request lacking a contract triggers a bounded registration continuation; ambiguous prompts inject context without guessing authority.
- Follow-up turns: persist the active task, but classify the current turn separately. Status/review-only questions can finish while leaving execution outstanding; clear stop/cancel/replace requests update lifecycle. Internal continuation prompts retain the original mode and authorization. Test topic changes and quoted skill names to prevent accidental activation.
- Stop: resolve the exact session/task binding, evaluate the current contract, and write an idempotent stop-decision state event. Complete/externally blocked/user-paused tasks permit handoff; executable unfinished work produces a continuation reason naming unmet obligations and the next permitted step.
- Proposed Stop response for unfinished work, encoded as one JSON object and exit 0:

```json
{"decision":"block","reason":"Megaskill task TASK_ID is unfinished. Obligation O2 lacks current readback evidence. Continue subphase 2.1 within the existing authorization and rerun the completion evaluator."}
```

- SessionStart restores a short contract summary on startup/resume/compact. PostCompact validates the binding and snapshot; select a documented context-delivery mechanism only after testing it on this release. If PostCompact cannot inject the required context, use SessionStart compact or a verified PreToolUse adapter.
- SubagentStart injects assigned scope and proof obligations. SubagentStop evaluates only the assignment. Unknown/unassigned children remain informational; parent acceptance still requires validated integration evidence.
- Interrupt records interruption when feasible and leaves work resumable. It never auto-restarts a user-cancelled task.
- PreToolUse initially guards supported, clearly identified mutation operations for an active execute task missing its validated plan/root-cause prerequisites. Permit reads, diagnostics, registration, and evidence-preserving work. Inventory actual Bash/apply_patch/MCP/code-mode coverage before advertising protection. Arbitrary shell mutation classification is not a complete security mechanism.
- PostToolUse can invalidate affected evidence and observe results where structured coverage is proven. Required verification receipts come from `mega_evidence.py run`; absence of a reliably structured exit status must not manufacture success.
- Enforcement handlers are synchronous, local, network-free, with a target execution time under one second on normal fixtures and a five-second timeout. Stdout contains only protocol output; diagnostics are redacted and written separately.
- `stop_hook_active` is a loop signal, not an unconditional bypass. Track retries across automatic continuation turns using task ID and a progress fingerprint, because turn IDs can change. Reset the stall count only for meaningful verified obligation progress or resolution of a prerequisite.
- Default stall policy: after three unchanged continuation attempts, record `enforcement_failed`, unmet obligations, attempted repairs, and resolution requirements; emit an explicit stop with that failure reason. This bounds wasted quota while preserving the distinction between failure and success. User budget/cancellation takes precedence.
- Recoverable evaluator errors on active tasks produce a bounded repair continuation. A hook that cannot start, is disabled/untrusted, times out, or emits unusable output may be ignored by the runtime: treat detection of these cases as deployment failure, not successful enforcement. Test precedence against other handlers that stop processing.
- Do not claim the hook can erase a final message already displayed. The behavioral guarantee to prove is continued execution after an attempted premature stop; evaluate what each client shows.

## ADR Integration
- Record stop decisions initially as `handoff` state events with structured metadata: task/plan revision, unmet obligations, verdict, why, evidence IDs, next action, authority reference, and what would change the verdict.
- Required decisions: scope reduction, blocker acceptance, pause, enforcement failure, and final completion. Record a recommendation to deploy separately from authority to deploy.
- Update `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md` during implementation to consume these IDs and promote durable policy choices into ADRs. Completion enforcement must work before the future decision-ledger CLI exists.

## Dependency and Tooling Preflight
- Required verification tools: Python 3 standard library, Git, installed Codex CLI, supported local hooks, and an isolated disposable workspace/session.
- Existing tooling found: Codex 0.160.1, state/evidence/plan/scope/commit/dashboard scripts, unittest suite, and existing user hooks.
- Install or repair: no install is needed for the plan or fixture tests. Resolve a missing supported Codex runtime through the normal installation mechanism before runtime canaries; do not disable trust or approval controls.
- Browser/runtime binaries: no browser UI is changed. CLI canaries are the deterministic real-user test. App/IDE claims require their own lifecycle canaries if included in rollout.
- Real blockers: unavailable supported runtime, trust review not granted, account/runtime outage, or a required client lacking hook support. Record these per surface rather than calling the whole deployment done.

## Deterministic Real-User Test
- Entry point: an isolated Codex execute session with a two-obligation fixture task and the proposed trusted hook adapter.
- User workflow: ask once for both artifacts and readbacks; deliberately complete only the first obligation and attempt a final. Observe Stop continuation, completion of the second, and an allowed final with verified contents.
- Stable inputs: temp workspace, fixed artifact text, exact task/subphase IDs, deterministic evaluator inputs, bounded runtime budget, and redacted lifecycle receipts.
- User-observable assertions: both files contain the required content without a second human prompt; a genuinely blocked fixture reports its blocker; a planning fixture produces only its plan; cancellation does not resume work.
- Commands after implementation: `python3 -m unittest discover -s tests -p 'test_*.py'`; `python3 scripts/mega_hook_canary.py --help`; `python3 scripts/mega_hook_canary.py --execute --workspace <isolated-path>`.
- Evidence: hook request/output receipts, task-state transitions, continuation count, final evaluator verdict, and file readback. Real model execution is behavioral evidence, not a perfectly deterministic test; fixture replay is the repeatable protocol proof.

## Fulfillment and Readback Proof
- Requested final user-visible result this turn: this complete canonical Markdown repair proposal.
- Required write/mutation operation this turn: add this document and validate it. Future runtime changes are the implementation deliverable, not delivered by this document.
- Readback surface: plan text, `mega_plan_check.py`, scoped Git diff. Future fulfillment: evaluator JSON, trusted hook invocation receipts, actual continuation and final artifact readbacks.
- Not-done conditions: configuration exists without runtime invocation; premature-stop fixture stalls; unrelated sessions are forced to continue; recovery/monitoring is substituted for required behavior; missing evidence passes completion.

## Armageddon Mode
- Attack scope: systemic runtime workflow behavior, tested in disposable sessions before broader rollout.
- Edge cases: `1.1`/`1.10`, cross-plan records, same plan path in different worktrees, reused task IDs, duplicate sequence/event IDs, partial JSONL lines, concurrency, zero subphases, stale proof, later failure, obsolete blockers, and revised acceptance criteria.
- Failure modes: missing/untrusted hook, timeout, malformed output, competing stop handler, code-mode nested tools, subagent identity collisions, cwd changes, compaction, resume, topic changes, interrupted task, and unchanged continuation loops.
- Optimization opportunities: bounded reads or indexed snapshots only if measurements justify them; avoid scanning session histories or spawning a model from a hook.
- Must-fix threshold: false completion, scope/authorization expansion, swallowed cancellation, uncontrolled quota consumption, damaged existing hooks, or deployment claims without lifecycle receipts.
- Evidence: targeted fixture outputs, full regression results, live canary transcript excerpts, latency and stall counts, rollback readback.

## Generality Guardrail
- Existing mechanism: state/evidence ledgers, plan checker/parser, dashboard, and final-gate CLI.
- General mechanism: one completion evaluator and one Codex hook adapter serving all Megaskill tasks, with explicit assignment and mode support.
- Recurrence: high across projects and agents. No project-specific stop script or watchdog-specific acceptance heuristic.
- One-off justification: disposable runtime canary fixtures are intentionally isolated test inputs.

## Ordered State and Dashboard
- Implementation state/evidence paths: `.mega/state.jsonl`, `.mega/evidence.jsonl`, linked to this plan's implementation task ID.
- Dashboard: `.mega/dashboards/completion-enforcement-plan.html`, generated from the canonical plan and ledgers. Generate/read back during implementation; use `--no-open` unless opening is requested.
- Display unmet obligations, active blockers, coverage by client, and enforcement failure; never show configuration presence as verified enforcement.

## Regression Guardrails
- Planned edit surface this turn: `MEGASKILL_COMPLETION_ENFORCEMENT_REPAIR_PLAN.md` only.
- Planned implementation surface: files listed in subphases below; optional live user-hook installation is a separate explicit rollout operation.
- Protected behaviors: existing root-cause baseline, evidence readback, atomic commits, user approvals, unrelated hooks, planning/review-only requests, and interruption.
- Likely consumers: Megaskill CLI scripts, dashboard, parent/child agents, and supported local Codex clients.
- Damage radius: systemic for implementation; small for this proposal document.
- Branch strategy: retain the existing `megaskill/root-cause-gate` branch for this plan-only change. Create `megaskill/completion-enforcement` before implementation; preserve the existing unpushed ADR-plan commit and unrelated user work.
- Proof plan: targeted regressions, CLI fixture readback, full suite, isolated runtime canaries, compatibility report, and rollback rehearsal.
- Execution rule: after implementation is requested, execute checked dependencies continuously without asking for approval at each phase. Real user authority, hook trust, and platform limits still apply.

## Phase 1: Repair completion semantics

### Subphase 1.1: Close the reproduced final-gate defects
- Commit: `fix(megaskill): scope final gate and reject stale completion`
- Tests: `python3 -m unittest discover -s tests -p 'test_mega_state.py'`; actual CLI fixtures for all five reproduced failures and valid controls.
- Success Criteria: exact plan/workspace/subphase matching, latest explicit state, nonempty valid plan structure, and scoped unresolved blockers determine the result.
- Planned Touch Files: `scripts/mega_state.py`, `scripts/mega_completion.py`, `tests/test_mega_state.py`, `tests/fixtures/completion/`.
- Checklist:
  - [ ] Add failing regressions before changing the evaluator.
  - [ ] Replace substring/history scanning with exact scoped evaluation; make final-gate delegate to the shared evaluator.
  - [ ] Prove unrelated records, later failure, and empty parsing cannot pass; preserve valid CLI behavior where proof requirements are satisfied.

## Phase 2: Persist contracts and proof identity

### Subphase 2.1: Register tasks and durable assignments
- Commit: `feat(megaskill): persist task contracts and session bindings`
- Tests: new `tests/test_mega_task.py`; concurrency, wrong cwd/worktree, mode, revision, assignment, and migration fixtures.
- Success Criteria: independent sessions and subagents resolve only their registered contracts; legacy records remain readable without implicit completion promotion.
- Planned Touch Files: `scripts/mega_task.py`, `scripts/mega_completion.py`, `scripts/mega_state.py`, `tests/test_mega_task.py`, `tests/fixtures/completion/`.
- Checklist:
  - [ ] Implement register/show/bind/reconcile/pause/cancel operations and schema validation with explicit authority references.
  - [ ] Use shared locking/atomic-write functions; add sequence and identity fields without rewriting historical ledgers.
  - [ ] Produce dry-run migration output and prove ambiguity cannot silently assign evidence.

### Subphase 2.2: Require current verification and blocker coverage
- Commit: `feat(megaskill): bind completion to outcome evidence`
- Tests: new `tests/test_mega_completion.py`; existing evidence tests; failed/stale/missing receipts, partial blockers, dependency graph, and fulfillment fixtures.
- Success Criteria: the evaluator rejects self-declared done without current linked proof and continues any unblocked required branch.
- Planned Touch Files: `scripts/mega_completion.py`, `scripts/mega_evidence.py`, `scripts/mega_state.py`, `tests/test_mega_completion.py`, `tests/test_mega_evidence.py`, `tests/fixtures/completion/`.
- Checklist:
  - [ ] Add evidence IDs, task/revision identity, artifact or relevant-input hashes, and receipt provenance to evidence run/record paths.
  - [ ] Let `record` import manual/external readbacks with declared provenance; do not treat imports as independently observed execution.
  - [ ] Check acceptance obligation coverage, invalidation, blocker lifecycle, and dependency-aware next actions.

## Phase 3: Enforce lifecycle decisions

### Subphase 3.1: Build the synchronous hook adapter
- Commit: `feat(megaskill): enforce completion through Codex hooks`
- Tests: new `tests/test_mega_hooks.py`; replay event fixtures for activation, Stop, children, resume, compaction, and interruption.
- Success Criteria: every adapter verdict derives from the shared evaluator; unrelated tasks pass through; unfinished execution receives a scoped continuation.
- Planned Touch Files: `scripts/mega_hooks.py`, `scripts/mega_completion.py`, `hooks/megaskill-hooks.json`, `tests/test_mega_hooks.py`, `tests/fixtures/hooks/`.
- Checklist:
  - [ ] Implement task activation/binding, concise restoration, Stop/SubagentStop, interruption, and supported mutation-prerequisite checks.
  - [ ] Record structured stop decisions and test exact protocol stdout/exit behavior, including code-mode coverage where available.
  - [ ] Keep hooks network-free and prove bounded latency and idempotency.

### Subphase 3.2: Bound failure loops and preserve user control
- Commit: `fix(megaskill): bound continuation and honor task lifecycle`
- Tests: repeated continuation across turn IDs, internal-prompt classification, status-only turns, user pause/cancel, evaluator errors, and conflicting hook output.
- Success Criteria: three unchanged attempts produce explicit enforcement failure; progress permits continued work; user interruption and task replacement are respected.
- Planned Touch Files: `scripts/mega_hooks.py`, `scripts/mega_task.py`, `tests/test_mega_hooks.py`, `tests/test_mega_task.py`, `tests/fixtures/hooks/`.
- Checklist:
  - [ ] Persist progress fingerprints and retry accounting with concurrency-safe updates.
  - [ ] Handle malformed active state through bounded repair; distinguish invalid configuration from external task blockers.
  - [ ] Verify no automatic continuation expands the original authorization or treats a user status question as cancellation.

## Phase 4: Align workflow documentation and decision awareness

### Subphase 4.1: Integrate plans, dashboard, and ADR links
- Commit: `docs(megaskill): integrate enforced completion and stop decisions`
- Tests: plan-check fixtures, plan-init tests, dashboard tests, and full unittest discovery.
- Success Criteria: generated plans declare task mode and proof obligations; dashboard/handoff report actual enforcement and outcome evidence; ADR proposal consumes stop-decision IDs.
- Planned Touch Files: `SKILL.md`, `README.md`, `references/execution-contract.md`, `references/agent-plan-template.md`, `references/final-handoff-template.md`, `scripts/mega_plan_init.py`, `scripts/mega_plan_check.py`, `scripts/mega_plan_dashboard.py`, `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`, affected existing tests.
- Checklist:
  - [ ] Explain plan-only versus execute modes and the required registration/readback sequence.
  - [ ] Integrate obligation validation without duplicating parsers or maintaining a parallel dashboard plan.
  - [ ] Document stop-decision schema and the limits of hooks and agent-writable evidence.

## Phase 5: Install, prove, and roll out

### Subphase 5.1: Ship reversible hook installation and live canaries
- Commit: `feat(megaskill): add hook installation and runtime canaries`
- Tests: new installer/canary fixture tests; help/invalid-input/idempotency checks; isolated live premature-stop, completion, blocker, cancellation, and rollback sessions.
- Success Criteria: trusted hooks actually fire on the tested client; incomplete work continues; completed work stops; uninstall restores owned configuration changes without erasing other handlers.
- Planned Touch Files: `scripts/mega_hooks_install.py`, `scripts/mega_hook_canary.py`, `tests/test_mega_hooks_install.py`, `tests/test_mega_hook_canary.py`, `hooks/megaskill-hooks.json`, `README.md`.
- Checklist:
  - [ ] Implement dry-run installation by default; explicit apply merges only owned handlers and records a recoverable backup and ownership manifest. Uninstall removes owned entries without overwriting subsequent unrelated changes.
  - [ ] Inventory all active hook sources and precedence, check feature/trust status, and prepare exact configuration for review. Never use trust-bypass flags as normal setup.
  - [ ] Run isolated runtime canaries after the exact definition is trusted; record runtime version, receipts, final-message visibility, artifacts, continuation/stall counts, and compatibility by client.
  - [ ] Start with one canary workspace, then enable for registered Megaskill execution tasks. Global installation remains opt-in; this plan request does not itself change user config.
  - [ ] Rehearse rollback; rerun scoped/full checks; record fulfillment proof and final-gate verdict for the implementation task; commit/push only when in the authorized delivery scope.

## Final Success Criteria
- Repair is done only when semantic regressions and runtime canaries pass, the requested supported installation is trusted and verified, and outcome readback proves autonomous continuation and correct stopping.
- If runtime trust/support prevents installation, report the precise blocked surface and deliver tested local artifacts with deployment still pending.
- Proposal delivery is done when this document is written, read back, and passes plan validation. No unchecked implementation item is claimed complete in this turn.
