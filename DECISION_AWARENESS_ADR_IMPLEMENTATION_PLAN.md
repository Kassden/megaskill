# Megaskill Decision Awareness And ADR Implementation Plan

Implementation update (2026-10-14): `mega_decision.py` now provides append-only record/validate/summary/status/promote, critique fields, exact task/plan linkage, lifecycle and supersession. Durable accepted choices become Markdown ADRs; the dashboard renders decisions and the runtime records stop decisions. The canonical implementation and verification record is `MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md`. This proposal remains historical design context, not evidence that every future extension is complete.

## GOAL
- Implement a first-class Megaskill decision-awareness system that records why agents choose specific approaches, alternatives, verification strategies, UI/product patterns, risk boundaries, and remediation paths, then makes those decisions available to the agent, reviewer, dashboard, and final handoff.

## Acceptance Criteria
- [ ] Megaskill has a structured `.mega/decisions.jsonl` ledger that records why meaningful choices were made.
- [ ] A `scripts/mega_decision.py` CLI can record, validate, summarize, and link decision records to plan phases, state events, and evidence records.
- [ ] Megaskill instructions and plan templates define when a decision record is required.
- [ ] UI/product decisions are explicitly covered, including layout, interaction model, information architecture, density, controls, and visual hierarchy choices.
- [ ] Decision records include self-critique: assumptions, rejected alternatives, what would prove the decision wrong, reversibility, and follow-up triggers.
- [ ] The dashboard renders a decision log beside ordered state and evidence.
- [ ] `mega_plan_check.py` can require a `Decision Record Policy` for substantial/systemic plans and reject missing or weak policy sections.
- [ ] The final handoff summarizes key decisions and links them to decision IDs.
- [ ] Fixture tests prove both failure and success cases for decision-aware plans and decision-ledger validation.
- [ ] Existing state/evidence workflows keep working; decision records complement them rather than becoming a parallel plan.

## Research
- Built-in options: reuse Megaskill's existing `.mega/state.jsonl`, `.mega/evidence.jsonl`, `mega_state.py`, `mega_evidence.py`, `mega_plan_dashboard.py`, `mega_plan_check.py`, plan template, and final handoff template.
- Off-the-shelf options: borrow durable rationale conventions from ADR/MADR/log4brains-style records; borrow self-reflection fields from Reflexion/Self-Refine style loops; borrow policy enforcement ideas from ADR governance and architecture-rule tooling.
- Official / standards sources: inspect local prior Megaskill rules first; when implementation begins, refresh ADR prior art and agent self-reflection references from primary project docs or repositories before locking schema names.

## Root-Cause Baseline
- Trigger scope: not an incident remediation task; this is a governance and agent-decision feature proposal, but it affects future remediation paths and must preserve the root-cause baseline behavior already implemented.
- Minimum evidence inventory: current health is the existing Megaskill state/evidence ledger design; relevant logs/journals are not applicable; metrics/readbacks are validator, fixture, generated dashboard, and final handoff behavior; recent changes include root-cause gate commits on `megaskill/root-cause-gate`; config/state includes `.mega/state.jsonl` and `.mega/evidence.jsonl`.
- Hypothesis model: proven need is that state explains what happened and evidence explains how it was verified, while neither fully explains why a choice was made; likely failure mode is agent reasoning hidden in chat transcript; possible failure mode is too many low-value records; unlikely/disproven approach is replacing state/evidence with ADRs.
- Missing-evidence policy: external ADR/self-reflection references must be refreshed during implementation; if network access is unavailable, record that limitation and use local README direction plus existing Megaskill ledgers as temporary evidence.
- Mutation boundary: before implementation, only write this plan and perform read-only repo inspection; implementation mutations require a dedicated subphase and validation.
- Remediation mapping: not a remediation fix; this maps a governance gap to a decision-ledger feature. Generic hardening such as "write better notes" is rejected unless implemented through structured decisions.
- Not-done conditions: plan only says "use ADRs" without schema, CLI, validation, dashboard, self-critique, and UI-decision coverage.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: ADRs preserve architectural rationale; MADR broadens the pattern toward any decision records; log-style tooling makes decisions searchable; agent self-reflection loops make agents critique their own choices before committing to them.
- Official docs, standards, specs, or platform guidance: implementation should refresh ADR/MADR format guidance, relevant GitHub examples, and any maintained docs for agent reflection systems before coding.
- Mature libraries, frameworks, or built-in mechanisms: prefer Python standard library JSONL handling, existing Megaskill ledger style, existing dashboard renderer, and existing plan-check patterns over a new storage format.
- Best-practice constraints to integrate: records must be small, structured, append-only, linkable, searchable, and auditable; threshold must avoid logging every trivial micro-choice; self-critique must happen before irreversible or high-impact choices.
- Rejected approaches: long prose ADRs for every turn; only adding README guidance; storing decisions only in chat; folding decisions into `.mega/state.jsonl`; requiring decisions for every tiny implementation detail; creating a separate dashboard source of truth.
- Implementation decision: create `.mega/decisions.jsonl` plus `scripts/mega_decision.py`, integrate it into plan validation, dashboard rendering, final handoff, and Megaskill instructions.

