# Decision records and ADR promotion

`scripts/mega_decision.py` uses only the Python standard library on POSIX systems.
Use a decision record when a reviewer would reasonably ask why: architecture,
UI/product interaction, schema, scope, dependencies, verification, root-cause
hypotheses, branch strategy, reversibility, risk, and durable policy. Mechanical
changes already dictated by the plan do not need additional records.

The ledger defaults to `.mega/decisions.jsonl` relative to the calling workspace.
All five commands accept `--file`. Run `COMMAND --help` for their arguments.
New records are always proposed. A decision ID is stable; each appended event has
a unique event ID and timezone-aware timestamp. JSON output from writes provides
the exact IDs for readback and downstream linkage.

## Required rationale and linkage

Each record requires a question, chosen decision, rationale (`--why` or
`--rationale`), at least one rejected alternative with its reason, assumptions,
self-critique, disconfirming evidence, the cheapest disconfirming test, tradeoffs,
reversibility, and follow-up triggers. Record these before accepting the choice.
For disconfirming evidence, state observations that contradict the choice; if
none have been observed, explicitly say so and describe what would refute it.
The validator enforces structure and nonempty values, not the truth or quality of
the author's reasoning. No private chain of thought or secrets should be stored.

`--task-id`, `--plan`, `--phase`, and `--subphase` are required for creation.
The plan must exist and contain the exact numbered phase and subphase headings.
The ledger stores the canonical absolute plan path and SHA-256 of its bytes at
creation. Phase/subphase matching is exact (`1.1` is distinct from `1.10`).
Task IDs are explicit caller-supplied identities, not inferred from cwd or chat.
The CLI does not register tasks. Status and promotion
require the same task ID and plan path. Lifecycle events retain the original
plan digest even if the plan evolves; offline historical validation does not
require the plan to remain on disk. A new record under changed plan bytes has a
new digest and cannot supersede a decision from the old snapshot.

When `.mega/tasks/TASK_ID.json` exists beside the ledger, writes also verify the
runtime contract's task ID, plan path/hash, exact obligation, active status, and
execute mode. Use `--task-file` to require an explicit contract on writes or
validation. Without a contract, IDs are caller assertions, not proof of authority.
Historical validation checks a contract only when explicitly supplied, so later
task reconciliation does not invalidate the append-only historical ledger.

Optional repeatable `--state-event-id` and `--evidence-ref` link supporting proof.
Supply `--state-file` and/or `--evidence-file` to `record` or `validate` for strict
reference resolution. References must uniquely resolve; explicit task, plan,
phase, and subphase conflicts fail. Legacy proof records may omit identity;
their IDs can resolve but do not establish task authority. Without those files,
the validator checks reference shapes, not existence. Evidence IDs use
`evidence_id`, `id`, or runtime `event_id`; state IDs use `event_id`. Runtime proof
`plan_hash` and `obligation_id` must match the exact plan snapshot and subphase.

## CLI example

Run in a workspace with `PLAN.md` containing Phase 1 and Subphase 1.1:

```sh
python3 /path/to/megaskill/scripts/mega_decision.py record \
  --task-id task-navigation --plan PLAN.md --phase 1 --subphase 1.1 \
  --decision-id dec-navigation --kind ui --durable \
  --question 'Tabs or sidebar?' --decision 'Tabs' \
  --why 'Three peer views fit the existing navigation' \
  --alternative 'Sidebar: consumes scarce horizontal space' \
  --assumption 'There will remain only three views' \
  --self-critique 'Tabs may reduce discovery of other views' \
  --disconfirming-evidence 'Observed hidden-view task failures would refute this' \
  --disconfirming-test 'Try three navigation tasks at 390px' \
  --tradeoffs 'Less space, weaker discoverability' \
  --reversibility 'Swap the navigation component; routes stay stable' \
  --follow-up 'Revisit when view count exceeds five'

python3 /path/to/megaskill/scripts/mega_decision.py status \
  --task-id task-navigation --plan PLAN.md --decision-id dec-navigation \
  --status challenged --reason 'Reviewed assumptions and alternatives'
python3 /path/to/megaskill/scripts/mega_decision.py status \
  --task-id task-navigation --plan PLAN.md --decision-id dec-navigation \
  --status accepted --reason 'Navigation trial supports the choice'
python3 /path/to/megaskill/scripts/mega_decision.py promote \
  --task-id task-navigation --plan PLAN.md --decision-id dec-navigation
python3 /path/to/megaskill/scripts/mega_decision.py validate
python3 /path/to/megaskill/scripts/mega_decision.py summary --task-id task-navigation --json
```

