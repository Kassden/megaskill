---
schema_version: 1
decision_id: "outcome-contracts-v2"
event_id: "devt-47e27f05fc0a4bbc87d3a3f27a1d5f0a"
task_id: "runtime-repair"
plan: "/Users/milkingthesun/.codex/skills/megaskill/MEGASKILL_RUNTIME_IMPLEMENTATION_PLAN.md"
plan_sha256: "26065a5030ccf058a507561be6a6ce5362ee8d5673d7f6a0b7f00c1fa215d974"
phase: "4"
subphase: "4.1"
kind: "verification"
status: "accepted"
timestamp: "2026-10-15T03:34:55.079166+00:00"
durable: true
supersedes: null
evidence_refs: []
state_event_ids: []
---

# outcome-contracts-v2: What evidence permits whole-goal completion?

## Context and question

What evidence permits whole-goal completion?

## Decision

Pin declarative outcome assertions to each obligation; require them in runtime, CLI evaluation and manual final gates; observe actual session lifecycle separately

## Rationale

Successful self-selected commands certified a rejected website; PCB ended after a failed gate without a Stop audit

## Alternatives considered

- More prompting alone: cannot detect a missing hook or distinguish a file from the requested outcome

## Assumptions

- Local report artifacts can express measurable outcomes; qualitative judgments require an explicitly independent reviewer

## Self-critique

Agent-writable reports are not tamper-proof and an absent native hook cannot be repaired by the hook itself

## Disconfirming evidence

A nonzero metric, rejected review or missing hook receipt still receives a certified complete verdict

## Cheapest disconfirming test

Replay the real failure classes with successful proxy proofs and assert strict runtime and final gate refusal

## Consequences and tradeoffs

Existing tasks must explicitly migrate acceptance policies; no hidden weakening for backward compatibility at certification boundaries

## Reversibility

Legacy artifact evaluation remains available internally; strict gates and policy migration are separately testable

## Follow-up triggers

Require same-session invocation evidence before claiming host enforcement and preserve unresolved host limitations