## Decision Record Policy
- Required for: architecture choices, UI/product workflow choices, data/schema choices, branch strategy for large/systemic work, scope expansion/reduction, verification tradeoffs, root-cause hypothesis selection, one-off versus general mechanism, dependency/tooling fallback, destructive or production-adjacent boundaries, and any decision a reviewer would reasonably ask about later.
- Optional for: local variable names, mechanical refactors, formatting, direct implementation of a plan item with no meaningful alternative, and choices already dictated by a repo convention.
- Record shape: decision ID, timestamp, plan, phase, subphase, kind, question, chosen decision, why, alternatives considered, evidence refs, state refs, tradeoffs, reversibility, self-critique, what would prove it wrong, supersedes, and status.
- Self-critique questions: what assumption am I making, what alternative am I rejecting, what would make this decision bad, how reversible is it, and what check will reveal the problem soonest?
- UI/product coverage: record choices about tabs versus sidebar, modal versus inline, compact versus verbose controls, density, visual hierarchy, empty/error/loading states, mobile behavior, keyboard path, and whether the chosen pattern matches existing design conventions.
- Threshold: if a future reviewer could reasonably ask "why did the agent do that?", record it.
- Not-done conditions: no structured schema, no self-critique, no UI/product coverage, no dashboard visibility, no validation, or decision records that cannot link to evidence/state.

## Dependency and Tooling Preflight
- Required verification tools: Python standard library, `unittest`, `rg`, `git`, existing Megaskill plan checker, state/evidence scripts, and dashboard tests.
- Existing tooling found: `scripts/mega_state.py`, `scripts/mega_evidence.py`, `scripts/mega_plan_dashboard.py`, `scripts/mega_plan_check.py`, `scripts/mega_plan_init.py`, `tests/test_*.py`, and existing fixture patterns.
- Install or repair commands: no install is needed for the core implementation; use Python standard library only.
- Browser/runtime binaries: dashboard rendering changes may require existing browser smoke or explicit readback; no new browser runtime should be required unless dashboard visual tests already use one.
- Real blockers that would prevent setup: conflicting user instruction, incompatible Python runtime, denied file edit permission, unavailable browser for dashboard smoke, or an external outage during optional ADR reference refresh.

## Deterministic Real-User Test
- Entry point: `python3 scripts/mega_decision.py record ...` followed by `python3 scripts/mega_decision.py summary`.
- User workflow: an agent records a UI decision such as tabs versus sidebar, includes rejected alternatives and self-critique, links it to a plan phase, then the reviewer reads the dashboard and final handoff to understand the choice.
- Stable inputs or fixtures: static JSONL fixtures for valid decisions, missing self-critique, missing alternatives, invalid status, superseded decision, UI decision missing "what would prove wrong", and decision linked to state/evidence records.
- User-observable assertions: CLI output shows the decision ID, summary lists key choices by kind/status, dashboard renders the decision log, and final handoff includes key decisions.
- Command: `python3 -m unittest discover -s tests -p 'test_*.py'`.
- Evidence to record: unit test output, fixture validation output, dashboard readback output, and plan-check output.

