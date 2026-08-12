# Weak Verification Plan

## GOAL
- Ship a CLI tool.

## Acceptance Criteria
- The CLI runs.

## Research
- Built-in options: use current scripts.
- Off-the-shelf options: none.
- Official / standards sources: none.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: CLI tools should prove help, invalid input, and fixture behavior.
- Official docs, standards, specs, or platform guidance: Python argparse and unittest docs.
- Mature libraries, frameworks, or built-in mechanisms: Python unittest.
- Best-practice constraints to integrate: exact exit code and stdout assertions.
- Rejected approaches: manual inspection.
- Implementation decision: use unittest and command fixtures.

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

## Fulfillment and Readback Proof
- Requested final user-visible result: CLI prints expected output.
- Required write/mutation operation: write CLI file.
- Readback surface: stdout and exit code.
- Expected content, rows, fields, counts, or behavior: exact output text and zero exit.
- Command or tool call evidence: python3 tool.py fixture.json.
- Not-done conditions: created command without output assertion.

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
