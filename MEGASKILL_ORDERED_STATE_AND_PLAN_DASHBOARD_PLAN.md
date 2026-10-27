# Megaskill Ordered State And Plan Dashboard Implementation Plan

## GOAL
- Add a reusable Megaskill mechanism that captures execution state in order, links that state to verification evidence and atomic commits, generates a canonical HTML plan dashboard with phase/regression/damage-radius/readback status, and optionally opens that dashboard in the default browser during interactive plan generation.

## Acceptance Criteria
- [ ] Megaskill has a documented ordered state contract that prevents unstructured or out-of-order handoff notes from becoming the source of truth.
- [ ] `scripts/mega_state.py` can initialize, append, inspect, and validate append-only execution state records in `.mega/state.jsonl`.
- [ ] `scripts/mega_evidence.py` can optionally link evidence records to state event IDs without breaking existing evidence consumers.
- [ ] `scripts/mega_plan_dashboard.py` generates a self-contained HTML dashboard from a canonical Markdown plan plus `.mega/state.jsonl` and `.mega/evidence.jsonl`.
- [ ] Generated dashboards include source-of-truth cards, objective, acceptance criteria, phases/subphases, damage radius, branch strategy, proof plan, deterministic real-user test, Armageddon mode, generality guardrail, fulfillment/readback status, evidence summary, commit/archive status, and explicit blockers.
- [ ] Interactive plan creation can generate and open the dashboard by default, while CI and noninteractive use can disable opening with `--no-open`.
- [ ] Existing plan validation, evidence recording, scope checking, commit checking, and tests continue to pass.
- [ ] The implementation is split into atomic commits matching the subphases below.

## Research
- Built-in options: Reuse Megaskill's current Markdown plan template, `mega_plan_init.py`, `mega_plan_check.py`, `mega_evidence.py`, `mega_scope_check.py`, and `mega_commit_check.py` rather than adding a separate planning product.
- Off-the-shelf options: Jujutsu operation log for ordered repository operation snapshots; OpenTelemetry trace/span/event semantics for ordered event modeling; Graphite/stacked PR flows for atomic reviewable work units; Changesets for small append-only change intent artifacts that roll up into human-readable release state.
- Official / standards sources: Jujutsu operation log docs and glossary, OpenTelemetry trace API and semantic convention docs, Graphite quick-start/docs for stacked changes, Changesets guide for append-only release intent.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: Use append-only, immutable event streams for auditability; use trace-like IDs to correlate plan phases, work events, command evidence, and commits; use generated dashboards as views over canonical state instead of manually maintained dashboards; use stacked/atomic commits for reviewability.
- Official docs, standards, specs, or platform guidance: OpenTelemetry distinguishes traces/spans/events and uses trace/span context for correlation; Jujutsu records operations and snapshots so prior states can be inspected; Graphite treats stacked changes as a navigable sequence; Changesets uses small Markdown records to produce release summaries.
- Mature libraries, frameworks, or built-in mechanisms: Use Python standard library only for the core CLI, JSONL parsing, Markdown heading extraction, HTML escaping, `webbrowser`, and subprocess/browser-open behavior. Avoid mandatory third-party dependencies for the skill runtime. Use Playwright only in tests that verify generated HTML rendering, and install it project-locally if absent.
- Best-practice constraints to integrate: State must be append-only; each event must include stable IDs, timestamp, cwd, plan path, phase/subphase, event kind, status, damage radius when relevant, branch when relevant, and parent/related IDs when available. Dashboard must be generated from canonical inputs and must not become a second editable source of truth. Browser opening must be opt-out and safe for CI. Tests must prove deterministic content and no-open behavior.
- Rejected approaches: Do not hand-author one HTML dashboard per project; it will drift. Do not add a database; local skill state should remain portable. Do not replace `mega_evidence.py`; verification evidence already has a general owner. Do not hard-code the BESS dashboard structure; use it as an interaction reference only.
- Implementation decision: Add a general ordered state ledger plus dashboard renderer to Megaskill, wire plan generation into that pipeline, and keep Markdown plan, state JSONL, evidence JSONL, and generated HTML as distinct canonical layers.