## Lifecycle and supersession

The ordered lifecycle is `proposed -> challenged -> accepted -> committed ->
executed -> validated`. `challenged -> committed` is supported for the original
proposal's naming. Accepted choices may go directly to executed; committed
choices must go through executed before validated. Proposed, challenged, or
accepted choices can be rejected; rejected and superseded choices are terminal.
Every status change requires a nonempty reason. Rationale and linkage cannot be
rewritten through lifecycle events.

To replace an accepted choice, create a new proposed record with
`--supersedes OLD_ID`, then challenge and accept or commit it. The old decision
must already be accepted, committed, executed, or validated, with the same task,
plan snapshot, phase, and subphase. Acceptance appends the new status and the
old decision's `superseded` status with `superseded_by` in one transaction.
Competing replacements cannot both supersede the same choice. Supersession
without an accepted replacement, unknown/forward IDs, duplicate IDs, invalid
transitions, backwards timestamps, and incomplete transactions fail validation.

`summary` presents current snapshots, retaining original rationale and linkage;
filter with exact `--task-id`, `--plan`, `--kind`, or `--status`. `--json` provides
machine-readable snapshots. Full immutable history remains in the JSONL ledger.

## Durable ADRs and storage guarantees

Promotion is allowed only for `--durable` records currently accepted, committed,
executed, or validated. It writes `docs/adr/DECISION_ID.md`, or an explicit
`--output` Markdown path. The Markdown carries YAML-compatible frontmatter with
schema version, decision/event IDs, task, exact plan path/digest, phase/subphase,
kind, acceptance status, timestamp, durability, supersedes, and proof references.
Its body includes all rationale and critique fields. This follows the rationale,
options, consequences, and metadata conventions in the primary
[MADR documentation](https://adr.github.io/madr/).

ADRs are immutable promotion snapshots. Later execution, validation, rejection,
or supersession appears in the ledger, not a rewritten ADR. Read `summary` for
current status. A replacement gets its own ADR with a `supersedes` link. Repeat
promotion checks the saved ADR hash and returns the existing receipt without
another event. Missing/modified ADRs or a different output path fail; existing
unrelated output files are never overwritten. An identical unreceipted file can
be adopted after a crash between ADR creation and ledger receipt.

A stable sidecar `.lock` reuses `mega_store.locked` and `fcntl.flock` to serialize each read/check/append
transaction. Ledger writes preserve all existing bytes as a prefix and use a
same-directory temporary file, file fsync, atomic replacement, and directory
fsync. Thus logical appends, including supersession pairs, are atomic rather than
leaving half a transaction. ADR writes use the same atomic mechanism and an
output lock. These guarantees require cooperating local writers and a filesystem
that supports advisory locks and atomic rename; editing the JSONL manually bypasses
them. There is no distributed transaction between ADR and ledger: write ADR
first and retry to adopt its identical bytes if the receipt was interrupted.

Validation fails closed on malformed JSON, duplicate keys, missing/wrong fields,
unterminated lines, or invalid lifecycle history. Empty ledgers are valid; missing
ledgers fail reads and are created only by `record`. Invalid writes leave history
unchanged. Success exits 0, validation/I/O failures exit 1 with a diagnostic,
and argparse usage failures exit 2. This CLI supplies decision records and ADRs;
it does not install a mutation gate, hook, dashboard, or enforcement policy.
