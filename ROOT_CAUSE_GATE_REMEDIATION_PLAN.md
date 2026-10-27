# Megaskill Root-Cause Gate Remediation Plan

## GOAL
- Add a hard Megaskill gate that prevents remediation planning, implementation, deployment, or broad hardening for live/system incidents until the agent has collected available forensic evidence, separated proven root cause from hypotheses, and explicitly justified any evidence it cannot obtain.

## Acceptance Criteria
- Megaskill instructions require root-cause analysis before writing or executing remediation plans for live infrastructure, production-adjacent systems, telemetry gaps, outages, incidents, data loss, auth failures, deployment failures, device/network failures, or any request phrased as "what happened", "fix the outage", "recover", "remediate", or "prevent this again".
- The plan template contains a required `Root-Cause Baseline` section before `SOTA` and before any implementation phase.
- `mega_plan_check.py` fails high-risk remediation plans that lack a root-cause baseline, evidence matrix, hypothesis ranking, missing-evidence justification, and remediation-to-cause mapping.
- The execution contract requires a pre-remediation stop condition: no mutation except evidence collection and reversible diagnostics until the root-cause gate is satisfied or a real blocker is recorded.
- Tests include fixtures proving the 2026-09-18 DTU failure mode is rejected: a plan that jumps from "missing durability/stale-data alerting" to implementation without Pi logs, service journals, modem/kernel logs, network state, and cloud write/readback evidence must fail validation.
- The final implementation is verified with unit tests, plan-check fixtures, and a dogfood run of this plan through `mega_plan_check.py`.

## Incident Evidence From Rollout `01a0b21e-369c-7c82-8074-35b4dc9b27d5`
- The session involved a live Raspberry Pi / 4G / Tailscale outage and a 33-day Influx telemetry gap in `/Users/milkingthesun/Projects/monitoringSys/sunrya-dashboard`.
- Memory records show the agent diagnosed cloud telemetry loss and later produced a local resilience implementation, while live deployment and drills remained unauthorized.
- The raw session shows the agent generated `docs/dtu-resilience-mitigation-plan.md`, edited it, switched to a `dtu-resilience-hardening` branch, and implemented dashboard/exporter hardening.
- Later in the same conversation, the assistant acknowledged the failure directly: it had jumped from known durability and stale-data gaps to mitigation without exhausting the obvious forensic step.
- The acknowledged missing evidence class included `tailscaled` journal, exporter journal, kernel USB/modem logs, NetworkManager/ModemManager logs, routing/DNS state, and outage-window system logs.

## Research
- Built-in options: extend Megaskill's existing required workflow, plan template, execution contract, `mega_plan_check.py`, fixtures, and unit tests.
- Off-the-shelf options: use incident-management concepts already common in SRE workflows: incident timeline, evidence inventory, causal hypothesis ranking, remediation-to-cause traceability, and postmortem-style corrective actions.
- Official / standards sources: consult Google SRE incident response/postmortem guidance, AWS Well-Architected operational excellence guidance, and OpenTelemetry/logging guidance during implementation. When network access is unavailable, record that limitation and use local repo rules plus Megaskill's existing execution contract as the temporary evidence source.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: serious incident response separates immediate restoration from root-cause investigation, then ties corrective actions to evidence-backed causal mechanisms.
- Official docs, standards, specs, or platform guidance: SRE postmortems and operational excellence guidance treat timeline, impact, detection, root cause, and action items as distinct artifacts; observability guidance treats logs, metrics, traces, and readback checks as complementary evidence.
- Mature libraries, frameworks, or built-in mechanisms: reuse Megaskill's existing Markdown validator, plan template, evidence ledger, state ledger, and final gate instead of creating a parallel incident workflow.
- Best-practice constraints to integrate: remediation must name the failure mode it addresses; broad hardening can proceed only as explicitly labeled risk reduction, not as "the fix" for an unproven cause.
- Rejected approaches: relying on agent self-discipline only; adding prose warnings without validator tests; allowing "root cause unknown" without required missing-evidence and bounded-remediation language; treating cloud gaps alone as proof of device-side cause.
- Implementation decision: add a general `Root-Cause Baseline` requirement to Megaskill, enforce it in `mega_plan_check.py` for high-risk remediation contexts, and document a pre-remediation mutation boundary in `SKILL.md` plus `references/execution-contract.md`.

