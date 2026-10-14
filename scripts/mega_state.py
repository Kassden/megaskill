#!/usr/bin/env python3
"""Record and validate ordered Megaskill execution state."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_FILE = Path(".mega/state.jsonl")
REQUIRED_FIELDS = {
    "event_id",
    "timestamp",
    "cwd",
    "plan",
    "phase",
    "subphase",
    "kind",
    "status",
    "summary",
    "damage_radius",
    "branch",
    "related_event_ids",
    "metadata",
}
KINDS = {
    "plan",
    "guardrail",
    "phase",
    "subphase",
    "edit",
    "test",
    "evidence",
    "readback",
    "armageddon",
    "commit",
    "blocker",
    "handoff",
    "archive",
}
STATUSES = {"planned", "active", "done", "blocked", "failed", "skipped", "archived"}
DAMAGE_RADII = {"", "small", "moderate", "large", "systemic"}
SUBPHASE_RE = re.compile(r"^###\s+Subphase\s+(\d+(?:\.\d+)+):\s*(.+)$", re.MULTILINE)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def state_path(raw: str | None) -> Path:
    return Path(raw) if raw else DEFAULT_FILE


def append_record(path: Path, record: dict[str, object]) -> None:
    from mega_store import append_jsonl
    append_jsonl(path, record)


def read_records(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    if not path.exists():
        return records, [f"state file not found: {path}"]
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(record, dict):
            errors.append(f"line {line_no}: record must be a JSON object")
            continue
        record["_line"] = line_no
        records.append(record)
    return records, errors


def validation_errors(records: list[dict[str, object]], parse_errors: list[str]) -> list[str]:
    errors = list(parse_errors)
    seen: set[str] = set()
    previous_key: tuple[str, str] | None = None
    for record in records:
        line = int(record.get("_line", 0))
        missing = sorted(REQUIRED_FIELDS - set(record))
        if missing:
            errors.append(f"line {line}: missing required fields: {', '.join(missing)}")
        event_id = str(record.get("event_id", ""))
        if not event_id:
            errors.append(f"line {line}: event_id is required")
        elif event_id in seen:
            errors.append(f"line {line}: duplicate event_id: {event_id}")
        seen.add(event_id)
        timestamp = str(record.get("timestamp", ""))
        sequence = int(record.get("sequence", line))
        current_key = (timestamp, sequence)
        if previous_key and current_key < previous_key:
            errors.append(f"line {line}: event order moved backwards")
        previous_key = current_key
        kind = str(record.get("kind", ""))
        if kind and kind not in KINDS:
            errors.append(f"line {line}: unknown kind: {kind}")
        status = str(record.get("status", ""))
        if status and status not in STATUSES:
            errors.append(f"line {line}: unknown status: {status}")
        damage_radius = str(record.get("damage_radius", "")).lower()
        if damage_radius not in DAMAGE_RADII:
            errors.append(f"line {line}: unknown damage_radius: {damage_radius}")
        related = record.get("related_event_ids", [])
        if related is None:
            related = []
        if not isinstance(related, list) or not all(isinstance(item, str) for item in related):
            errors.append(f"line {line}: related_event_ids must be a list of strings")
        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            errors.append(f"line {line}: metadata must be an object")
    valid_ids = {str(record.get("event_id", "")) for record in records}
    for record in records:
        line = int(record.get("_line", 0))
        for related_id in record.get("related_event_ids", []) if isinstance(record.get("related_event_ids", []), list) else []:
            if related_id not in valid_ids:
                errors.append(f"line {line}: related_event_id not found: {related_id}")
    return errors


def clean_record(record: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in record.items() if key != "_line"}


def normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", str(value).lower()).strip()


def plan_subphases(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"plan file not found: {path}")
    text = path.read_text(encoding="utf-8")
    return [(match.group(1), match.group(2).strip()) for match in SUBPHASE_RE.finditer(text)]


def subphase_completed(records: list[dict[str, object]], number: str, title: str) -> bool:
    relevant = [r for r in records if str(r.get('subphase', '')).strip() == number
                and r.get('kind') in {'subphase', 'edit'}]
    return bool(relevant) and relevant[-1].get('kind') == 'subphase' and relevant[-1].get('status') == 'done'


def blocked_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    latest = {}
    for record in records:
        if record.get('kind') == 'blocker':
            key = record.get('metadata', {}).get('blocker_id', record.get('subphase', ''))
            latest[key] = record
    return [r for r in latest.values() if r.get('status') in {'blocked', 'failed'}]


def cmd_final_gate(args: argparse.Namespace) -> int:
    if getattr(args, 'task', None):
        from mega_completion import evaluate
        from mega_store import read_json, safe_id
        from mega_agents import open_agents
        root = Path(args.root).resolve()
        try:
            contract = read_json(root / 'tasks' / (safe_id(args.task) + '.json'))
        except (ValueError, OSError):
            print('Mega final gate failed: invalid task contract.')
            return 1
        if not contract or Path(contract['plan']).resolve() != Path(args.plan).resolve():
            print('Mega final gate failed: requested plan does not match task contract.')
            return 1
        parent = contract.get('session_id')
        children = [c for c in open_agents(root, args.task) if c.get('parent_session_id') == parent]
        if children:
            print('Mega final gate failed: owned children still require native closure receipts.')
            return 1
        result = evaluate(Path(args.root), args.task)
        valid = result['verdict'] == ('complete' if args.verdict == 'done' else 'blocked')
        print(json.dumps(result, sort_keys=True))
        print('Mega final gate passed.' if valid else 'Mega final gate failed.')
        return 0 if valid else 1
    records, parse_errors = read_records(state_path(args.file))
    errors = validation_errors(records, parse_errors)
    if errors:
        print("Mega final gate failed: state ledger is invalid.")
        for error in errors:
            print(f"- {error}")
        return 1
    try:
        subphases = plan_subphases(Path(args.plan))
    except FileNotFoundError as exc:
        print(f"Mega final gate failed: {exc}")
        return 1
    if not subphases or len({n for n, _ in subphases}) != len(subphases):
        print('Mega final gate failed: plan needs nonempty unique subphases.')
        return 1
    target = Path(args.plan).resolve()
    def belongs(record):
        raw = Path(str(record.get('plan', '')))
        resolved = raw.resolve() if raw.is_absolute() else (Path(str(record.get('cwd', ''))) / raw).resolve()
        return resolved == target
    records = [r for r in records if belongs(r)]
    blockers = blocked_records(records)
    incomplete = [
        f"Subphase {number}: {title}"
        for number, title in subphases
        if not subphase_completed(records, number, title)
    ]

    print("Mega final gate")
    print(f"- plan: {args.plan}")
    print(f"- state: {state_path(args.file)}")
    print(f"- verdict: {args.verdict}")
    print(f"- subphases: {len(subphases)}")
    print(f"- incomplete: {len(incomplete)}")
    print(f"- blockers: {len(blockers)}")

    if args.whole_plan and args.verdict == "not-done":
        print("Mega final gate failed: whole-plan execution cannot final as not-done without continuing or naming a real blocker.")
        return 1
    if args.verdict == "done" and incomplete:
        print("Mega final gate failed: done verdict has incomplete plan subphases.")
        for item in incomplete:
            print(f"- {item}")
        return 1
    if args.verdict == "blocked" and not blockers:
        print("Mega final gate failed: blocked verdict requires a blocker event in the state ledger.")
        return 1
    if args.verdict == 'blocked':
        covered = {str(r.get('subphase', '')) for r in blockers}
        required = {n for n, title in subphases if not subphase_completed(records, n, title)}
        if not required.issubset(covered):
            print('Mega final gate failed: independent incomplete subphases are not blocked.')
            return 1
    if args.whole_plan and incomplete and not blockers:
        print("Mega final gate failed: whole-plan request still has executable incomplete subphases and no blocker.")
        for item in incomplete:
            print(f"- {item}")
        return 1
    print("Mega final gate passed.")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    path = state_path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    print(f"initialized state ledger: {path}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    metadata = json.loads(args.metadata) if args.metadata else {}
    if not isinstance(metadata, dict):
        print("--metadata must decode to a JSON object")
        return 2
    record = {
        "event_id": args.event_id or f"evt-{uuid4().hex[:12]}",
        "timestamp": args.timestamp or now(),
        "cwd": str(Path.cwd()),
        "plan": args.plan,
        "phase": args.phase,
        "subphase": args.subphase or "",
        "kind": args.kind,
        "status": args.status,
        "summary": args.summary,
        "damage_radius": args.damage_radius or "",
        "branch": args.branch or "",
        "related_event_ids": args.related_event_id or [],
        "metadata": metadata,
    }
    append_record(state_path(args.file), record)
    print(f"recorded state: {record['event_id']} | {record['phase']} | {record['status']}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    records, parse_errors = read_records(state_path(args.file))
    errors = validation_errors(records, parse_errors)
    if errors:
        print("Mega state validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Mega state validation passed.")
    print(f"- file: {state_path(args.file)}")
    print(f"- records: {len(records)}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    path = state_path(args.file)
    records, parse_errors = read_records(path)
    errors = validation_errors(records, parse_errors)
    print("Mega state summary")
    print(f"- file: {path}")
    print(f"- records: {len(records)}")
    if errors:
        print(f"- validation errors: {len(errors)}")
        for error in errors[: args.last]:
            print(f"  - {error}")
        return 1
    for record in records[-args.last :]:
        print(
            f"- {record.get('timestamp')} | {record.get('phase')} | "
            f"{record.get('subphase')} | {record.get('kind')} | "
            f"{record.get('status')} | {record.get('summary')}"
        )
    return 0 if records else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="create the state ledger if missing")
    init.add_argument("--file")
    init.set_defaults(func=cmd_init)

    record = sub.add_parser("record", help="append an execution state event")
    record.add_argument("--plan", required=True)
    record.add_argument("--phase", required=True)
    record.add_argument("--subphase")
    record.add_argument("--kind", required=True, choices=sorted(KINDS))
    record.add_argument("--status", required=True, choices=sorted(STATUSES))
    record.add_argument("--summary", required=True)
    record.add_argument("--damage-radius")
    record.add_argument("--branch")
    record.add_argument("--related-event-id", action="append")
    record.add_argument("--metadata")
    record.add_argument("--event-id")
    record.add_argument("--timestamp")
    record.add_argument("--file")
    record.set_defaults(func=cmd_record)

    validate = sub.add_parser("validate", help="validate ordered state records")
    validate.add_argument("--file")
    validate.set_defaults(func=cmd_validate)

    summary = sub.add_parser("summary", help="summarize ordered state records")
    summary.add_argument("--file")
    summary.add_argument("--last", type=int, default=20)
    summary.set_defaults(func=cmd_summary)

    final_gate = sub.add_parser("final-gate", help="check whether a final handoff is allowed")
    final_gate.add_argument("--plan", required=True)
    final_gate.add_argument("--file")
    final_gate.add_argument('--task', help='use strict task contract and current linked proof')
    final_gate.add_argument('--root', default='.mega')
    final_gate.add_argument("--verdict", choices=["done", "blocked", "not-done"], default="done")
    final_gate.add_argument(
        "--whole-plan",
        action="store_true",
        help="enforce that a whole-plan request cannot stop on partial progress",
    )
    final_gate.set_defaults(func=cmd_final_gate)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
