---
schema_version: 1
decision_id: "ADR-001"
event_id: "devt-5ca25d69032247d8845011850727b587"
task_id: "runtime-repair"
plan: "/Users/milkingthesun/.codex/skills/megaskill/MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md"
plan_sha256: "98ea72eea516b0e1a04963895af578d273667cb9276e2910723c0c53233846fb"
phase: "1"
subphase: "1.1"
kind: "architecture"
status: "accepted"
timestamp: "2026-10-14T03:20:23.536243+00:00"
durable: true
supersedes: null
evidence_refs: []
state_event_ids: []
---

# ADR-001: Where should completion be enforced?

## Context and question

Where should completion be enforced?

## Decision

Use a shared exact-task proof evaluator behind synchronous Codex lifecycle hooks.

## Rationale

Skill prose cannot force the agent to run a gate; lifecycle checks run independently of that choice.

## Alternatives considered

- Stronger instruction prose alone

## Assumptions

- The supported Codex runtime loads trusted synchronous hooks.

## Self-critique

Hooks can be disabled or fail; agent-written receipts do not establish a security boundary.

## Disconfirming evidence

A trusted Stop hook fails to produce continuation in the installed runtime.

## Cheapest disconfirming test

Run a premature-stop canary and inspect actual hook invocation receipts.

## Consequences and tradeoffs

Small local state and hooks introduce installation and migration work.

## Reversibility

Remove owned hook entries and use the previous CLI workflow without deleting historical records.

## Follow-up triggers

Refresh runtime coverage after Codex upgrades.
