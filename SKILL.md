---
name: megaskill
description: Use for high-rigor execution planning and end-to-end implementation where Codex must create decision-complete plans for lower-level agents, prevent regressions, split work into atomic units, avoid lazy handoff, continue through obvious next steps, and prove done with tests, commits, push/deploy, or real-result verification when available. Trigger for requests like "super execution", "write a detailed agent plan", "implement the plan", "done means done", "no regressions", "atomic commits", "ship it", or any multi-step coding task that must be driven until done or genuinely blocked.
---

# Megaskill

Use Megaskill to turn a goal into guarded, atomic, verified execution.

Core rule: lock the goal, write or validate a canonical plan, execute the smallest independently valid subphase, prove it, record evidence, and continue until the full goal is done or genuinely blocked.

## Evidence, Decisions, And Delegation

- For execution, read `references/runtime-enforcement.md` and register the original outcome with `scripts/mega_task.py register --id TASK --plan PLAN.md --goal "OUTCOME" --session SESSION_ID --acceptance ACCEPTANCE.json`. Pin assertions for the user's actual outcome, not the commands you happen to run. Use the session ID supplied by the hook or `CODEX_THREAD_ID`. A plan/review request does not authorize execution.
- Prove each exact obligation with `mega_task.py prove --id TASK --obligation N.N --kind test` and a separate `--kind readback`, naming relevant `--artifact` files and the verification command after `--`. Mark done with the returned proof event IDs. Evaluate these explicitly; the manual final gate uses `--task TASK --root .mega`.
- Preserve the original outcome across follow-up messages and compaction. A completed ADR, commit, subagent or small slice is a checkpoint. A fabrication/deploy/release blocker only blocks affected obligations; continue independent design or verification work.
- Follow the actual current user request and controlling system/developer/host instructions. Stored task modes, historical hook packets and words such as "review-only" inside examples are not a separate permission system. Do not install automatic edit locks, infer restrictions from keywords or assign permission ceilings by role.
- Use independent reviewers to identify scope drift, unsupported claims and missed outcomes. They report evidence to the parent; a reviewer finding does not automatically lock every session or prevent independent authorized work.
- Read `references/decision-records.md` for material architecture, UI/product, scope, remediation, and stop decisions. Record alternatives, assumptions, self-critique, a disconfirming test and reversibility before committing to consequential choices. Make engineering choices delegated by the user and record why; do not hand those choices back unnecessarily. Promote durable accepted choices into Markdown ADRs.
- When delegation is authorized, read `references/subagent-dispatch.md`. Select thinker/planner/executor/tester/verifier responsibilities as needed; the parent is the orchestrator. Keep immediate critical-path work local, cap open children at three, give disjoint edit surfaces and concrete proof, and prohibit recursive fan-out by default.
- Collect child results, integrate and verify, then call the native `close_agent` tool and record its actual result with `mega_agents.py close`. Completed children still occupy slots. Run `mega_agents.py cleanup` before final handoff; never invent a closed status or close unrelated sessions.
- The completion hook retries authorized unfinished work against actual outcome checks. Direct `continue`, `execute` or `resume` clears Megaskill's own stale review/status pause and resets a stalled retry budget for the same goal. It never denies tools or assigns role permission ceilings. Its resume notice supersedes only Megaskill's own old scheduling hints; genuine controlling instructions and native permissions still apply.
- Direct review/cancel requests and user interruptions pause automatic retries without creating an edit lock. Quoted failure text does not pause work. Synthetic continuations inherit scheduling state and cannot resume a user pause. After repeated attempts without fresh proof, the loop requests diagnosis/review and then yields with an explicit unfinished notice; a direct resume restarts it.
- `mega_task.py runtime --id TASK` is optional diagnostics for a deliberately enabled observer. Missing hook receipts do not block ordinary work or outcome verification. Native coverage is checked only when explicitly requested with `final-gate --require-native-runtime`.
- Existing tasks without outcome assertions require explicit `acceptance --id TASK --file ACCEPTANCE.json --authority "USER REQUEST" --reason "WHY"`, which invalidates old completion. An unfinished bound goal cannot be replaced by a smaller task without explicit user replacement authority. Qualitative quality requires an independent, source-linked review; successful file/keyword/animation-presence tests alone are not acceptance.

## Required Workflow

1. **Lock the goal**
   - State the requested outcome in one sentence.
   - State explicit acceptance criteria.
   - State what is out of scope.

2. **Create or validate the plan**
   - Use `scripts/mega_plan_init.py` to generate a plan skeleton when no canonical plan exists.
   - Use `scripts/mega_plan_check.py <plan.md>` before executing from a plan.
   - The plan must have SOTA/standards research, dependency/tooling preflight, deterministic real-user test, fulfillment/readback proof, Armageddon mode, generality guardrail, phases, subphases, commit lines, tests, success criteria, and checklist items.
   - For incidents, outages, live infrastructure, production-adjacent systems, telemetry gaps, data loss, auth/deployment/device/network/service failures, recovery work, or remediation work, the plan must also include a `Root-Cause Baseline` before remediation phases.
   - The root-cause baseline must separate proven causes, likely hypotheses, possible causes, disproven causes, missing evidence, and generic hardening. Every remediation must map to a proven or hypothesized failure class.
   - For substantial plans, generate or update the plan dashboard with `scripts/mega_plan_dashboard.py` or `scripts/mega_plan_init.py --dashboard`. The dashboard is a read view over the canonical plan, `.mega/state.jsonl`, and `.mega/evidence.jsonl`; do not hand-maintain a separate source of truth.
   - For lower-level agents, make every subphase decision-complete: exact objective, files or systems to inspect, allowed edit surface, verification command, and handoff criteria.