## Fulfillment and Readback Proof
- Requested final user-visible result: a reviewer can understand why the agent made meaningful choices without reading the entire chat transcript.
- Required write/mutation operation: create `scripts/mega_decision.py`, update templates/instructions/checker/dashboard/final handoff, and add tests/fixtures.
- Readback surface: CLI summary, dashboard HTML, final handoff template, validator errors, and `.mega/decisions.jsonl` contents.
- Expected content, rows, fields, counts, or behavior: decisions have required fields; weak decisions fail validation; dashboard shows question/decision/why/evidence/self-critique/status; final handoff lists key decisions; existing state/evidence tests pass.
- Command or tool call evidence: `python3 scripts/mega_decision.py validate --file tests/fixtures/decisions-good.jsonl`, bad-fixture validation, dashboard tests, plan-check tests, and full unittest discovery.
- Not-done conditions: ledger exists but no validator; records lack alternatives or self-critique; dashboard omits decisions; final handoff omits key choices; UI decisions are not covered; existing Megaskill tests regress.

## Armageddon Mode
- Damage-scaled attack scope: systemic because decision awareness changes Megaskill's execution contract and future agent behavior.
- Edge cases to try: empty decision file, malformed JSONL, duplicate decision IDs, missing required fields, very long rationale, invalid kind/status, supersedes unknown ID, evidence refs not found, status transition from proposed to superseded, trivial decision spam, and UI decision without self-critique.
- Failure modes to simulate: agent records decision after implementation instead of before, decision conflicts with plan, decision claims evidence that does not exist, dashboard cannot parse decisions, plan checker forces decisions on tiny low-risk edits, and final handoff overflows with too many low-value decisions.
- Optimization opportunities to inspect: compact JSONL schema, summary filtering by kind/status, dashboard table readability, stable IDs, and reuse of state/evidence validation helpers.
- Must-fix threshold: high-impact work can complete without decision rationale, or ordinary small changes become noisy and burdensome.
- Evidence to record: unit tests, fixture validation, dashboard readback, and examples of UI/product decision records.

## Generality Guardrail
- Existing mechanism to reuse: ordered state ledger, evidence ledger, dashboard renderer, plan checker, plan init template, final handoff template, and commit/scope checks.
- Similar existing use cases: root-cause baseline, SOTA implementation decision, generality guardrail, branch strategy, proof plan, state/evidence linked records.
- Recurrence likelihood: high across UI, architecture, data, production, testing, and agent-tool workflows.
- General mechanism to create if none exists: `.mega/decisions.jsonl` and `mega_decision.py`.
- Specific use case implementation through the mechanism: ADR-style records become one decision kind, not a separate ADR-only workflow.
- One-off justification, if any: none.

## Ordered State and Dashboard
- State ledger path: `.mega/state.jsonl`.
- Dashboard output path: `.mega/dashboards/decision-awareness-plan.html`.
- Open behavior: generate with `--no-open` during noninteractive validation; use `--open` only when explicitly requested.
- State events to record: plan accepted, schema implemented, CLI implemented, validator implemented, dashboard integrated, tests passed, docs updated, final readback.
- Evidence links: link decision validation and dashboard checks via `state_event_id` where practical.
- Dashboard readback assertions: dashboard includes a Decision Log section with question, decision, why, kind, status, evidence refs, self-critique, and supersedes fields.

