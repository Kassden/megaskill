# Mega Skill Execution Contract

## Pre-Edit Declaration

Before mutating files, state:

```text
Mega Skill Guardrail
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
- conflicting user instructions
- material product choice that cannot be inferred
- verification failure that requires user/environment action

Everything else should be inspected, fixed, verified, and continued.
