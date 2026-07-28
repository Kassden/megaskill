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
| Deploy/live URL | Build/deploy status plus live URL or API smoke, with auth caveats stated precisely. |
| Live device/production | Read-only probe first; write/switch actions require explicit approval and rollback awareness. |

## Execution Loop

For each subphase:

1. Re-read the plan.
2. Confirm the subphase goal and edit surface.
3. Implement only that unit.
4. Run the declared tests.
5. Record evidence.
6. Check scope drift.
7. Stage only that unit.
8. Check atomicity.
9. Commit when commits are in scope.
10. Continue to the next executable subphase.

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