## Regression Guardrails
- Planned edit surface:
  - `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`
  - `SKILL.md`
  - `README.md`
  - `references/agent-plan-template.md`
  - `references/execution-contract.md`
  - `references/final-handoff-template.md`
  - `scripts/mega_decision.py`
  - `scripts/mega_plan_check.py`
  - `scripts/mega_plan_dashboard.py`
  - `scripts/mega_plan_init.py`
  - `tests/test_mega_decision.py`
  - `tests/test_plan_check.py`
  - `tests/test_plan_dashboard.py`
  - `tests/fixtures/decisions-good.jsonl`
  - `tests/fixtures/decisions-missing-self-critique-bad.jsonl`
  - `tests/fixtures/decision-policy-missing-bad.md`
  - `tests/fixtures/decision-policy-good.md`
- Protected behaviors: existing state/evidence ledgers, root-cause gate validation, dashboard generation, plan skeleton validation, full test suite, and atomic commit checks.
- Likely consumers: future agents using Megaskill, reviewers reading final handoffs, dashboard users, plan authors, and lower-level agents.
- Damage radius: Systemic.
- Branch strategy: Create dedicated branch `megaskill/decision-awareness-adrs` before implementation edits. This proposal artifact can be reviewed from the current planning branch, but executable ADR work should be isolated on that named branch.
- Proof plan: plan check, decision CLI fixture validation, full unittest discovery, dashboard readback, bad-fixture failures, good-fixture passes, scope check, commit check, and final gate.

## Phase 1: Proposal And Schema

### Subphase 1.1: Finalize Decision Record Schema
- Commit: define decision-awareness schema and thresholds.
- Tests: `python3 scripts/mega_plan_check.py DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`.
- Success Criteria: plan validates and names the decision record fields, thresholds, self-critique questions, UI/product coverage, and not-done conditions.
- Planned Touch Files:
  - `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`
- Checklist:
  - [ ] Define required decision fields.
  - [ ] Define decision kinds and statuses.
  - [ ] Define when decisions are required versus optional.
  - [ ] Include UI/product decision examples.
  - [ ] Validate this plan.

## Phase 2: Decision CLI And Ledger

### Subphase 2.1: Implement `mega_decision.py`
- Commit: add decision ledger CLI.
- Tests: `python3 -m unittest tests/test_mega_decision.py`.
- Success Criteria: CLI can record, validate, and summarize decisions in `.mega/decisions.jsonl`.
- Planned Touch Files:
  - `scripts/mega_decision.py`
  - `tests/test_mega_decision.py`
  - `tests/fixtures/decisions-good.jsonl`
  - `tests/fixtures/decisions-missing-self-critique-bad.jsonl`
- Checklist:
  - [ ] Add record command with stable generated IDs.
  - [ ] Add validate command.
  - [ ] Add summary command.
  - [ ] Validate required fields, kinds, statuses, alternatives, and self-critique.
  - [ ] Test duplicate IDs and malformed JSONL.

### Subphase 2.2: Link Decisions To State And Evidence
- Commit: connect decisions to existing Megaskill ledgers.
- Tests: `python3 -m unittest tests/test_mega_decision.py`.
- Success Criteria: decisions can reference state event IDs and evidence records, and validator reports unresolved refs when provided with those ledger files.
- Planned Touch Files:
  - `scripts/mega_decision.py`
  - `tests/test_mega_decision.py`
- Checklist:
  - [ ] Support `--state-event-id`.
  - [ ] Support evidence refs as strings.
  - [ ] Validate refs when state/evidence files are supplied.
  - [ ] Keep validation usable without state/evidence files.

## Phase 3: Plan Policy And Validation

### Subphase 3.1: Add Decision Policy To Templates
- Commit: add Decision Record Policy to Megaskill templates and docs.
- Tests: `rg -n "Decision Record Policy|decisions.jsonl|self-critique" SKILL.md references README.md`.
- Success Criteria: plan authors and agents know when to record decisions and what fields matter.
- Planned Touch Files:
  - `SKILL.md`
  - `README.md`
  - `references/agent-plan-template.md`
  - `references/execution-contract.md`
  - `references/final-handoff-template.md`
  - `scripts/mega_plan_init.py`
