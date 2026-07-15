#!/usr/bin/env python3
"""Record and summarize Megaskill verification evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_FILE = Path(".mega/evidence.jsonl")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def evidence_path(raw: str | None) -> Path:
    return Path(raw) if raw else DEFAULT_FILE


def append_record(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def cmd_record(args: argparse.Namespace) -> int:
    record = {
        "timestamp": now(),
        "cwd": str(Path.cwd()),
        "phase": args.phase,
        "command": args.command,
        "exit_code": args.exit_code,
        "note": args.note or "",
    }
    append_record(evidence_path(args.file), record)
    print(f"recorded evidence: {args.command} -> exit {args.exit_code}")
    return 0 if args.exit_code == 0 else int(args.exit_code)


def cmd_run(args: argparse.Namespace) -> int:
    if not args.command:
        print("mega_evidence run requires a command after --")
        return 2
    command = " ".join(args.command)
    result = subprocess.run(args.command)
    record = {
        "timestamp": now(),
        "cwd": str(Path.cwd()),
        "phase": args.phase,
        "command": command,
        "exit_code": result.returncode,
        "note": args.note or "",
    }
    append_record(evidence_path(args.file), record)
    print(f"recorded evidence: {command} -> exit {result.returncode}")
    return result.returncode


def read_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def cmd_summary(args: argparse.Namespace) -> int:
    path = evidence_path(args.file)
    records = read_records(path)
    print("Mega evidence summary")
    print(f"- file: {path}")
    print(f"- records: {len(records)}")
    if not records:
        return 1
    failures = [r for r in records if int(r.get("exit_code", 1)) != 0]
    print(f"- failures: {len(failures)}")
    for record in records[-args.last :]:
        note = f" | {record.get('note')}" if record.get("note") else ""
        print(
            f"- {record.get('timestamp')} | {record.get('phase')} | "
            f"{record.get('command')} | exit {record.get('exit_code')}{note}"
        )
    return 1 if failures and args.fail_on_failure else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="record an already-run command")
    record.add_argument("--phase", required=True)
    record.add_argument("--command", required=True)
    record.add_argument("--exit-code", type=int, required=True)
    record.add_argument("--note")
    record.add_argument("--file")
    record.set_defaults(func=cmd_record)

    run = sub.add_parser("run", help="run a command and record its exit code")
    run.add_argument("--phase", required=True)
    run.add_argument("--note")
    run.add_argument("--file")
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(func=cmd_run)

    summary = sub.add_parser("summary", help="summarize recorded evidence")
    summary.add_argument("--file")
    summary.add_argument("--last", type=int, default=20)
    summary.add_argument("--fail-on-failure", action="store_true")
    summary.set_defaults(func=cmd_summary)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