## Dependency and Tooling Preflight
- Required verification tools: Python 3, pytest, the existing Megaskill scripts, Git, and Playwright/browser smoke for generated HTML because the dashboard is a browser-facing artifact.
- Existing tooling found: Megaskill already has `scripts/mega_plan_init.py`, `scripts/mega_plan_check.py`, `scripts/mega_evidence.py`, `scripts/mega_scope_check.py`, `scripts/mega_commit_check.py`, and pytest tests under `tests/`.
- Install or repair commands: Run `python3 -m pytest`; if pytest is missing, install it in the current project-local Python environment. For dashboard render smoke, use an existing Playwright package if present; otherwise install a local browser-test dependency or use the Python Playwright package plus `python3 -m playwright install chromium` if allowed by the environment.
- Browser/runtime binaries: Chromium or the platform browser used by Playwright for generated HTML smoke. The open-in-default-browser command must be tested with a mock/stub path and `--no-open` so CI does not launch a real browser.
- Real blockers that would prevent setup: denied package/browser install approval, incompatible platform, external registry outage, or policy blocking browser launch automation. If blocked, implementation must still include deterministic no-open tests and record the browser setup blocker.

## Deterministic Real-User Test
- Entry point: `scripts/mega_plan_init.py "Example Dashboard Plan" --goal "Verify dashboard generation" --output .tmp/example-plan.md --dashboard .tmp/example-plan.html --no-open`.
- User workflow: A lower-level agent creates a plan, records ordered state for plan/subphase/evidence/readback events, generates the dashboard, opens or suppresses browser launch depending on flags, and reads the dashboard to understand the current execution state.
- Stable inputs or fixtures: A fixture Markdown plan with SOTA, dependency preflight, deterministic UX test, fulfillment proof, Armageddon mode, generality guardrail, regression guardrails, phases, subphases, and planned touch files; deterministic state/evidence JSONL fixtures with fixed timestamps and IDs.
- User-observable assertions: The generated HTML contains the goal, acceptance criteria, phase/subphase status, damage radius, branch strategy, proof plan, deterministic UX test, Armageddon scope, generality decision, fulfillment/readback status, evidence records, commit/archive indicators, and no stale hand-authored content.
- Command: `python3 scripts/mega_plan_init.py "Example Dashboard Plan" --goal "Verify dashboard generation" --output .tmp/example-plan.md --dashboard .tmp/example-plan.html --no-open`; then `python3 scripts/mega_plan_dashboard.py .tmp/example-plan.md --state tests/fixtures/state-valid.jsonl --evidence tests/fixtures/evidence-valid.jsonl --output .tmp/example-plan.html --no-open`.
- Evidence to record: Record both commands with `scripts/mega_evidence.py record` or `scripts/mega_evidence.py run`, plus the Playwright/HTML smoke result once dashboard rendering is implemented.

## Fulfillment and Readback Proof
- Requested final user-visible result: A generated dashboard HTML file that a user can open from the plan workflow and use to inspect ordered execution state, damage radius, regression guardrails, subphase progress, evidence, readback proof, blockers, and archive status.
- Required write/mutation operation: Write `.mega/state.jsonl` event records, write optional linked `.mega/evidence.jsonl` records, write the generated dashboard HTML artifact, and update Megaskill scripts/docs/templates/tests so the behavior is part of the general workflow.
- Readback surface: Read `.mega/state.jsonl` through `mega_state.py summary`, read `.mega/evidence.jsonl` through `mega_evidence.py summary`, parse the generated HTML with tests, and smoke-render the HTML in a browser or browser-test equivalent.
- Expected content, rows, fields, counts, or behavior: State rows must be ordered, valid JSON, schema-complete, and phase/subphase-linked; evidence rows with state IDs must resolve; dashboard sections must include the exact plan/status/proof fields listed in acceptance criteria; `--no-open` must never invoke browser launch; interactive open must target the generated file path.
- Command or tool call evidence: pytest output for state/dashboard tests, plan-check output for this plan and fixture plans, evidence/state summary output, and browser smoke/screenshot or DOM assertion for generated HTML.
- Not-done conditions: A static hand-authored dashboard only, a dashboard not generated from canonical plan/state/evidence, missing readback assertions, browser launch without no-open safety, unlinked evidence/state rows, or skipped browser verification because Playwright/browser tooling was merely absent.