- Checklist:
  - [ ] Add Decision Record Policy to generated plans.
  - [ ] Add required decision triggers to the execution contract.
  - [ ] Add final handoff decision summary field.
  - [ ] Keep root-cause baseline rules intact.

### Subphase 3.2: Enforce Decision Policy In Plan Checker
- Commit: validate decision-aware plans.
- Tests: `python3 -m unittest tests/test_plan_check.py`.
- Success Criteria: substantial/systemic plans require a Decision Record Policy and bad fixtures fail with actionable errors.
- Planned Touch Files:
  - `scripts/mega_plan_check.py`
  - `tests/test_plan_check.py`
  - `tests/fixtures/decision-policy-missing-bad.md`
  - `tests/fixtures/decision-policy-good.md`
- Checklist:
  - [ ] Detect large/systemic or decision-heavy plans.
  - [ ] Require policy fields for required/optional decisions and self-critique.
  - [ ] Avoid forcing decision policy on tiny simple plans.
  - [ ] Add good and bad fixtures.

## Phase 4: Dashboard And Handoff Integration

### Subphase 4.1: Render Decision Log In Dashboard
- Commit: show decisions in generated dashboards.
- Tests: `python3 -m unittest tests/test_plan_dashboard.py`.
- Success Criteria: dashboard reads `.mega/decisions.jsonl` and renders decision ID, kind, question, decision, why, evidence refs, self-critique, status, and supersedes.
- Planned Touch Files:
  - `scripts/mega_plan_dashboard.py`
  - `tests/test_plan_dashboard.py`
  - `tests/fixtures/decisions-good.jsonl`
- Checklist:
  - [ ] Add `--decisions` path argument or default `.mega/decisions.jsonl`.
  - [ ] Render decision table.
  - [ ] Show parse/validation warnings.
  - [ ] Preserve dashboard behavior when decisions file is absent.

### Subphase 4.2: Update Final Handoff Shape
- Commit: include key decisions in final handoff.
- Tests: `rg -n "Key decisions|Decision Record" references/final-handoff-template.md README.md`.
- Success Criteria: final handoff prompts agents to list the key decisions and any unresolved decision risks.
- Planned Touch Files:
  - `references/final-handoff-template.md`
  - `README.md`
- Checklist:
  - [ ] Add key decisions field.
  - [ ] Add unresolved/superseded decision note.
  - [ ] Keep final verdict rules unchanged.

## Phase 5: Dogfood And Release Readiness

### Subphase 5.1: Dogfood Decision Awareness On This Feature
- Commit: record decisions made while implementing decision awareness.
- Tests: `python3 scripts/mega_decision.py validate --file .mega/decisions.jsonl`; `python3 scripts/mega_decision.py summary`.
- Success Criteria: implementation itself leaves useful decision records for schema, validation threshold, dashboard integration, and UI/product coverage choices.
- Planned Touch Files:
  - `.mega/decisions.jsonl`
- Checklist:
  - [ ] Record schema decision.
  - [ ] Record validation threshold decision.
  - [ ] Record dashboard presentation decision.
  - [ ] Record UI/product self-critique requirement decision.

### Subphase 5.2: Run Full Verification And Final Gate
- Commit: verify and hand off decision-awareness implementation.
- Tests: `python3 -m unittest discover -s tests -p 'test_*.py'`; `python3 scripts/mega_plan_check.py DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`; `python3 scripts/mega_scope_check.py DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`; `python3 scripts/mega_state.py final-gate --plan DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md --whole-plan --verdict done`.
- Success Criteria: all tests pass, this plan validates, scope is clean, final gate passes, and commits are atomic.
- Planned Touch Files:
  - `DECISION_AWARENESS_ADR_IMPLEMENTATION_PLAN.md`
- Checklist:
  - [ ] Run full unit discovery.
  - [ ] Run plan check.
  - [ ] Run good and bad fixture checks.
  - [ ] Run dashboard readback.
  - [ ] Run scope and commit checks.
  - [ ] Run final gate.
