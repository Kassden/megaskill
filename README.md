# Megaskill

<p align="center">
  <a href="https://github.com/Kassden/megaskill/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/Kassden/megaskill?style=for-the-badge&logo=github"></a>
  <a href="https://github.com/Kassden/megaskill/forks"><img alt="GitHub forks" src="https://img.shields.io/github/forks/Kassden/megaskill?style=for-the-badge&logo=github"></a>
  <a href="https://github.com/Kassden/megaskill/watchers"><img alt="GitHub watchers" src="https://img.shields.io/github/watchers/Kassden/megaskill?style=for-the-badge&logo=github"></a>
  <img alt="Repo size" src="https://img.shields.io/github/repo-size/Kassden/megaskill?style=for-the-badge">
  <a href="https://tokei.kojix2.net/github/Kassden/megaskill"><img alt="Lines of code" src="https://img.shields.io/endpoint?style=for-the-badge&url=https%3A%2F%2Ftokei.kojix2.net%2Fbadge%2Fgithub%2FKassden%2Fmegaskill%2Flines"></a>
  <img alt="Files" src="https://img.shields.io/badge/Files-20-blue?style=for-the-badge">
  <img alt="Languages" src="https://img.shields.io/github/languages/count/Kassden/megaskill?style=for-the-badge">
  <img alt="Top language" src="https://img.shields.io/github/languages/top/Kassden/megaskill?style=for-the-badge">
  <a href="https://github.com/Kassden/megaskill/commits/main"><img alt="Commits" src="https://img.shields.io/github/commit-activity/t/Kassden/megaskill?style=for-the-badge"></a>
  <a href="https://github.com/Kassden/megaskill/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Kassden/megaskill?style=for-the-badge"></a>
  <a href="https://github.com/Kassden/megaskill/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/Kassden/megaskill?style=for-the-badge"></a>
</p>

<p align="center">
  <a href="https://github.com/Kassden/megaskill#install"><img alt="Install for Codex" src="https://img.shields.io/badge/Codex-install-0A84FF?style=for-the-badge"></a>
  <a href="https://github.com/Kassden/megaskill#quick-start"><img alt="Quick start" src="https://img.shields.io/badge/Quick%20Start-commands-2EA44F?style=for-the-badge"></a>
  <a href="https://github.com/Kassden/megaskill#execution-loop"><img alt="Execution loop" src="https://img.shields.io/badge/Loop-plan%20%7C%20execute%20%7C%20prove-7B61FF?style=for-the-badge"></a>
</p>

Megaskill is a high-rigor execution skill for AI coding agents. It turns a broad coding goal into a guarded, step-by-step execution loop with explicit acceptance criteria, regression guardrails, atomic commits, verification evidence, and a final done/blocked/not-done verdict.

Use it when an agent needs to write a decision-complete plan for lower-level agents, prevent scope drift, execute iteratively, and prove the result with real checks instead of handing work back early.

## What It Provides

- Goal locking with acceptance criteria and out-of-scope boundaries.
- Plan validation for dependency/tooling preflight, phases, subphases, tests, success criteria, planned touch files, and checklist items.
- Regression guardrail prompts before file edits.
- Scope drift checks against changed, staged, and untracked files.
- Atomic commit checks for staged changes.
- Evidence recording for verification commands.
- Final handoff structure with a clear `done`, `blocked`, or `not done` verdict.

## Autonomy Rule

Missing verification tooling is setup work, not a reason to skip relevant checks. If the requested work needs a verification surface, Megaskill expects the agent to install or repair project-local tooling and continue.

For UI, visual, browser, canvas, 3D, or game work, use the repo's existing browser-test stack or add project-local Playwright tooling when absent, install required browser binaries, and run the browser smoke, screenshot, visual, or pixel checks that match the change. Only skip relevant verification for a real blocker: denied approval, missing credentials, incompatible platform, external outage, destructive-action boundary, or product decision that cannot be inferred.

## Execution Loop

