# Valid UI Plan

## GOAL
- Ship a browser UI change with proof.

## Acceptance Criteria
- Browser route renders on desktop and mobile.

## Research
- Built-in options: use existing npm scripts.
- Off-the-shelf options: use Playwright.
- Official / standards sources: check framework docs.

## Dependency and Tooling Preflight
- Required verification tools: Playwright browser smoke and screenshots.
- Existing tooling found: none yet.
- Install or repair commands: npm install and npx playwright install chromium.
- Browser/runtime binaries: Chromium.
- Real blockers that would prevent setup: approval, credential, external outage, incompatible platform.

## Deterministic Real-User Test
- Entry point: `/dashboard`.
- User workflow: load dashboard and open the primary panel.
- Stable inputs or fixtures: recorded fixture data.
- User-observable assertions: panel title and status are visible.
- Command: npx playwright test.
- Evidence to record: Playwright output and screenshot.

## Armageddon Mode
- Damage-scaled attack scope: moderate UI attack scope.
- Edge cases to try: narrow viewport, long text, empty fixture, failed network.
- Failure modes to simulate: disabled controls and network error.
- Optimization opportunities to inspect: repeated requests and layout churn.
- Must-fix threshold: broken primary workflow, console error, or overlapping text.
- Evidence to record: screenshots, console logs, and test output.

## Generality Guardrail
- Existing mechanism to reuse: existing dashboard test helpers.
- Similar existing use cases: other dashboard route smoke tests.
- Recurrence likelihood: high for future UI workflows.
- General mechanism to create if none exists: shared Playwright smoke helper.
- Specific use case implementation through the mechanism: dashboard route uses shared helper.
- One-off justification, if any: none.

## Regression Guardrails
- Planned edit surface:
  - `src/page.tsx`
- Protected behaviors: routing.
- Likely consumers: web users.
- Damage radius: Moderate.
- Proof plan: Playwright browser smoke and screenshot checks.

## Phase 1: UI

### Subphase 1.1: Render Route
- Commit: render route safely.
- Tests: npx playwright test.
- Success Criteria: desktop and mobile smoke pass.
- Planned Touch Files:
  - `src/page.tsx`
- Checklist:
  - [ ] Change route.
  - [ ] Run Playwright.
