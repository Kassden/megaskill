# Final Handoff Template

Use this at completion.

```text
Megaskill Handoff
- Goal:
- Acceptance criteria:
- Requested change delivered:
- Incidental but necessary changes:
- Intentionally untouched:
- Verified surfaces:
- Verification evidence:
- SOTA / standards / best-practices applied:
- Deterministic real-user test:
- Fulfillment/readback proof:
- Armageddon report:
- Generality/anti-overfitting decision:
- Tooling installed or repaired:
- Retry/fallback attempts:
- Checks not run and blocker class:
- Deployment/push evidence:
- Real-result check:
- Next executable step already taken?:
- Unverified or partially verified:
- Scope expansion:
- Measured damage radius:
- Atomic commit split:
- Remaining gaps:
- Whole-plan final gate:
- Verdict: done | blocked | not done
```

Verdict rules:

- `done`: evidence proves the requested goal on the strongest available surface.
- `blocked`: a real blocker prevents completion, and the blocker is named exactly.
- `not done`: implementation or verification is incomplete without a hard external blocker.

Whole-plan rule:

- If the user asked to execute the whole plan, finish all phases, or not drop the plan, `not done` is not a valid final answer unless the user explicitly asked for a progress report.
- Run `scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --verdict done` before a done handoff.
- Run `scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --verdict blocked` before a blocked handoff.
- If the gate finds incomplete subphases and no blocker, continue instead of handing off.
