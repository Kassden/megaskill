# Agent Plan Template

Use this shape for lower-level agent plans.

```markdown
# <Plan Title>

## GOAL
- <measurable end state>

## Acceptance Criteria
- <what proves success>

## Research
- Built-in options:
- Off-the-shelf options:
- Official / standards sources:

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

## Regression Guardrails
- Planned edit surface:
- Protected behaviors:
- Likely consumers:
- Damage radius:
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
- Do not create a plan without deterministic real-user test, Armageddon mode, and generality guardrail sections.
- Do not create a subphase without commit, tests, success criteria, planned touch files, and checklist.
- Make every subphase independently valid unless explicitly impossible.
- Name the exact evidence the lower-level agent must produce.
- For UI/browser-facing work, missing Playwright or browser binaries must be handled as an install/repair subphase unless a real blocker prevents setup.
- If no general mechanism exists and the behavior is likely to recur, create the general mechanism first and implement the specific use case through it.
