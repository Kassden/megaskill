# Agent Plan Template

Use this shape for lower-level agent plans.

```markdown
# <Plan Title>

## GOAL
- <measurable end state>

## Acceptance Criteria
- <what proves success>

## Runtime Contract And Decision Record Policy
- Task mode: plan/review/execute/monitor; execution must be authorized.
- Exact obligation IDs and relevant proof artifacts:
- Pinned actual-outcome assertions for every obligation (ACCEPTANCE.json), including independent review for qualitative criteria:
- Actual session prompt/tool/Stop invocation proof and unsupported-host fallback:
- Material decisions requiring alternatives/self-critique and ADR promotion:
- Delegated roles, allowed edit surfaces, and native close/readback requirements:

## Research
- Built-in options:
- Off-the-shelf options:
- Official / standards sources:

## Root-Cause Baseline
- Trigger scope:
- Minimum evidence inventory:
- Hypothesis model:
- Missing-evidence policy:
- Mutation boundary:
- Remediation mapping:
- Not-done conditions:

## SOTA, Standards, And Best Practices
- Current SOTA / prior art:
- Official docs, standards, specs, or platform guidance:
- Mature libraries, frameworks, or built-in mechanisms:
- Best-practice constraints to integrate:
- Rejected approaches:
- Implementation decision:

## Dependency and Tooling Preflight
- Required verification tools:
- Existing tooling found:
- Install or repair commands:
- Browser/runtime binaries:
- Real blockers that would prevent setup:

## Deterministic Real-User Test
- Entry point:
- User workflow:
- Stable inputs or fixtures:
- User-observable assertions:
- Command:
- Evidence to record:

## Fulfillment and Readback Proof
- Requested final user-visible result:
- Required write/mutation operation:
- Readback surface:
- Expected content, rows, fields, counts, or behavior:
- Command or tool call evidence:
- Not-done conditions:

## Armageddon Mode
- Damage-scaled attack scope:
- Edge cases to try:
- Failure modes to simulate:
- Optimization opportunities to inspect:
- Must-fix threshold:
- Evidence to record:

## Generality Guardrail
- Existing mechanism to reuse:
- Similar existing use cases:
- Recurrence likelihood:
- General mechanism to create if none exists:
- Specific use case implementation through the mechanism:
- One-off justification, if any:

## Ordered State and Dashboard
- State ledger path:
- Dashboard output path:
- Open behavior:
- State events to record:
- Evidence links:
- Dashboard readback assertions:

## Regression Guardrails
- Planned edit surface:
- Protected behaviors:
- Likely consumers:
- Damage radius:
- Branch strategy:
- Proof plan:

## Phase 1: <name>

### Subphase 1.1: <name>
- Commit: <single commit intent for this subphase>
- Tests: <specific tests/checks>
- Success Criteria: <what proves this subphase advances the goal>
- Planned Touch Files:
  - `<path>`
- Checklist:
  - [ ] <work item>
  - [ ] <verification item>
```

Rules:

- Do not create a phase without subphases.
- Do not create a plan without dependency/tooling preflight.
- Do not create a plan without SOTA/standards research, deterministic real-user test, fulfillment/readback proof, Armageddon mode, and generality guardrail sections.
- For incidents, outages, live infrastructure, production-adjacent systems, telemetry gaps, data loss, auth/deployment/device/network/service failures, recovery work, or remediation work, do not create a plan without a `Root-Cause Baseline`.
- A root-cause baseline must inventory evidence, rank hypotheses, name missing evidence and uncertainty, declare the mutation boundary, and map every remediation to a proven or hypothesized failure class.
- For multi-phase or multi-agent plans, include ordered state and dashboard fields or explicitly justify why the plan is too small to need them.
- For execution, register exact obligations and use current linked test/readback proof. Stop hooks and final-gate must refer to the same contract. Record material decisions before consequential action, and promote durable accepted decisions to ADRs.
- Delegate only useful independent work. Bound children, collect results, call native close_agent, and record closure receipts. No mandatory six-agent roster.
- Do not create a subphase without commit, tests, success criteria, planned touch files, and checklist.
- Make every subphase independently valid unless explicitly impossible.
- Name the exact evidence the lower-level agent must produce.
- For UI/browser-facing work, missing Playwright or browser binaries must be handled as an install/repair subphase unless a real blocker prevents setup.
- For artifact, data-write, integration, deployment, or agent-tool workflows, creation/copy/routing is not success; require mutation proof and final readback of the user-visible result.
- If no general mechanism exists and the behavior is likely to recur, create the general mechanism first and implement the specific use case through it.
- If damage radius is Large or Systemic, create or use a dedicated work branch before implementation unless a real blocker or explicit user instruction prevents branching.