3. **Declare regression guardrails before edits**
   - Requested outcome.
   - Planned edit surface.
   - Protected behaviors.
   - Likely consumers.
   - Damage radius: small, moderate, large, or systemic.
   - Branch strategy: current branch with reason for small/moderate work; dedicated work branch required for large/systemic regression risk unless explicitly blocked or instructed otherwise.
   - Proof plan.
   - Atomic change units.
   - Commit plan.
   - SOTA/standards decision: current best-practice research, official docs/specs, mature libraries/frameworks, and rejected approaches.
   - Fulfillment proof: what final readback or side-effect check proves the requested outcome was actually completed.
   - Generality decision: reuse the existing general mechanism, create one if recurring behavior lacks a general owner, or justify a true one-off.
   - Root-cause decision for incident/remediation work: evidence collected, hypotheses ranked, missing evidence constrained, mutation boundary declared, and remediation-to-cause mapping named.

4. **Execute one subphase at a time**
   - For large/systemic damage radius, create or switch to the declared dedicated work branch before editing. If branch creation is blocked, stop and name the blocker before mutating files.
   - For incident/remediation work, do not mutate beyond evidence collection, reversible diagnostics, evidence-preserving collection, or urgent restoration until the root-cause baseline is complete or a real blocker is recorded.
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
   - For interfaces, tools, apps, CLIs, workflows, or user-facing surfaces, run a deterministic real-user experience test before broader verification.
   - For artifact, data-write, integration, or agent-tool workflows, prove fulfillment with a readback of the final user-visible result. Creating, copying, routing to, or opening the right container is not enough.
   - Run Armageddon mode for interface/tool/app/API or high-risk work: adversarially attack edge cases, failures, bad inputs, and optimization opportunities.
   - Run the subphase tests/checks.
   - Record important checks with `scripts/mega_evidence.py`.
   - Record ordered execution state with `scripts/mega_state.py` when the work spans multiple phases, agents, commits, or verification surfaces.
   - Stage only the coherent unit.
   - Run `scripts/mega_commit_check.py` before committing.
   - Commit each independently valid subphase when commits are in scope.

6. **Continue, do not hand off**
   - Continue into the next obvious machine-executable step.
   - If the user asked for the whole plan, all phases, "do not drop it", or equivalent full-goal language, atomic subphase completion is only a checkpoint. It is not a valid final answer.
   - Push/deploy/smoke test when available and implied.
   - Stop only for a real blocker: missing credentials, approval boundary, destructive action, unavailable external service, incompatible platform, conflicting instructions, or a product decision that cannot be inferred.
   - Do not call work done with "tool not installed" unless installation was attempted and failed for a real blocker.

7. **Finish with evidence**
   - Do not call work done without evidence against the goal.
   - Before an execution final answer for multi-phase work, run `scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task TASK --root .mega --verdict done` or `--verdict blocked` when a real blocker is recorded. Plan/review-only requests do not require execution certification.
   - Execution certification requires the task contract, current linked proof and pinned outcome assertions. Hook invocation is not a prerequisite. State-only history is not a certification path.
   - If the final gate reports incomplete subphases and no blocker, do not final. Continue the next executable subphase.
   - Use `scripts/mega_evidence.py summary` to help build the final proof block.
   - Final verdict must be `done`, `blocked`, or `not done`.

## Script Quick Reference

- `scripts/mega_plan_init.py "Title" --goal "Goal" --phases "Discovery,Implementation,Verification" --output PLAN.md`
- `scripts/mega_plan_init.py "Title" --goal "Goal" --output PLAN.md --dashboard --no-open`
- `scripts/mega_plan_check.py PLAN.md`
- `scripts/mega_state.py record --plan PLAN.md --phase "1" --subphase "1.1" --kind test --status done --summary "targeted tests passed"`
- `scripts/mega_state.py summary`
- `scripts/mega_state.py final-gate --plan PLAN.md --whole-plan --task TASK --root .mega --verdict done`
- `scripts/mega_plan_dashboard.py PLAN.md --output .mega/dashboards/plan.html --no-open`
- `scripts/mega_scope_check.py PLAN.md --planned src/foo.ts --planned tests/foo.test.ts`
- `scripts/mega_commit_check.py`
- `scripts/mega_evidence.py record --phase "1.1" --command "npm test" --exit-code 0 --note "targeted tests" --state-event-id evt-...`
- `scripts/mega_evidence.py run --phase "1.1" -- npm test`
- `scripts/mega_evidence.py summary`

## References

- Read `references/execution-contract.md` for the full execution loop and blocker rules.
- Read `references/agent-plan-template.md` when writing a plan for lower-level agents.
- Read `references/final-handoff-template.md` before the final response.