```mermaid
flowchart LR
    A(["Lock goal"]) --> B(["Acceptance criteria"])
    B --> C(["Plan subphases"])
    C --> D(["Declare guardrails"])
    D --> E(["Execute one unit"])
    E --> F(["Verify"])
    F --> G(["Record evidence"])
    G --> H(["Scope check"])
    H --> I(["Atomic commit check"])
    I --> J{"Complete?"}
    J -- "next unit" --> E
    J -- "yes" --> K(["Final handoff: done"])
    F -- "fails" --> L{"Real blocker?"}
    L -- "fixable" --> E
    L -- "blocked" --> M(["Final handoff: blocked"])

    classDef action fill:#F8FAFC,stroke:#334155,stroke-width:1.5px,color:#0F172A;
    classDef decision fill:#FEF3C7,stroke:#B45309,stroke-width:1.5px,color:#78350F;
    classDef terminal fill:#ECFDF5,stroke:#047857,stroke-width:1.5px,color:#064E3B;
    class A,B,C,D,E,F,G,H,I action;
    class J,L decision;
    class K,M terminal;
```

## Install

### Codex

Recommended Codex install:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Kassden/megaskill \
  --path . \
  --name megaskill
```

For an editable install, clone this repo directly into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Kassden/megaskill.git ~/.codex/skills/megaskill
```

Restart Codex or start a new session, then ask for `$megaskill`.

### Claude Code

Install as a personal Claude Code skill:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Kassden/megaskill.git ~/.claude/skills/megaskill
```

Or install it for one project:

```bash
mkdir -p .claude/skills
git clone https://github.com/Kassden/megaskill.git .claude/skills/megaskill
```

Restart Claude Code or start a new session, then ask Claude to use Megaskill for guarded execution planning and verification.

## Quick Start

Run commands from the Megaskill folder:

```bash
cd ~/.codex/skills/megaskill
```

Create a plan skeleton:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_plan_init.py \
  "Execution Plan" \
  --goal "Ship the requested change with tests and evidence" \
  --phases "Discovery,Implementation,Verification" \
  --output PLAN.md
```

Validate a plan before execution:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_plan_check.py PLAN.md
```

Check scope drift against the plan:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_scope_check.py PLAN.md
```

Check only staged files before committing:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_scope_check.py PLAN.md --staged
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_commit_check.py
```

Record evidence for checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_evidence.py run \
  --phase "1.1" \
  -- npm test
```

Summarize recorded evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/mega_evidence.py summary
```

## Example Goal And Research Plan

Use this shape when assigning work to a lower-level coding agent. The important part is that each subphase is decision-complete: it names what to inspect, what may be edited, what proves success, and what must be checked off before moving on.

```markdown
# Add Cached Customer Search

## GOAL
- Add server-side caching to customer search so repeated identical queries return faster without changing search results, permissions, or API response shape.

## Acceptance Criteria
- [ ] Identical customer search requests reuse cached results within a 60 second TTL.
- [ ] Users only receive results they are authorized to see.
- [ ] Existing search response JSON remains backward compatible.
- [ ] Cache behavior is covered by targeted tests.
- [ ] Verification evidence is recorded before final handoff.

## Research
- Built-in options:
  - Inspect the existing search API route, service layer, auth checks, and cache utilities already in the repo.
  - Prefer existing framework cache primitives if the app already uses them.
- Off-the-shelf options:
  - Consider Redis or the platform cache only if the repo already has that dependency or production config.
  - Do not introduce a new cache service for this subphase unless existing infrastructure proves it is available.
- Official / standards sources:
  - Check framework docs for cache invalidation and runtime constraints if a built-in cache is used.
  - Check existing project docs for data privacy, tenancy, or authorization rules.

## Dependency and Tooling Preflight
- Required verification tools:
  - Existing project test runner.
  - TypeScript typecheck.
  - Local API smoke tool such as `curl` if the app exposes a dev server.
- Existing tooling found:
  - To be filled after reading `package.json` and existing test files.
- Install or repair commands:
  - Use the repo package manager to install missing declared dependencies.
  - Add narrowly scoped project-local test dependencies only when the required proof surface is absent.
- Browser/runtime binaries:
  - Not required unless the cache behavior is exposed through browser-only UI behavior.
- Real blockers that would prevent setup:
  - Missing credentials, denied dependency-install approval, incompatible platform, or external package registry outage.