## Dependency and Tooling Preflight
- Required verification tools: Python standard library, `unittest`, `rg`, `sed`, `git`, Megaskill's `mega_plan_check.py`, and existing Megaskill fixture tests.
- Existing tooling found: `scripts/mega_plan_check.py`, `tests/test_plan_check.py`, `references/agent-plan-template.md`, `references/execution-contract.md`, `SKILL.md`, and fixture-based validation tests.
- Install or repair commands: no install is needed; the work uses Python standard library tests already present in the skill repo.
- Browser/runtime binaries: not applicable; this is a CLI/Markdown validator and instruction change, not a browser UI. No browser smoke, Playwright, screenshot, visual, pixel, canvas, or accessibility proof is required for this remediation.
- Real blockers that would prevent setup: denied file edit permission, incompatible Python runtime, conflicting user instruction, or a dirty skill repo change that overlaps the same files and cannot be reconciled safely.

## Root-Cause Baseline
- Trigger scope: required for live incidents, outages, recovery tasks, production-adjacent systems, device/network/service failures, telemetry gaps, data loss, deployment failures, auth failures, or any remediation plan.
- Minimum evidence inventory: timeline, affected surface, current health, logs/journals, metrics/readbacks, recent changes, config/state, external dependencies, and user-observed facts.
- Hypothesis model: rank candidate causes as proven, likely, possible, unlikely, or disproven; attach evidence and counter-evidence to each.
- Missing-evidence policy: if evidence is unavailable, state why, who or what could supply it, whether collection is destructive, and how that uncertainty constrains remediation.
- Mutation boundary: before this baseline is complete, allowed actions are read-only probes, reversible diagnostics, evidence-preserving collection, and urgent restoration steps explicitly scoped to regain access or reduce active harm.
- Remediation mapping: every proposed fix must name the proven or hypothesized failure class it addresses; generic hardening must be labeled as risk reduction and cannot be presented as root-cause remediation.
- Not-done conditions: no plan validation if the document jumps from symptoms to implementation, lacks outage-window evidence, conflates root cause with missing guardrails, or omits uncertainty.

## Deterministic Real-User Test
- Entry point: `python3 scripts/mega_plan_check.py tests/fixtures/root-cause-gate-missing-bad.md`.
- User workflow: a lower-level agent writes a live-system remediation plan after an outage; the validator rejects it because it lacks a root-cause baseline and jumps directly to hardening.
- Stable inputs or fixtures: one bad fixture based on the DTU/Tailscale/Influx failure mode and one good fixture with evidence inventory, hypothesis ranking, missing-evidence notes, and remediation mapping.
- User-observable assertions: bad fixture fails with a clear root-cause-gate error; good fixture passes; existing valid plans still pass unless they are high-risk remediation plans missing the new section.
- Command: `python3 -m unittest tests/test_plan_check.py`.
- Evidence to record: failing fixture error text before implementation if using test-first flow, passing unit test output after implementation, and `mega_plan_check.py ROOT_CAUSE_GATE_REMEDIATION_PLAN.md`.

## Fulfillment and Readback Proof
- Requested final user-visible result: Megaskill rejects premature remediation plans and instructs agents to do root-cause analysis before plan/write/execute on incidents.
- Required write/mutation operation: update Megaskill instructions, template, validator, and tests.
- Readback surface: read `SKILL.md`, `references/execution-contract.md`, `references/agent-plan-template.md`, `scripts/mega_plan_check.py`, and test fixtures; run validator/tests and compare expected pass/fail behavior.
- Expected content, rows, fields, counts, or behavior: root-cause baseline appears in instructions/templates; validator emits a specific missing-root-cause-baseline error for high-risk remediation plans; good and bad fixtures prove the behavior.
- Command or tool call evidence: `python3 scripts/mega_plan_check.py ROOT_CAUSE_GATE_REMEDIATION_PLAN.md`, `python3 -m unittest tests/test_plan_check.py`, and targeted fixture commands.
- Not-done conditions: prose-only warning, no automated rejection, validator that rejects unrelated small plans, no fixture matching the DTU incident pattern, or no remediation-to-cause mapping requirement.

