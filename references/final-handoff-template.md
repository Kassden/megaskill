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
- Original outcome and unmet obligation IDs:
- Task contract and current proof:
- Material decision IDs / ADR links:
- Owned children closed (native receipts):
- Installed / trusted / runtime-tested hook coverage:
- Verdict: done | blocked | not done
```

Verdict rules:

- `done`: evidence proves the requested goal on the strongest available surface.
- `blocked`: a real blocker prevents completion, and the blocker is named exactly.
- `not done`: implementation or verification is incomplete without a hard external blocker.

Whole-plan rule:

- If the user asked to execute the whole plan, finish all phases, or not drop the plan, `not done` is not a valid final answer unless the user explicitly asked for a progress report.
- Run `scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task TASK --root .mega --verdict done` before an execution done handoff. A state-only history cannot certify completion.
- Run the same task-scoped gate with `--verdict blocked` for an external blocker; retain per-obligation evidence and continue independent work.
- If the gate finds incomplete subphases and no blocker, continue instead of handing off.
