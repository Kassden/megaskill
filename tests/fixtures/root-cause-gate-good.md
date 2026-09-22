# Evidence-First Live Incident Remediation Plan

## GOAL
- Diagnose a live Raspberry Pi, 4G, Tailscale, exporter, and Influx telemetry gap before implementing bounded remediation.

## Acceptance Criteria
- Root cause is separated from hypotheses, unavailable logs are named, and every mitigation maps to a proven or hypothesized failure class.

## Research
- Built-in options: inspect the exporter health endpoint, journals, dashboard Influx configuration, and existing alert worker.
- Off-the-shelf options: use SQLite WAL only after evidence shows memory-only buffering is a relevant failure class.
- Official / standards sources: SRE incident timeline and postmortem practice, plus local operational docs.

## Root-Cause Baseline
- Trigger scope: live device outage, production-adjacent telemetry gap, missing data, and remediation request.
- Minimum evidence inventory: incident timeline, affected surface, current health, `tailscaled` logs/journals, exporter journal, kernel USB modem logs, route/DNS state, Influx metrics/readbacks, recent changes, config/state, external dependencies, and user-observed facts.
- Hypothesis model: candidate causes are ranked as proven, likely, possible, unlikely, or disproven, with evidence and counter-evidence for modem power loss, carrier loss, tailscaled failure, exporter failure, route/DNS failure, and cloud write failure.
- Missing-evidence policy: unavailable outage-window logs are listed with why they cannot be obtained, who or what could supply them, whether collection is destructive, and how uncertainty constrains remediation.
- Mutation boundary: before this baseline is complete, actions are read-only probes, reversible diagnostics, evidence-preserving collection, and urgent restoration to reduce active harm.
- Remediation mapping: each proposed fix is mapped to a failure class; durable buffering addresses verified memory-only loss risk, stale alerts address cloud readback silence, and watchdog actions are labeled risk reduction unless modem failure is proven.
- Not-done conditions: symptom-to-hardening without outage-window evidence, missing uncertainty, or calling generic hardening the root-cause fix.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: evidence-first incident response separates restoration, root cause, and corrective actions.
- Official docs, standards, specs, or platform guidance: SRE postmortem and operational excellence guidance.
- Mature libraries, frameworks, or built-in mechanisms: existing Megaskill state/evidence ledgers, exporter tests, and dashboard tests.
- Best-practice constraints to integrate: no live mutation before the evidence gate unless urgent restoration is required.
- Rejected approaches: implementing broad hardening before log collection.
- Implementation decision: collect evidence first, then implement only mapped mitigations.

## Dependency and Tooling Preflight
- Required verification tools: Tailscale CLI, journalctl, curl, Python unittest, Node tests, and Influx readback.
- Existing tooling found: exporter tests and dashboard tests.
- Install or repair commands: no install is needed.
- Browser/runtime binaries: none.
- Real blockers that would prevent setup: approval, credential, incompatible platform, external outage, destructive action, or product decision.

## Deterministic Real-User Test
- Entry point: `scripts/dtu-health-check.mjs`.
- User workflow: operator runs health check after root-cause evidence is collected.
- Stable inputs or fixtures: fake collector and fake Influx provider.
- User-observable assertions: status separates management, collector, cloud write, dashboard read, and backlog.
- Command: `python3 -m unittest`.
- Evidence to record: test output and readback.

## Fulfillment and Readback Proof
- Requested final user-visible result: evidence-backed remediation plan and mapped hardening.
- Required write/mutation operation: update plan and then update mapped implementation files.
- Readback surface: validator output, health check output, and Influx readback.
- Expected content, rows, fields, counts, or behavior: root-cause baseline exists, mapped mitigations exist, and durable rows drain with readback.
- Command or tool call evidence: plan check, tests, and health check.
- Not-done conditions: missing root-cause baseline, unmapped generic hardening, or no readback.

## Armageddon Mode
- Damage-scaled attack scope: systemic live telemetry path.
- Edge cases to try: unavailable logs, empty data, duplicate writes, modem offline, route failure, stale cloud readback, and repeated watchdog run.
- Failure modes to simulate: downstream failure, retention gap, process restart, and bad config.
- Optimization opportunities to inspect: duplicate diagnostics and slow readbacks.
- Must-fix threshold: false root-cause claim or live mutation before evidence gate.
- Evidence to record: fixture results and command output.

## Generality Guardrail
- Existing mechanism to reuse: Megaskill root-cause baseline, evidence ledger, and validator.
- Similar existing use cases: deployment incidents, auth failures, telemetry gaps, and live device failures.
- Recurrence likelihood: high.
- General mechanism to create if none exists: reusable root-cause gate.
- Specific use case implementation through the mechanism: DTU incident plan uses the root-cause gate.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface: exporter and dashboard telemetry files.
- Protected behaviors: existing dashboard alerts and exporter telemetry.
- Likely consumers: operators and dashboard users.
- Damage radius: Systemic.
- Branch strategy: Create dedicated branch `dtu-resilience-hardening`.
- Proof plan: root-cause gate, unit tests, health check, and readback.

## Phase 1: Evidence

### Subphase 1.1: Collect Forensic Bundle
- Commit: record evidence-first diagnostic bundle.
- Tests: `python3 -m unittest`.
- Success Criteria: hypotheses are ranked and missing evidence is constrained.
- Planned Touch Files:
  - `docs/incident-root-cause.md`
- Checklist:
  - [ ] Collect logs and readbacks.
  - [ ] Rank hypotheses.