## Armageddon Mode
- Damage-scaled attack scope: systemic because Megaskill governs future high-rigor remediation work.
- Edge cases to try: normal UI plan without incident language, live incident plan with "root cause unknown" but good missing-evidence policy, plan with evidence inventory but no remediation mapping, plan that calls broad hardening "root cause", plan that needs urgent restoration before logs, and plan where logs are unavailable due to retention.
- Failure modes to simulate: false positive on ordinary implementation plans, false negative on remediation plans missing logs, loophole phrases such as "we know enough", "obvious fix", "hardening first", or "logs later".
- Optimization opportunities to inspect: keep the validator heuristic simple and explainable; avoid forcing irrelevant incident ceremony onto small feature work.
- Must-fix threshold: any high-risk remediation plan can pass without root-cause evidence or explicit missing-evidence constraint; any ordinary non-remediation valid plan is broken by the new rule.
- Evidence to record: unit test names, fixture results, and the exact validator error messages.

## Generality Guardrail
- Existing mechanism to reuse: Megaskill plan validation, execution contract, evidence ledger, and agent plan template.
- Similar existing use cases: fulfillment/readback proof, Armageddon mode, dependency/tooling preflight, branch strategy, and generality checks are already enforced generally instead of as one-off advice.
- Recurrence likelihood: high; premature remediation is a recurring risk across live devices, production apps, deployments, auth failures, data pipelines, and network incidents.
- General mechanism to create if none exists: a reusable root-cause gate section plus validator checks for incident/remediation language.
- Specific use case implementation through the mechanism: the DTU outage failure becomes a regression fixture, not a special-case rule hard-coded to `pi4b`.
- One-off justification, if any: none.

## Ordered State and Dashboard
- State ledger path: `.mega/state.jsonl` if implementation spans multiple commits.
- Dashboard output path: `.mega/dashboards/root-cause-gate-remediation.html` if implementation spans multiple phases.
- Open behavior: generate with `--no-open` during noninteractive validation.
- State events to record: plan accepted, instruction edits, validator edits, fixture additions, test pass/fail, final readback.
- Evidence links: `mega_evidence.py` records for validator and unit test commands if this is executed as a full Megaskill implementation.
- Dashboard readback assertions: generated dashboard includes all phases, state events, and evidence references if dashboard generation is used.

## Regression Guardrails
- Planned edit surface:
  - `SKILL.md`
  - `references/execution-contract.md`
  - `references/agent-plan-template.md`
  - `scripts/mega_plan_check.py`
  - `scripts/mega_plan_init.py`
  - `tests/test_plan_check.py`
  - `tests/fixtures/root-cause-gate-missing-bad.md`
  - `tests/fixtures/root-cause-gate-good.md`
- Protected behaviors: existing valid plans remain valid unless they are incident/remediation plans missing the new required root-cause baseline; plan checks stay fast and dependency-free; low-risk feature work is not forced through incident RCA.
- Likely consumers: future Codex agents using Megaskill, lower-level implementation agents, plan authors, and the user relying on Megaskill for serious execution.
- Damage radius: Systemic.
- Branch strategy: Create dedicated branch `megaskill/root-cause-gate` before implementation edits.
- Proof plan: test-first fixture failure, implementation, all plan-check tests, dogfood validation of this plan, and readback of updated instructions/templates.

## Phase 1: Failure Capture

### Subphase 1.1: Add DTU-Inspired Regression Fixtures
- Commit: add root-cause gate fixtures that capture the premature remediation failure.
- Tests: `python3 scripts/mega_plan_check.py tests/fixtures/root-cause-gate-missing-bad.md` should fail; `python3 scripts/mega_plan_check.py tests/fixtures/root-cause-gate-good.md` should pass after validator implementation.
- Success Criteria: the bad fixture clearly represents symptom-to-hardening without forensic logs, and the good fixture shows the intended evidence model.
- Planned Touch Files:
  - `tests/fixtures/root-cause-gate-missing-bad.md`
  - `tests/fixtures/root-cause-gate-good.md`
- Checklist:
  - [ ] Encode the DTU pattern without hard-coding private credentials or secrets.
  - [ ] Include missing Pi logs, service journals, modem/kernel logs, route/DNS state, and cloud readback in the bad fixture's omitted evidence.
  - [ ] Include evidence inventory, hypothesis ranking, missing-evidence policy, and remediation mapping in the good fixture.
  - [ ] Confirm the bad fixture fails for the new reason after validator implementation.