## Regression Guardrails
- Planned edit surface:
  - `src/api/customers/search.ts`
  - `src/services/customer-search.ts`
  - `tests/customer-search-cache.test.ts`
- Protected behaviors:
  - Authorization filtering, response schema, pagination, sorting, and empty-state behavior.
- Likely consumers:
  - Customer search UI, saved-search workflows, API clients, and support tooling.
- Damage radius:
  - Moderate: API behavior and shared service path.
- Proof plan:
  - Run targeted cache tests, existing customer search tests, typecheck, and one manual API smoke if the app has a local dev server.

## Phase 1: Discovery

### Subphase 1.1: Map Search Flow
- Commit: docs/plan only if a durable plan file is being committed; otherwise no commit.
- Tests: no code tests; evidence is file/path inventory and confirmed call flow.
- Success Criteria: exact API route, service function, auth boundary, and test locations are known.
- Planned Touch Files:
  - `MEGA_PLAN.md`
- Checklist:
  - [ ] Read the search route and identify request parameters.
  - [ ] Trace the service function that produces search results.
  - [ ] Identify where authorization or tenant filtering happens.
  - [ ] Identify existing tests that must keep passing.
  - [ ] Record findings in the plan before editing code.

## Phase 2: Implementation

### Subphase 2.1: Add Cache Key And TTL
- Commit: add customer search cache key and TTL handling.
- Tests: `npm test -- customer-search-cache`
- Success Criteria: identical authorized queries can hit the cache while distinct users, tenants, query params, sort order, and pages produce separate cache keys.
- Planned Touch Files:
  - `src/services/customer-search.ts`
  - `tests/customer-search-cache.test.ts`
- Checklist:
  - [ ] Build the cache key from user/tenant identity and normalized search params.
  - [ ] Set TTL to 60 seconds.
  - [ ] Avoid caching authorization failures.
  - [ ] Add tests for cache hit, cache miss, and cross-user isolation.
  - [ ] Run targeted tests and record evidence.
  - [ ] Run `scripts/mega_scope_check.py MEGA_PLAN.md --staged` before commit.

### Subphase 2.2: Preserve API Contract
- Commit: preserve customer search API response shape with cached results.
- Tests: `npm test -- customer-search` and `npm run typecheck`
- Success Criteria: cached and uncached responses have the same JSON shape, status codes, pagination fields, and sorting behavior.
- Planned Touch Files:
  - `src/api/customers/search.ts`
  - `tests/customer-search-cache.test.ts`
- Checklist:
  - [ ] Confirm the route still delegates authorization to the same boundary.
  - [ ] Add or update a response-shape assertion.
  - [ ] Run targeted search tests.
  - [ ] Run typecheck.
  - [ ] Record evidence for each verification command.
  - [ ] Run `scripts/mega_commit_check.py` before commit.

## Phase 3: Verification

### Subphase 3.1: Final Evidence And Handoff
- Commit: none unless verification docs are committed.
- Tests: targeted tests, typecheck, and optional local API smoke.
- Success Criteria: final handoff can state `done` with evidence, or name a precise blocker.
- Planned Touch Files:
  - `.mega/evidence.jsonl`
- Checklist:
  - [ ] Run `scripts/mega_evidence.py summary`.
  - [ ] Confirm no unplanned files remain changed.
  - [ ] Confirm commits are pushed if publishing is in scope.
  - [ ] Write final handoff with verified surfaces, unverified surfaces, and verdict.
```

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/mega_plan_init.py` | Creates a canonical execution plan skeleton. |
| `scripts/mega_plan_check.py` | Validates plan structure before execution. |
| `scripts/mega_scope_check.py` | Compares planned touch files with working-tree, staged, and untracked changes. |
| `scripts/mega_commit_check.py` | Checks whether staged files look like one atomic commit. |
| `scripts/mega_evidence.py` | Records and summarizes verification evidence. |

## Skill Files

- `SKILL.md`: skill entrypoint and routing instructions.
- `references/execution-contract.md`: full execution loop and blocker rules.
- `references/agent-plan-template.md`: template for lower-level agent plans.
- `references/final-handoff-template.md`: final response proof block.
- `agents/openai.yaml`: OpenAI agent interface metadata.

## License

MIT
