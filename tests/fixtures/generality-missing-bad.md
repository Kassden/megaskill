# Missing Generality Plan

## GOAL
- Add a one-off script for a recurring workflow.

## Acceptance Criteria
- The script handles the pasted example.

## Research
- Built-in options: use current scripts.
- Off-the-shelf options: none.
- Official / standards sources: none.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: recurring scripts should use shared parser and fixture tests.
- Official docs, standards, specs, or platform guidance: Python argparse and unittest docs.
- Mature libraries, frameworks, or built-in mechanisms: current scripts and unittest.
- Best-practice constraints to integrate: reusable workflow mechanism.
- Rejected approaches: hard-coded one-off script.
- Implementation decision: inspect shared script mechanisms first.

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

## Fulfillment and Readback Proof
- Requested final user-visible result: script output handles recurring workflow fixture.
- Required write/mutation operation: write script behavior.
- Readback surface: stdout and exit code.
- Expected content, rows, fields, counts, or behavior: expected fields are emitted.
- Command or tool call evidence: python3 scripts/new_one_off.py fixture.json.
- Not-done conditions: created script without fixture readback.

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
- Branch strategy: Current branch is acceptable for this moderate scoped change after status check.
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