## Phase 2: Instruction And Template Gate

### Subphase 2.1: Update Megaskill Instructions
- Commit: require root-cause baseline before incident remediation.
- Tests: readback with `rg -n "Root-Cause Baseline|pre-remediation|remediation mapping" SKILL.md references`.
- Success Criteria: `SKILL.md` makes the root-cause gate part of the required workflow before remediation plans or mutations.
- Planned Touch Files:
  - `SKILL.md`
  - `references/execution-contract.md`
- Checklist:
  - [ ] Add a pre-remediation root-cause gate to the required workflow.
  - [ ] Define allowed actions before the gate: read-only probes, reversible diagnostics, evidence-preserving collection, and urgent restoration only.
  - [ ] Require explicit separation of proven cause, likely hypothesis, generic hardening, and deployed remediation.
  - [ ] Require missing-evidence constraints when logs or provider state cannot be retrieved.

### Subphase 2.2: Update Agent Plan Template
- Commit: add root-cause baseline fields to lower-level agent plans.
- Tests: `python3 scripts/mega_plan_check.py ROOT_CAUSE_GATE_REMEDIATION_PLAN.md`.
- Success Criteria: future generated plans have a dedicated root-cause section before implementation work.
- Planned Touch Files:
  - `references/agent-plan-template.md`
  - `scripts/mega_plan_init.py`
- Checklist:
  - [ ] Add `Root-Cause Baseline` after research/SOTA or before it if that reads better in the final template.
  - [ ] Add the same section to the generated plan skeleton.
  - [ ] Include evidence inventory, hypothesis ranking, missing evidence, mutation boundary, remediation mapping, and not-done conditions.
  - [ ] Ensure the template still contains all existing required sections.

## Phase 3: Validator Enforcement

### Subphase 3.1: Implement High-Risk Remediation Detection
- Commit: detect incident/remediation plans that require root-cause baseline validation.
- Tests: `python3 -m unittest tests/test_plan_check.py`.
- Success Criteria: the checker identifies live incidents, outages, telemetry gaps, recovery/remediation language, production-adjacent failures, and device/network/service failures without flagging ordinary feature plans.
- Planned Touch Files:
  - `scripts/mega_plan_check.py`
  - `tests/test_plan_check.py`
- Checklist:
  - [ ] Add an explainable regex or section-based heuristic for remediation contexts.
  - [ ] Keep the detection dependency-free and fast.
  - [ ] Add tests for both triggered and non-triggered plans.

### Subphase 3.2: Enforce Root-Cause Baseline Contents
- Commit: require evidence inventory, hypotheses, missing-evidence policy, mutation boundary, and remediation mapping.
- Tests: `python3 -m unittest tests/test_plan_check.py`; targeted `mega_plan_check.py` runs against the good and bad fixtures.
- Success Criteria: high-risk remediation plans fail with specific actionable errors when root-cause analysis is missing or too thin.
- Planned Touch Files:
  - `scripts/mega_plan_check.py`
  - `tests/test_plan_check.py`
  - `tests/fixtures/root-cause-gate-missing-bad.md`
  - `tests/fixtures/root-cause-gate-good.md`
- Checklist:
  - [ ] Add required-section check for `## Root-Cause Baseline` only when remediation detection triggers.
  - [ ] Validate evidence inventory terms.
  - [ ] Validate hypothesis ranking terms.
  - [ ] Validate missing-evidence policy.
  - [ ] Validate mutation boundary.
  - [ ] Validate remediation-to-cause mapping.
  - [ ] Verify error messages point authors to the missing field.

## Phase 4: Dogfood And Handoff

### Subphase 4.1: Run Dogfood Validation
- Commit: validate Megaskill's own remediation plan and regression suite.
- Tests: `python3 scripts/mega_plan_check.py ROOT_CAUSE_GATE_REMEDIATION_PLAN.md`; `python3 -m unittest`.
- Success Criteria: the plan validates, all tests pass, and the new root-cause gate does not regress unrelated Megaskill checks.
- Planned Touch Files:
  - `ROOT_CAUSE_GATE_REMEDIATION_PLAN.md`
- Checklist:
  - [ ] Run the plan checker on this plan.
  - [ ] Run the full skill test suite.
  - [ ] Read back key instruction changes.
  - [ ] Record remaining limitations, especially heuristic false positives/false negatives.
