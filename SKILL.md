---
name: megaskill
description: Use for high-rigor execution planning and end-to-end implementation where Codex must create decision-complete plans for lower-level agents, prevent regressions, split work into atomic units, avoid lazy handoff, continue through obvious next steps, and prove done with tests, commits, push/deploy, or real-result verification when available. Trigger for requests like "super execution", "write a detailed agent plan", "implement the plan", "done means done", "no regressions", "atomic commits", "ship it", or any multi-step coding task that must be driven until done or genuinely blocked.
---

# Megaskill

Use Megaskill to turn a goal into guarded, atomic, verified execution.

Core rule: lock the goal, write or validate a canonical plan, execute the smallest independently valid subphase, prove it, record evidence, and continue until the full goal is done or genuinely blocked.

## Required Workflow

1. **Lock the goal**
   - State the requested outcome in one sentence.
   - State explicit acceptance criteria.
   - State what is out of scope.

2. **Create or validate the plan**
   - Use `scripts/mega_plan_init.py` to generate a plan skeleton when no canonical plan exists.
   - Use `scripts/mega_plan_check.py <plan.md>` before executing from a plan.
   - The plan must have dependency/tooling preflight, phases, subphases, commit lines, tests, success criteria, and checklist items.
   - For lower-level agents, make every subphase decision-complete: exact objective, files or systems to inspect, allowed edit surface, verification command, and handoff criteria.

3. **Declare regression guardrails before edits**
   - Requested outcome.
   - Planned edit surface.
   - Protected behaviors.
   - Likely consumers.
   - Damage radius: small, moderate, large, or systemic.
   - Proof plan.
   - Atomic change units.
   - Commit plan.

4. **Execute one subphase at a time**
   - Re-read the plan before each subphase.
   - Edit only the current subphase.
   - If changed files exceed the planned touch surface, stop and call out scope expansion.
   - Use `scripts/mega_scope_check.py <plan.md>` before committing or final handoff when the plan lists touch files.
   - Do not perform unrelated cleanup.

5. **Verify and commit atomically**
   - Missing verification tooling is setup work, not a skip reason.
   - If the work requires a verification surface, install or repair project-local tooling when absent.
   - For UI/browser-facing work, install or repair Playwright and browser binaries when needed, then run browser smoke, screenshot, visual, or canvas checks that match the change.
   - Only skip relevant verification for a real blocker: denied approval, missing credentials, incompatible platform, external outage, destructive action boundary, or an unresolved product decision.
   - Run the subphase tests/checks.
   - Record important checks with `scripts/mega_evidence.py`.
   - Stage only the coherent unit.
   - Run `scripts/mega_commit_check.py` before committing.
   - Commit each independently valid subphase when commits are in scope.

6. **Continue, do not hand off**
   - Continue into the next obvious machine-executable step.
   - Push/deploy/smoke test when available and implied.
   - Stop only for a real blocker: missing credentials, approval boundary, destructive action, unavailable external service, incompatible platform, conflicting instructions, or a product decision that cannot be inferred.
   - Do not call work done with "tool not installed" unless installation was attempted and failed for a real blocker.

7. **Finish with evidence**
   - Do not call work done without evidence against the goal.
   - Use `scripts/mega_evidence.py summary` to help build the final proof block.
   - Final verdict must be `done`, `blocked`, or `not done`.

## Script Quick Reference

- `scripts/mega_plan_init.py "Title" --goal "Goal" --phases "Discovery,Implementation,Verification" --output PLAN.md`
- `scripts/mega_plan_check.py PLAN.md`
- `scripts/mega_scope_check.py PLAN.md --planned src/foo.ts --planned tests/foo.test.ts`
- `scripts/mega_commit_check.py`
- `scripts/mega_evidence.py record --phase "1.1" --command "npm test" --exit-code 0 --note "targeted tests"`
- `scripts/mega_evidence.py run --phase "1.1" -- npm test`
- `scripts/mega_evidence.py summary`

## References

- Read `references/execution-contract.md` for the full execution loop and blocker rules.
- Read `references/agent-plan-template.md` when writing a plan for lower-level agents.
- Read `references/final-handoff-template.md` before the final response.
