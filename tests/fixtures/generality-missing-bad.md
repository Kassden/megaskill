# Missing Generality Plan

## GOAL
- Add a one-off script for a recurring workflow.

## Acceptance Criteria
- The script handles the pasted example.

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
- Command: python3 scripts/new_one_off.py fixture.json.
- Evidence to record: command output.

## Armageddon Mode
- Damage-scaled attack scope: small CLI attack scope.
- Edge cases to try: empty input and malformed input.
- Failure modes to simulate: missing file.
- Optimization opportunities to inspect: duplicate scripts.
- Must-fix threshold: crash or wrong exit code.
- Evidence to record: command output.

## Regression Guardrails
- Planned edit surface:
  - `scripts/new_one_off.py`
- Protected behaviors: existing scripts.
- Likely consumers: operators.
- Damage radius: Moderate.
- Proof plan: fixture tests.

## Phase 1: Script

### Subphase 1.1: Add One-Off
- Commit: add one-off script.
- Tests: python3 scripts/new_one_off.py fixture.json.
- Success Criteria: script exits zero.
- Planned Touch Files:
  - `scripts/new_one_off.py`
- Checklist:
  - [ ] Add script.
  - [ ] Run fixture.
