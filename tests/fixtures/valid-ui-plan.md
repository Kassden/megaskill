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
