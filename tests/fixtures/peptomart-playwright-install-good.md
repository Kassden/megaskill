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

## Deterministic Real-User Test
- Entry point: `index.html`.
- User workflow: open the landing page and use the primary call to action.
- Stable inputs or fixtures: static local HTML.
- User-observable assertions: hero, navigation, and CTA are visible.
- Command: npx playwright test.
- Evidence to record: Playwright output and screenshots.

## Armageddon Mode
- Damage-scaled attack scope: moderate landing-page attack scope.
- Edge cases to try: mobile width, long text, missing image, repeated CTA click.
- Failure modes to simulate: failed asset load and narrow viewport.
- Optimization opportunities to inspect: asset weight and layout stability.
- Must-fix threshold: broken CTA, overlap, blank page, or console error.
- Evidence to record: screenshots, console logs, and test output.

## Generality Guardrail
- Existing mechanism to reuse: none found.
- Similar existing use cases: future static landing pages.
- Recurrence likelihood: medium because landing pages recur.
- General mechanism to create if none exists: shared Playwright static-page smoke helper.
- Specific use case implementation through the mechanism: PEPTOMART uses the shared helper.
- One-off justification, if any: none.

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
