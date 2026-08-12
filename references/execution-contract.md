# Megaskill Execution Contract

## Pre-Edit Declaration

Before mutating files, state:

```text
Megaskill Guardrail
- Goal:
- Acceptance criteria:
- Planned edit surface:
- Protected behaviors:
- Likely consumers:
- Damage radius:
- Proof plan:
- Atomic units:
- Commit plan:
- SOTA/standards decision:
- Fulfillment proof:
```

## Damage Radius

Use the highest applicable tier:

- Small: local implementation, few consumers, obvious failures.
- Moderate: shared helper, reused UI, API handler, query, parser, or config.
- Large: public contract, schema, deploy/runtime surface, broad refactor.
- Systemic: auth, startup, data migration, production deploy, high-fan-out path.

Scale proof to radius:

- Small: direct check.
- Moderate: direct check plus one adjacent flow.
- Large: contract-aware checks plus build/integration where available.
- Systemic: strongest available end-to-end or live verification plus rollback awareness.

## SOTA, Standards, And Best-Practices Research

Before building or adding a capability, research the current state of the art and the relevant standards for that kind of work.

Required coverage:

- Current SOTA or prior art for the feature, workflow, interface, integration, or testing method.
- Official docs, standards, specs, protocol docs, platform guidance, or security/accessibility/performance rules that govern the work.
- Mature libraries, frameworks, APIs, or built-in platform mechanisms that should be preferred over hand-rolled logic for well-known domains.
- Best-practice constraints that will be integrated into the design and implementation.
- Rejected approaches and why they are not the right fit.
- The implementation decision that follows from the research.

Rules:

- Integrate selected standards and best practices into the implementation and tests; do not merely cite them.
- Prefer established general mechanisms, official APIs, mature libraries, and project-standard patterns over bespoke solutions.
- When network access is unavailable, use repo docs, installed package docs, and local source as the fallback, state the limitation, and refresh research when network access becomes available.
- For high-risk domains such as auth, payments, medical, legal, financial, deployment, data migration, browser automation, or platform integrations, prefer primary sources such as official docs, standards, specs, and maintained project docs.

## Dependency And Tooling Preflight

Missing verification tooling is an executable setup task, not a reason to skip relevant checks.

Before editing, identify the strongest verification surface implied by the work and confirm the local tooling needed for it. If the tool is absent, install or repair it in the project-local way unless a real blocker prevents that.

Examples:

- UI, browser, visual, responsive, canvas, or 3D work: install project-local Playwright or the repo's existing browser-test stack, install required browser binaries, then run browser smoke and screenshot/visual/pixel checks appropriate to the change.
- API, route, SDK, or contract work: install missing test dependencies if the repo declares them, then run unit or contract tests plus an endpoint/CLI smoke where runnable.
- CLI or script work: run help, invalid-input, fixture, and real-sample checks.
- Docs, PDF, images, or generated artifacts: render or open the artifact, inspect generated output, and verify source/readback evidence.
- Deployment work: verify build status, deployment status, and the deployed URL/API unless auth or provider outage blocks it.
- Live-device or production-adjacent work: perform the strongest read-only or smoke check available before writes, and name credentials or access as blockers if missing.

Do not use "not installed", "not configured", or "no test script" as final verification reasons unless setup was attempted, rejected by approval policy, or blocked by credentials, platform incompatibility, destructive-action boundaries, or an external outage.

## Deterministic Real-User Experience Test

For any interface, app, CLI, tool, workflow, agent surface, or user-facing path, first create or run a deterministic real-user experience test before broader verification.

A deterministic real-user experience test must:

- start from the user's actual entry point
- perform the core workflow as a real user would
- use stable seeded inputs, recorded fixtures, or deterministic local state
- assert user-observable outcomes, not only internals
- run repeatably without timing luck
- record evidence with `scripts/mega_evidence.py`

Examples:

- Web app: route entry -> user action -> visible UI result, verified with Playwright or the repo's browser-test equivalent.
- CLI/tool: command plus fixture input -> exact stdout/stderr/exit code.
- API-backed tool: request fixture -> exact response shape and side-effect/readback check.
- Docs/artifact: source -> render/open/readback evidence.
- Agent/tool workflow: task fixture -> deterministic structured result or output contract.

## Fulfillment And Readback Proof

Do not confuse progress with fulfillment. For output-producing workflows, Megaskill requires proof that the final user-visible result contains the requested content or side effect.

Required when work creates, mutates, exports, deploys, emails, syncs, indexes, imports, transforms, routes through agent tools, or writes to an external system:

- Name the requested final artifact, record, deployment, message, sheet, document, file, database row, API side effect, or user-visible state.
- Name the required write or mutation operation, not just discovery, routing, copying, or creation.
- Read back the final result through the same surface a user or downstream system would use when practical.
- Compare the readback against expected content, rows, fields, counts, formulas, status, metadata, or acceptance criteria.
- Treat missing write permissions, disabled APIs, failed mutation calls, partial exports, stale deployments, and template-only outputs as `not done` unless a real blocker prevents completion.

Examples:

- Google Sheet cost estimation: create/copy template -> extract quote rows -> call the sheet value update operation -> export/read the sheet -> assert quote-derived rows, totals, and expected columns are present.
- Document generation: render/export -> open/read text -> assert required clauses, tables, and values exist.
- Data import: run import -> query counts and sample rows -> assert dedupe and field mappings.
- Agent workflow: tool route selected -> required mutation tool called -> final external artifact read back and compared.
- Deployment: deploy -> verify commit served -> live route/API smoke proves changed behavior.

## Armageddon Mode

Armageddon mode is an adversarial verification pass. It tries to break the result, expose weaknesses, and identify optimization opportunities before final handoff.

Scale Armageddon by damage radius:

- Small: 3-5 adversarial checks against the changed surface.
- Moderate: changed surface plus one adjacent consumer or workflow.
- Large/Systemic: full adversarial pass across entry points, contracts, and live/deploy surfaces where available.

Use the relevant attack list:

- UI/app: mobile, narrow, desktop, long text, empty data, loading, error, disabled states, repeated clicks, reload/back/forward, console errors, failed network calls, keyboard-only path where relevant, screenshots.
- CLI/tool: `--help`, missing args, invalid args, malformed input, empty input, large input when cheap, wrong cwd, missing config/env, repeated run/idempotency.
- API/backend: missing fields, wrong types, unknown fields, empty arrays, oversized input, unauthorized request, wrong tenant/user ID, replay/idempotency, downstream failure when practical, stable error shape.
- Data/query: empty result, duplicates, missing fields, timezone/boundary dates, very old/new dates, count/shape checks.
- Deploy/live: route smoke, API smoke, auth/protection caveat, stale deployment check, rollback awareness.

Armageddon output must name:

- surface attacked
- weaknesses found
- bugs found
- optimization opportunities
- edge cases tried
- evidence
- must-fix-before-done items
- safe-to-defer items

## Generality Guardrail

Before implementing, check whether the request is one instance of a broader repeated pattern.

Do not create one-off tools, routes, scripts, prompts, fixtures, UI components, validators, or services when a general mechanism should own the behavior.

Prefer a general mechanism when:

- two or more similar things already exist
- the new thing duplicates behavior with different names
- the use case is likely to recur
- future agents or users would not know which duplicate to use
- the solution would create a parallel workflow

Rules:

- Use the existing general mechanism when one exists.
- If no general mechanism exists and recurrence is likely, create the general mechanism first.
- Implement the specific request through that general mechanism.
- Only make a one-off when the use case is truly isolated, low-risk, and unlikely to recur.
- Document why a one-off is acceptable if choosing one.

Forbidden:

- Do not hard-code to the pasted example when the user is asking for a reusable tool, workflow, service, or test surface.
- Do not add a bespoke helper if a shared helper should own it.
- Do not create many narrow variants that do the same thing.

## Verification Matrix

Choose proof by work type before editing:

| Work type | Required proof floor |
| --- | --- |
| UI/browser | Browser smoke for affected routes, plus screenshot or accessibility/layout inspection when visual behavior changed. |
| Visual/layout | Desktop and mobile screenshots; verify text does not overlap or overflow. |
| Canvas/3D/game | Browser smoke plus nonblank canvas pixel check and interaction/motion check. |
| API/route | Unit or contract tests plus endpoint smoke when locally runnable. |
| Shared helper/library | Targeted tests plus at least one adjacent consumer check. |
| CLI/script | `--help`, invalid input, fixture, and real-sample check. |
| Docs/artifact | Render/open/readback check; file existence alone is insufficient. |
| Data/query | Fixture or golden check plus query/count/shape verification. |
| External write/tool workflow | Mutation call plus final readback of user-visible artifact or state; creation/copy/routing alone is insufficient. |
| Deploy/live URL | Build/deploy status plus live URL or API smoke, with auth caveats stated precisely. |
| Live device/production | Read-only probe first; write/switch actions require explicit approval and rollback awareness. |

For interface, app, CLI, tool, workflow, and user-facing work, this proof floor is in addition to the deterministic real-user experience test.

For high-risk, API/backend, UI/app, CLI/tool, data/query, deploy/live, and production-adjacent work, include an Armageddon pass scaled to the damage radius.

## Execution Loop

For each subphase:

1. Re-read the plan.
2. Confirm the subphase goal and edit surface.
3. Implement only that unit.
4. Run the deterministic real-user test when relevant.
5. Run fulfillment/readback proof when the work produces or mutates an artifact, record, deployment, external system, or agent-tool result.
6. Run the declared tests and Armageddon checks.
7. Record evidence.
8. Check scope drift.
9. Stage only that unit.
10. Check atomicity.
11. Commit when commits are in scope.
12. Continue to the next executable subphase.

## Real Blockers

Stop only for:

- missing credentials, remote, deploy target, or required auth
- destructive action needing approval
- external service outage
- incompatible platform or unavailable runtime after attempted setup
- conflicting user instructions
- material product choice that cannot be inferred
- verification failure that requires user/environment action

Everything else should be inspected, fixed, verified, and continued.