## Armageddon Mode
- Damage-scaled attack scope: Large damage radius. Attack the public Megaskill planning contract, script CLI behavior, generated artifacts, browser-opening behavior, state/evidence schema compatibility, and existing tests.
- Edge cases to try: missing plan file, invalid Markdown, plan without required sections, missing state file, empty state file, malformed JSONL, duplicate event IDs, non-monotonic event order, unknown event kind, event for nonexistent phase, evidence pointing to missing state event, very long notes, HTML special characters, `--no-open`, CI environment, wrong cwd, generated output directory missing, repeated dashboard generation, and archive-only closed phases.
- Failure modes to simulate: browser open unavailable, Playwright missing before install/repair, invalid output path, state validation failure, plan validation failure, interrupted state event sequence, failed verification evidence, failed fulfillment readback, high-risk plan without branch strategy.
- Optimization opportunities to inspect: duplicated parsing between plan checker and dashboard generator, brittle regex extraction, excessive dashboard CSS/JS, nonportable file URLs, large JSONL read performance, state/evidence schema drift, and whether the dashboard can reuse a small shared plan parser.
- Must-fix threshold: Any schema corruption, invalid ordering accepted as valid, generated dashboard missing required proof fields, accidental browser launch in no-open/CI mode, existing plan-check regression, or test suite failure blocks done.
- Evidence to record: Unit tests, fixture tests, CLI smoke output, dashboard DOM/browser smoke, and `mega_evidence.py summary`.

## Generality Guardrail
- Existing mechanism to reuse: Use Megaskill's canonical Markdown plan, plan checker, evidence recorder, scope checker, and commit checker as the owning mechanisms for planning/proof/atomicity.
- Similar existing use cases: BESS production-controller dashboard, Megaskill evidence ledger, plan templates, plan validation fixtures, atomic commit checks, branch strategy checks, and future lower-agent execution plans.
- Recurrence likelihood: High. Every substantial Megaskill plan benefits from ordered state capture and a navigable dashboard.
- General mechanism to create if none exists: Create `mega_state.py` as the ordered execution ledger owner and `mega_plan_dashboard.py` as the dashboard renderer owner. Add any shared plan parsing helper only if implementation shows parser duplication between checker and dashboard is meaningful.
- Specific use case implementation through the mechanism: The initial dashboard workflow should be implemented by `mega_plan_init.py --dashboard` delegating to `mega_plan_dashboard.py`; the BESS dashboard is only used as a visual/reference artifact, not copied into project-specific Megaskill code.
- One-off justification, if any: None. The user's request is explicitly recurring for Megaskill plans and lower-agent work.

## Regression Guardrails
- Planned edit surface: `SKILL.md`, `README.md`, `references/execution-contract.md`, `references/agent-plan-template.md`, `scripts/mega_state.py`, `scripts/mega_plan_dashboard.py`, `scripts/mega_plan_init.py`, `scripts/mega_plan_check.py`, `scripts/mega_evidence.py`, test fixtures under `tests/fixtures/`, tests under `tests/`, and optional `.gitignore` entries for generated dashboard output.
- Protected behaviors: Existing plan skeleton generation, existing plan validation failures, existing evidence record/run/summary behavior, commit/scope checks, current fixture expectations, no forced browser opening in CI, no mandatory external service for normal CLI usage.
- Likely consumers: Codex agents invoking `$megaskill`, lower-level agents receiving generated plans, future skills that call Megaskill scripts, Git reviewers expecting atomic commits, and users opening generated plan dashboards.
- Damage radius: Large.
- Branch strategy: Create a dedicated work branch before implementation, for example `feat/megaskill-ordered-state-dashboard`, because this changes the public skill contract and adds browser-facing generated artifacts.
- Proof plan: Validate this plan with `python3 scripts/mega_plan_check.py MEGASKILL_ORDERED_STATE_AND_PLAN_DASHBOARD_PLAN.md`; run unit/fixture tests with `python3 -m pytest`; run CLI smoke for state, evidence, plan init, dashboard generation, and no-open behavior; run browser/Playwright smoke for generated dashboard HTML; record evidence; run scope/commit checks before each atomic commit.

## Phase 1: Architecture Contract And Dashboard Shape

### Subphase 1.1: Document the ordered state and dashboard contract
- Commit: docs(megaskill): define ordered state and dashboard contract
- Tests: `python3 scripts/mega_plan_check.py MEGASKILL_ORDERED_STATE_AND_PLAN_DASHBOARD_PLAN.md`
- Success Criteria: The public Megaskill contract explains state ledger ownership, dashboard generation, optional browser open, no-open/CI behavior, and evidence correlation.
- Planned Touch Files:
  - `SKILL.md`
  - `README.md`
  - `references/execution-contract.md`
  - `references/agent-plan-template.md`
