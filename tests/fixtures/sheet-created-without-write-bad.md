# Sheet Creation Without Fulfillment

## GOAL
- Create a quote-derived cost estimation spreadsheet from all source quotes.

## Acceptance Criteria
- The Google Sheet contains quote-derived rows and totals from every source quote.

## Research
- Built-in options: use existing Google Workspace tools.
- Off-the-shelf options: Google Sheets API.
- Official / standards sources: Google Sheets values update docs.

## SOTA, Standards, And Best Practices
- Current SOTA / prior art: write structured rows through Sheets values API and verify by export.
- Official docs, standards, specs, or platform guidance: Google Sheets API docs.
- Mature libraries, frameworks, or built-in mechanisms: existing workspace tool family.
- Best-practice constraints to integrate: idempotent row writes and exported CSV comparison.
- Rejected approaches: copying a template without data writes.
- Implementation decision: use the sheet update API then export.

## Dependency and Tooling Preflight
- Required verification tools: Google Workspace tool calls and Drive export.
- Existing tooling found: googleWorkspaceOps and Drive export.
- Install or repair commands: no install is needed.
- Browser/runtime binaries: none.
- Real blockers that would prevent setup: credential, auth, external outage.

## Deterministic Real-User Test
- Entry point: production chat prompt.
- User workflow: ask for quote-derived cost estimation.
- Stable inputs or fixtures: recorded quote files.
- User-observable assertions: new sheet link is returned.
- Command: production /api/chat prompt.
- Evidence to record: stream output.

## Fulfillment and Readback Proof
- Requested final user-visible result: new Google Sheet in the cost estimation folder.
- Required write/mutation operation: create the sheet from template.
- Readback surface: Drive export.
- Expected content, rows, fields, counts, or behavior: exported CSV opens.
- Command or tool call evidence: googleDriveWorkflow.
- Not-done conditions: missing sheet link.

## Armageddon Mode
- Damage-scaled attack scope: systemic agent-tool workflow attack scope.
- Edge cases to try: disabled Sheets API, missing quotes, duplicate quotes, empty exports.
- Failure modes to simulate: failed mutation and stale template output.
- Optimization opportunities to inspect: unnecessary template copy.
- Must-fix threshold: missing quote rows or missing write call.
- Evidence to record: stream tools, export, and CSV comparison.

## Generality Guardrail
- Existing mechanism to reuse: workspace artifact workflow.
- Similar existing use cases: document and spreadsheet generation.
- Recurrence likelihood: high for external artifacts.
- General mechanism to create if none exists: fulfillment readback verifier.
- Specific use case implementation through the mechanism: sheet workflow uses readback verifier.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface:
  - `src/tools/workspace.ts`
- Protected behaviors: Drive file creation and quote extraction.
- Likely consumers: production chat users.
- Damage radius: Systemic.
- Branch strategy: Create dedicated branch `mega/sheet-write-fulfillment` before editing.
- Proof plan: production tool stream plus exported sheet content comparison.

## Phase 1: Sheet Workflow

### Subphase 1.1: Create Cost Sheet
- Commit: create quote-derived sheet workflow.
- Tests: production /api/chat prompt and Drive export.
- Success Criteria: sheet link exists.
- Planned Touch Files:
  - `src/tools/workspace.ts`
- Checklist:
  - [ ] Create sheet.
  - [ ] Export sheet.
