---
schema_version: 1
decision_id: "ADR-002"
event_id: "devt-2dd17a19d8a747f88c5900418fdf5032"
task_id: "runtime-repair"
plan: "/Users/milkingthesun/.codex/skills/megaskill/MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md"
plan_sha256: "98ea72eea516b0e1a04963895af578d273667cb9276e2910723c0c53233846fb"
phase: "2"
subphase: "2.2"
kind: "policy"
status: "accepted"
timestamp: "2026-10-14T03:36:01.049415+00:00"
durable: true
supersedes: null
evidence_refs: []
state_event_ids: []
---

# ADR-002: How should roles be dispatched and children retired?

## Context and question

How should roles be dispatched and children retired?

## Decision

Use on-demand responsibilities, a native cap of three open children, exact parent ownership and real native close receipts.

## Rationale

Unbounded or completed-but-open children consume slots and leave parent integration unclear.

## Alternatives considered

- Always instantiate six role agents or recursively fan out

## Assumptions

- The native close operation identifies its target and returns a lifecycle result.

## Self-critique

Roles alone do not provide permissions; some runtime tool paths can bypass hooks.

## Disconfirming evidence

Quota races or parent-crossing cleanup occur in isolated lifecycle tests.

## Cheapest disconfirming test

Attack concurrent spawn limits, cross-parent ownership and completed-versus-closed transitions.

## Consequences and tradeoffs

Bounded parallelism favors useful independent work over maximum agent count.

## Reversibility

Remove the installed cap/profiles and owned hooks while keeping historical assignment receipts.

## Follow-up triggers

Recheck tool coverage and native lifecycle after runtime upgrades.
