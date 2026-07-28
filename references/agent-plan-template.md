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
- Do not create a subphase without commit, tests, success criteria, planned touch files, and checklist.
- Make every subphase independently valid unless explicitly impossible.
- Name the exact evidence the lower-level agent must produce.
- For UI/browser-facing work, missing Playwright or browser binaries must be handled as an install/repair subphase unless a real blocker prevents setup.
