# Premature Live Incident Remediation Plan

## GOAL
- Implement DTU resilience hardening after a live Raspberry Pi, 4G, Tailscale, and Influx telemetry gap.

## Acceptance Criteria
- Durable buffering, stale telemetry alerts, and a watchdog are implemented locally.

## Research
- Built-in options: inspect existing exporter and dashboard code.
- Off-the-shelf options: use SQLite and existing alert infrastructure.
- Official / standards sources: use local operational docs.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: resilient telemetry systems use durable queues and stale-data alerts.
- Official docs, standards, specs, or platform guidance: local exporter and dashboard contracts.
- Mature libraries, frameworks, or built-in mechanisms: SQLite WAL and existing cron worker.
- Best-practice constraints to integrate: bounded retries and readback after cloud writes.
- Rejected approaches: memory-only queue.
- Implementation decision: add durable spool, watchdog, and dashboard stale-data alerts.

## Dependency and Tooling Preflight
- Required verification tools: Python unittest and Node tests.
- Existing tooling found: exporter tests and dashboard tests.
- Install or repair commands: no install is needed.
- Browser/runtime binaries: none.
- Real blockers that would prevent setup: approval, credential, incompatible platform, external outage, destructive action, or product decision.

## Deterministic Real-User Test
- Entry point: `scripts/dtu-health-check.mjs`.
- User workflow: run the health check after implementing the mitigation.
- Stable inputs or fixtures: fake collector and fake Influx provider.
- User-observable assertions: status shows management, collector, cloud write, dashboard read, and backlog.
- Command: `python3 -m unittest`.
- Evidence to record: test output.

## Fulfillment and Readback Proof
- Requested final user-visible result: local resilience hardening for the live incident.
- Required write/mutation operation: update exporter and dashboard code.
- Readback surface: unit tests and health check output.
- Expected content, rows, fields, counts, or behavior: durable rows drain and stale telemetry alerts render.
- Command or tool call evidence: Python and Node tests.
- Not-done conditions: no tests.

## Armageddon Mode
- Damage-scaled attack scope: systemic live telemetry path.
- Edge cases to try: empty queue, failed Influx, modem offline, repeated watchdog run.
- Failure modes to simulate: downstream failure and process restart.
- Optimization opportunities to inspect: duplicate writes.
- Must-fix threshold: data loss or unbounded retry.
- Evidence to record: fixture results.

## Generality Guardrail
- Existing mechanism to reuse: exporter writer and dashboard alert worker.
- Similar existing use cases: telemetry write and alert dispatch.
- Recurrence likelihood: high.
- General mechanism to create if none exists: shared durable spool.
- Specific use case implementation through the mechanism: DTU telemetry uses the durable spool.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface: exporter and dashboard telemetry files.
- Protected behaviors: existing dashboard alerts and exporter telemetry.
- Likely consumers: operators and dashboard users.
- Damage radius: Systemic.
- Branch strategy: Create dedicated branch `dtu-resilience-hardening`.
- Proof plan: unit tests and local health check.

## Phase 1: Hardening

### Subphase 1.1: Implement Durable Spool
- Commit: add durable telemetry spool.
- Tests: `python3 -m unittest`.
- Success Criteria: rows persist and drain.
- Planned Touch Files:
  - `telemetry_spool.py`
- Checklist:
  - [ ] Add SQLite spool.
  - [ ] Run tests.