- Checklist:
  - [ ] Re-read the BESS dashboard HTML and extract reusable concepts: source-of-truth cards, diagram/status area, acceptance list, findings table, phase list, go/no-go gates, archive boundary.
  - [ ] Update Megaskill docs to state that dashboards are generated views over canonical plan/state/evidence.
  - [ ] Add dashboard/readback fields to the lower-agent plan template without weakening existing required sections.
  - [ ] Run the plan checker against this plan and any updated fixture plan that uses dashboard fields.

### Subphase 1.2: Add dashboard requirements to plan validation
- Commit: feat(plan): validate ordered state dashboard requirements
- Tests: `python3 -m pytest tests/test_plan_check.py`
- Success Criteria: Plans that request dashboard/state behavior must name state capture, dashboard output, open/no-open behavior, and readback proof; existing valid plans remain valid.
- Planned Touch Files:
  - `scripts/mega_plan_check.py`
  - `tests/test_plan_check.py`
  - `tests/fixtures/dashboard-state-good.md`
  - `tests/fixtures/dashboard-state-missing-readback-bad.md`
- Checklist:
  - [ ] Add narrowly scoped validation for dashboard-specific plans, avoiding false positives for unrelated plans.
  - [ ] Add one valid fixture and at least one invalid fixture that catches dashboard-generation without readback.
  - [ ] Verify existing bad fixtures still fail for their original reasons.

## Phase 2: Ordered State Ledger

### Subphase 2.1: Implement append-only state recording
- Commit: feat(state): add append-only execution state ledger
- Tests: `python3 -m pytest tests/test_mega_state.py`
- Success Criteria: `mega_state.py` can append deterministic, schema-complete event records and summarize them in execution order.
- Planned Touch Files:
  - `scripts/mega_state.py`
  - `tests/test_mega_state.py`
  - `tests/fixtures/state-valid.jsonl`
- Checklist:
  - [ ] Implement commands: `init`, `record`, `summary`, and `validate`.
  - [ ] Required fields: `event_id`, `timestamp`, `cwd`, `plan`, `phase`, `subphase`, `kind`, `status`, `summary`, `damage_radius`, `branch`, `related_event_ids`, and `metadata`.
  - [ ] Generate stable event IDs from timestamp plus sequence or UUID; tests may inject IDs/timestamps for determinism.
  - [ ] Ensure records are append-only and JSONL-compatible.
  - [ ] Add summary output grouped by phase/subphase/status.

### Subphase 2.2: Validate ordering, schema, and correlations
- Commit: test(state): cover state ledger ordering and corruption
- Tests: `python3 -m pytest tests/test_mega_state.py`
- Success Criteria: Invalid JSONL, duplicate IDs, non-monotonic ordering, missing required fields, unknown statuses, and bad related IDs fail validation with actionable messages.
- Planned Touch Files:
  - `scripts/mega_state.py`
  - `tests/test_mega_state.py`
  - `tests/fixtures/state-duplicate-id-bad.jsonl`
  - `tests/fixtures/state-nonmonotonic-bad.jsonl`
  - `tests/fixtures/state-missing-field-bad.jsonl`
- Checklist:
  - [ ] Add validation for duplicate event IDs.
  - [ ] Add validation for timestamp/sequence order.
  - [ ] Add validation for allowed event kinds and statuses.
  - [ ] Add validation for `related_event_ids`.

### Subphase 2.3: Link evidence to state without breaking compatibility
- Commit: feat(evidence): link verification evidence to execution state
- Tests: `python3 -m pytest tests/test_mega_evidence.py tests/test_mega_state.py`
- Success Criteria: Existing evidence commands still work, and new `--state-event-id` metadata can be recorded and validated by dashboard/state tooling.
- Planned Touch Files:
  - `scripts/mega_evidence.py`
  - `scripts/mega_state.py`
  - `tests/test_mega_evidence.py`
  - `tests/fixtures/evidence-valid.jsonl`
