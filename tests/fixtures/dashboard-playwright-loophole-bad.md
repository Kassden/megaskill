# Dashboard Benchmark Plan

## GOAL
- Benchmark a dashboard UI optimization.

## Acceptance Criteria
- Browser/API behavior is compared against main.

## Research
- Built-in options: Next.js dev server.
- Off-the-shelf options: Playwright only if already available; otherwise use Node probes.
- Official / standards sources: Next.js cache docs.

## Dependency and Tooling Preflight
- Required verification tools: browser smoke.
- Existing tooling found: unknown.
- Install or repair commands: no install is needed.
- Browser/runtime binaries: none.
- Real blockers that would prevent setup: approval.

## Deterministic Real-User Test
- Entry point: `/`.
- User workflow: load dashboard.
- Stable inputs or fixtures: recorded API fixture.
- User-observable assertions: dashboard status visible.
- Command: node scripts/benchmark.mjs.
- Evidence to record: benchmark output.

## Armageddon Mode
- Damage-scaled attack scope: moderate dashboard attack scope.
- Edge cases to try: empty data and narrow viewport.
- Failure modes to simulate: failed status request.
- Optimization opportunities to inspect: repeated requests.
- Must-fix threshold: broken dashboard render.
- Evidence to record: benchmark output.

## Generality Guardrail
- Existing mechanism to reuse: benchmark helper.
- Similar existing use cases: dashboard query audits.
- Recurrence likelihood: high.
- General mechanism to create if none exists: shared request counter.
- Specific use case implementation through the mechanism: dashboard benchmark.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface:
  - `scripts/benchmark.mjs`
- Protected behaviors: dashboard render.
- Likely consumers: dashboard users.
- Damage radius: Large.
- Proof plan: browser smoke when possible.

## Phase 1: Benchmark

### Subphase 1.1: Count Requests
- Commit: add benchmark.
- Tests: node scripts/benchmark.mjs.
- Success Criteria: counts are reported.
- Planned Touch Files:
  - `scripts/benchmark.mjs`
- Checklist:
  - [ ] Add benchmark.
  - [ ] Run benchmark.
