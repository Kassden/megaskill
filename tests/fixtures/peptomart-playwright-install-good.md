# PEPTOMART Browser Verification

## GOAL
- Build a static landing page and prove the browser output.

## Acceptance Criteria
- Desktop and mobile browser smoke tests pass.

## Research
- Built-in options: static HTML, CSS, and npm scripts.
- Off-the-shelf options: Playwright.
- Official / standards sources: Playwright install behavior.

## Dependency and Tooling Preflight
- Required verification tools: Playwright browser smoke, screenshots, and Chromium.
- Existing tooling found: package manifest without Playwright.
- Install or repair commands: npm install and npx playwright install chromium.
- Browser/runtime binaries: Chromium.
- Real blockers that would prevent setup: approval, credential, external outage, incompatible platform.

## Regression Guardrails
- Planned edit surface:
  - `index.html`
  - `styles.css`
  - `tests/smoke.spec.ts`
- Protected behaviors: static hosting.
- Likely consumers: landing page visitors.
- Damage radius: Moderate.
- Proof plan: Playwright browser smoke and screenshot checks.

## Phase 1: UI

### Subphase 1.1: Add Page And Smoke
- Commit: add PEPTOMART page and browser smoke.
- Tests: npx playwright test.
- Success Criteria: Playwright passes after local browser installation.
- Planned Touch Files:
  - `index.html`
  - `styles.css`
  - `tests/smoke.spec.ts`
- Checklist:
  - [ ] Add static page.
  - [ ] Install Playwright and Chromium.
  - [ ] Run browser smoke.
