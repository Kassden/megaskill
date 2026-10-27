---
schema_version: 1
decision_id: "resumable-completion-escape-hatch"
event_id: "devt-fe5eacd2af2949a4b4955d5dd193ca8e"
task_id: "megaskill-resumable-loop-20261026"
plan: "/Users/milkingthesun/Projects/.mega/MEGASKILL_CONVERSATION_REPAIR_PLAN.md"
plan_sha256: "967ab59ea3b23536007d9ce268a956f239a0866f773ac646d6bede537f3c355e"
phase: "4"
subphase: "4.1"
kind: "architecture"
status: "accepted"
timestamp: "2026-10-26T15:52:43.895485+00:00"
durable: true
supersedes: null
evidence_refs: []
state_event_ids: []
---

# resumable-completion-escape-hatch: How can completion retries remain useful while the user can escape a stale review loop?

## Context and question

How can completion retries remain useful while the user can escape a stale review loop?

## Decision

Keep outcome-based retries and make direct continue execute or resume clear only Megaskill scheduling state for the same goal

## Rationale

Native lockouts showed that inferred review permissions blocked legitimate work and their own repair; user explicitly wants the completion loop retained with an escape hatch

## Alternatives considered

- Remove all completion retries: rejected by the user because completing the whole goal remains valuable
- Persist a developer-level review prohibition and require metadata repair: rejected because the hook then blocks its own correction

## Assumptions

- Native host permissions and actual controlling instructions remain independent of scheduling hints

## Self-critique

Free-form language is ambiguous; parse direct requests conservatively and never deny tools based on the parser

## Disconfirming evidence

Independent review reproduced child contamination, pasted-refusal lockouts and false progress; focused regressions now cover these cases

## Cheapest disconfirming test

Replay review then continue then synthetic retry; reject genuine review limits, preserve original acceptance and stop budget resets from invalid or regressing evidence

## Consequences and tradeoffs

Unchanged attempts request diagnosis then yield as unfinished; explicit resume resets the soft budget without changing proof obligations

## Reversibility

Dedicated feature branch and configuration backups; native user off switches and trust hashes are preserved

## Follow-up triggers

Qualify actual host delivery when native hooks are enabled; report source protocol tests separately from native execution
