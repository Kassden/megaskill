# Weak Verification Plan

## GOAL
- Ship a CLI tool.

## Acceptance Criteria
- The CLI runs.

## Research
- Built-in options: use current scripts.
- Off-the-shelf options: none.
- Official / standards sources: none.

## Dependency and Tooling Preflight
- Required verification tools: Python unittest.
- Existing tooling found: unittest.
- Install or repair commands: no install is needed.
- Browser/runtime binaries: none.
- Real blockers that would prevent setup: approval.

## Deterministic Real-User Test
- Entry point: CLI command.
- User workflow: run command with fixture.
- Stable inputs or fixtures: local fixture.
- User-observable assertions: stdout and exit code.
- Command: python3 tool.py fixture.json.
- Evidence to record: command output.

## Armageddon Mode
- Damage-scaled attack scope: happy path only.
- Edge cases to try: none.
- Failure modes to simulate: none.
- Optimization opportunities to inspect: none.
- Must-fix threshold: crash.
- Evidence to record: command output.

## Generality Guardrail
- Existing mechanism to reuse: none found.
- Similar existing use cases: none.
- Recurrence likelihood: low.
- General mechanism to create if none exists: not needed.
- Specific use case implementation through the mechanism: direct CLI.
- One-off justification, if any: isolated.

## Regression Guardrails
- Planned edit surface:
  - `tool.py`
- Protected behaviors: CLI output.
- Likely consumers: operators.
- Damage radius: Small.
- Proof plan: happy path only.

## Phase 1: CLI

### Subphase 1.1: Add Command
- Commit: add command.
- Tests: python3 tool.py fixture.json.
- Success Criteria: command exits zero.
- Planned Touch Files:
  - `tool.py`
- Checklist:
  - [ ] Add command.
  - [ ] Run happy path only.