- Checklist:
  - [ ] Add optional `--state-event-id` to `record` and `run`.
  - [ ] Preserve current evidence JSON fields and summary output.
  - [ ] Add tests proving old evidence records remain readable.
  - [ ] Add correlation validation in `mega_state.py` or the dashboard generator.

## Phase 3: Dashboard Generator

### Subphase 3.1: Generate canonical HTML from plan, state, and evidence
- Commit: feat(dashboard): render megaskill plan dashboard html
- Tests: `python3 -m pytest tests/test_plan_dashboard.py`
- Success Criteria: The dashboard generator writes deterministic, escaped, self-contained HTML that reflects canonical Markdown, state, and evidence inputs.
- Planned Touch Files:
  - `scripts/mega_plan_dashboard.py`
  - `tests/test_plan_dashboard.py`
  - `tests/fixtures/dashboard-plan.md`
  - `tests/fixtures/state-valid.jsonl`
  - `tests/fixtures/evidence-valid.jsonl`
- Checklist:
  - [ ] Parse the plan into title, goal, acceptance, research/SOTA, preflight, deterministic UX test, fulfillment/readback, Armageddon, generality, regression guardrails, phases, subphases, planned touch files, and checklist items.
  - [ ] Render source-of-truth cards for plan path, state path, evidence path, branch, damage radius, and generated timestamp.
  - [ ] Render phase/subphase status from state records and evidence records.
  - [ ] Render proof/readback and Armageddon status distinctly from implementation progress.
  - [ ] Escape all plan/state/evidence content and avoid external JS/CSS dependencies.

### Subphase 3.2: Add archive and damage-radius visualization
- Commit: feat(dashboard): show regression radius and archive state
- Tests: `python3 -m pytest tests/test_plan_dashboard.py`
- Success Criteria: Dashboard makes high-risk work visible: damage radius, branch strategy, protected behaviors, likely consumers, open blockers, completed/archive phases, and failed/blocked evidence are obvious.
- Planned Touch Files:
  - `scripts/mega_plan_dashboard.py`
  - `tests/test_plan_dashboard.py`
  - `tests/fixtures/dashboard-plan-with-archive.md`
- Checklist:
  - [ ] Add CSS status classes for done, active, blocked, failed, warning, and archive.
  - [ ] Add an archive section that marks superseded phases or previous plans as evidence, not current instructions.
  - [ ] Add a regression matrix table: planned edit surface, protected behaviors, likely consumers, damage radius, branch strategy, proof plan.
  - [ ] Add failing evidence/readback as no-go gate items.

### Subphase 3.3: Browser smoke the generated dashboard
- Commit: test(dashboard): smoke generated plan html in browser
- Tests: `python3 -m pytest tests/test_plan_dashboard.py` plus the project-local Playwright/browser smoke command added by this subphase
- Success Criteria: Generated HTML renders in a browser, key sections are visible, navigation anchors work, and no console/runtime errors appear.
- Planned Touch Files:
  - `tests/test_plan_dashboard_browser.py`
  - `tests/fixtures/dashboard-plan.md`
  - optional project-local browser-test config or dependency file if needed
- Checklist:
  - [ ] Install or repair browser test tooling if absent.
  - [ ] Generate dashboard fixture HTML in a temp directory.
  - [ ] Open the file URL in Chromium through Playwright or the repo-equivalent browser runner.
  - [ ] Assert visible sections: source of truth, objective, acceptance, phases, regression, Armageddon, evidence, archive.
  - [ ] Capture a screenshot or DOM evidence artifact and record it with `mega_evidence.py`.

## Phase 4: Plan Init Integration And Browser Open

### Subphase 4.1: Integrate dashboard generation into plan creation
- Commit: feat(plan): generate dashboard during megaskill plan init
- Tests: `python3 -m pytest tests/test_plan_init.py tests/test_plan_dashboard.py`
- Success Criteria: `mega_plan_init.py` can create a plan and dashboard in one command while preserving existing plan-only behavior.
- Planned Touch Files:
  - `scripts/mega_plan_init.py`
  - `scripts/mega_plan_dashboard.py`
  - `tests/test_plan_init.py`
  - `README.md`
- Checklist:
  - [ ] Add `--dashboard [path]` support that writes HTML after plan creation.
  - [ ] Default dashboard path should be deterministic when requested, for example beside the plan or under `.mega/dashboards/`.
  - [ ] Do not require state/evidence files to exist; render empty-state guidance when absent.
  - [ ] Preserve stdout behavior when `--output` is not used.

### Subphase 4.2: Add safe automatic browser opening
- Commit: feat(dashboard): add safe default browser open flow
- Tests: `python3 -m pytest tests/test_plan_init.py tests/test_plan_dashboard.py`
- Success Criteria: Interactive dashboard generation can open the generated file in the default browser, and `--no-open` plus CI detection suppress browser launch deterministically.
- Planned Touch Files:
  - `scripts/mega_plan_init.py`
  - `scripts/mega_plan_dashboard.py`
  - `tests/test_plan_init.py`
  - `tests/test_plan_dashboard.py`
- Checklist:
  - [ ] Add `--open` and `--no-open` flags with CI-safe defaults.
  - [ ] Use `webbrowser.open(file_uri)` through a wrapper that can be mocked in tests.
  - [ ] Add tests proving no-open does not call the browser wrapper.
  - [ ] Add tests proving open targets the generated dashboard file URI.

## Phase 5: End-To-End Enforcement And Release

### Subphase 5.1: Add end-to-end fixture pipeline
- Commit: test(megaskill): verify ordered state dashboard workflow
- Tests: `python3 -m pytest`
- Success Criteria: A full fixture run covers plan generation, plan validation, state recording, evidence recording, dashboard generation, no-open behavior, and dashboard readback.
- Planned Touch Files:
  - `tests/test_ordered_state_dashboard_workflow.py`
  - `tests/fixtures/dashboard-plan.md`
  - `tests/fixtures/state-valid.jsonl`
  - `tests/fixtures/evidence-valid.jsonl`
- Checklist:
  - [ ] Build one deterministic integration test using temp dirs.
  - [ ] Verify generated plan passes `mega_plan_check.py`.
  - [ ] Verify generated state passes `mega_state.py validate`.
  - [ ] Verify evidence summary remains compatible.
  - [ ] Verify dashboard readback contains expected status and proof fields.

### Subphase 5.2: Run Armageddon and regression proof
- Commit: chore(release): verify ordered state dashboard pipeline
- Tests: `python3 scripts/mega_plan_check.py MEGASKILL_ORDERED_STATE_AND_PLAN_DASHBOARD_PLAN.md`; `python3 -m pytest`; dashboard browser smoke; `python3 scripts/mega_scope_check.py MEGASKILL_ORDERED_STATE_AND_PLAN_DASHBOARD_PLAN.md --planned ...`; `python3 scripts/mega_commit_check.py`
- Success Criteria: Full proof passes, adversarial fixture failures are caught, no existing behavior regresses, evidence is recorded, and the branch is ready to push.
- Planned Touch Files:
  - `.mega/evidence.jsonl`
  - generated temp artifacts only under ignored `.tmp/` or `.mega/dashboards/`
- Checklist:
  - [ ] Run all tests.
  - [ ] Run browser smoke and screenshot/DOM readback for generated dashboard.
  - [ ] Run Armageddon cases from this plan and document weaknesses/bugs/optimizations.
  - [ ] Record evidence summary.
  - [ ] Push the dedicated branch after tests pass.

## Commit Plan
- `docs(megaskill): define ordered state and dashboard contract`
- `feat(plan): validate ordered state dashboard requirements`
- `feat(state): add append-only execution state ledger`
- `test(state): cover state ledger ordering and corruption`
- `feat(evidence): link verification evidence to execution state`
- `feat(dashboard): render megaskill plan dashboard html`
- `feat(dashboard): show regression radius and archive state`
- `test(dashboard): smoke generated plan html in browser`
- `feat(plan): generate dashboard during megaskill plan init`
- `feat(dashboard): add safe default browser open flow`
- `test(megaskill): verify ordered state dashboard workflow`
- `chore(release): verify ordered state dashboard pipeline`

## Lower-Agent Execution Notes
- Start by creating `feat/megaskill-ordered-state-dashboard`; stop before edits if branching is blocked.
- Re-read this plan before every subphase.
- Do not copy the BESS dashboard HTML. Extract concepts and implement a generator.
- Keep generated dashboard outputs ignored unless a specific fixture artifact is intentionally committed.
- Record verification evidence after each meaningful check.
- Do not call the dashboard work done until generated HTML has been read back and browser-rendered, or until browser setup is blocked by a real documented blocker after attempted install/repair.
