#!/usr/bin/env python3
"""Append-only decision lifecycle and durable Markdown ADRs (stdlib, POSIX)."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4

from mega_store import locked as store_locked

DEFAULT_FILE = Path(".mega/decisions.jsonl")
KINDS = {"architecture", "ui", "product", "data", "schema", "scope", "verification",
         "root-cause", "generality", "dependency", "risk", "branch", "policy"}
TRANSITIONS = {
    "proposed": {"challenged", "rejected"},
    "challenged": {"accepted", "committed", "rejected"},
    "accepted": {"committed", "executed", "rejected", "superseded"},
    "committed": {"executed", "superseded"},
    "executed": {"validated", "superseded"},
    "validated": {"superseded"}, "rejected": set(), "superseded": set(),
}
ACCEPTED = {"accepted", "committed", "executed", "validated"}
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TEXT_FIELDS = ("question", "decision", "why", "self_critique", "disconfirming_evidence",
               "disconfirming_test", "tradeoffs", "reversibility", "follow_up")
LIST_FIELDS = ("alternatives", "assumptions", "evidence_refs", "state_event_ids")
LINK_FIELDS = ("task_id", "plan", "plan_sha256", "phase", "subphase")
COMMON = {"schema_version", "event_id", "decision_id", "timestamp", "event", "status",
          "reason", *LINK_FIELDS}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def load_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def read_records(path):
    """Return records and diagnostics; never skip corruption silently."""
    path = Path(path)
    if not path.exists():
        return [], [f"decision file not found: {path}"]
    raw = path.read_text(encoding="utf-8")
    records, errors = [], []
    if raw and not raw.endswith("\n"):
        errors.append("ledger has an unterminated final line")
    for number, line in enumerate(raw.splitlines(), 1):
        try:
            record = load_json(line)
            if not isinstance(record, dict):
                raise ValueError("record must be a JSON object")
            records.append(record)
        except ValueError as exc:
            errors.append(f"line {number}: invalid JSON: {exc}")
    return records, errors


def replay(records):
    """Validate the entire ordered history, returning current immutable snapshots."""
    current, seen, errors = {}, set(), []
    previous_time = None
    for number, row in enumerate(records, 1):
        try:
            missing = COMMON - row.keys()
            if missing:
                raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
            if type(row["schema_version"]) is not int or row["schema_version"] != 1:
                raise ValueError("unsupported schema_version")
            for field in ("event_id", "decision_id", "task_id"):
                if not isinstance(row[field], str) or not TOKEN.fullmatch(row[field]):
                    raise ValueError(f"invalid {field}")
            if row["event_id"] in seen:
                raise ValueError("duplicate event_id")
            seen.add(row["event_id"])
            timestamp = datetime.fromisoformat(row["timestamp"])
            if timestamp.tzinfo is None:
                raise ValueError("timestamp must include timezone")
            if previous_time and timestamp < previous_time:
                raise ValueError("event order moved backwards")
            previous_time = timestamp
            for field in (*LINK_FIELDS, "reason"):
                if not nonempty(row[field]):
                    raise ValueError(f"{field} must be a nonempty string")
            if not Path(row["plan"]).is_absolute() or str(Path(row["plan"]).resolve()) != row["plan"]:
                raise ValueError("plan must be a canonical absolute path")
            if not re.fullmatch(r"[0-9a-f]{64}", row["plan_sha256"]):
                raise ValueError("invalid plan_sha256")
            if not re.fullmatch(r"\d+", row["phase"]) or not re.fullmatch(
                    re.escape(row["phase"]) + r"\.\d+(?:\.\d+)*", row["subphase"]):
                raise ValueError("subphase must belong to the exact phase")
            if row["event"] == "record":
                if row["decision_id"] in current:
                    raise ValueError("duplicate decision_id")
                if row["status"] != "proposed":
                    raise ValueError("new decisions must be proposed")
                for field in TEXT_FIELDS:
                    if not nonempty(row.get(field)):
                        raise ValueError(f"{field} must be a nonempty string")
                for field in LIST_FIELDS:
                    value = row.get(field)
                    if not isinstance(value, list) or not all(nonempty(item) for item in value):
                        raise ValueError(f"{field} must be a list of nonempty strings")
                    if field in {"alternatives", "assumptions"} and not value:
                        raise ValueError(f"{field} must not be empty")
                    if len(set(value)) != len(value):
                        raise ValueError(f"duplicate {field}")
                if row.get("kind") not in KINDS or type(row.get("durable")) is not bool:
                    raise ValueError("invalid kind or durable flag")
                if row["decision"] in row["alternatives"]:
                    raise ValueError("alternatives must differ from the chosen decision")
                supersedes = row.get("supersedes")
                if supersedes is not None:
                    old = current.get(supersedes) if isinstance(supersedes, str) else None
                    if old is None or old["status"] not in ACCEPTED:
                        raise ValueError("supersedes must name an existing accepted decision")
                    if any(row[key] != old[key] for key in LINK_FIELDS):
                        raise ValueError("supersedes crosses task/plan/subphase identity")
                allowed = COMMON | set(TEXT_FIELDS) | set(LIST_FIELDS) | {"kind", "durable", "supersedes"}
                if row.keys() - allowed:
                    raise ValueError("unknown record fields")
                current[row["decision_id"]] = dict(row)
            elif row["event"] in {"status", "promote"}:
                old = current.get(row["decision_id"])
                if old is None:
                    raise ValueError("decision_id not found")
                if any(row[key] != old[key] for key in LINK_FIELDS):
                    raise ValueError("event crosses task/plan/subphase identity")
                allowed = COMMON | ({"superseded_by"} if row["event"] == "status" else {"adr_path", "adr_sha256"})
                if row.keys() - allowed:
                    raise ValueError("unknown lifecycle fields (rationale is immutable)")
                if row["event"] == "status":
                    if row["status"] not in TRANSITIONS[old["status"]]:
                        raise ValueError(f"invalid transition {old['status']} -> {row['status']}")
                    if row["status"] == "superseded":
                        replacement = current.get(row.get("superseded_by"))
                        if replacement is None or replacement.get("supersedes") != row["decision_id"] or replacement["status"] not in ACCEPTED:
                            raise ValueError("superseded requires an accepted replacement")
                    elif "superseded_by" in row:
                        raise ValueError("superseded_by only belongs to supersession")
                else:
                    if old["status"] not in ACCEPTED or not old["durable"] or row["status"] != old["status"]:
                        raise ValueError("promotion requires an accepted durable decision")
                    if "adr_path" in old:
                        raise ValueError("duplicate promotion")
                    if not nonempty(row.get("adr_path")) or not Path(row["adr_path"]).is_absolute():
                        raise ValueError("adr_path must be absolute")
                    if not isinstance(row.get("adr_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["adr_sha256"]):
                        raise ValueError("invalid adr_sha256")
                current[row["decision_id"]] = {**old, **row}
            else:
                raise ValueError("unknown event")
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"line {number}: {exc}")
    # Supersession is a transaction: no accepted replacement may leave its old choice active.
    for row in current.values():
        if row["status"] in ACCEPTED and row.get("supersedes"):
            old = current[row["supersedes"]]
            if old["status"] != "superseded" or old.get("superseded_by") != row["decision_id"]:
                errors.append(f"{row['decision_id']}: incomplete supersession")
    return current, errors


def validation_errors(records, parse_errors=()):
    return list(parse_errors) + replay(records)[1]


@contextmanager
def locked(path):
    # Stable sidecar survives atomic replacement of the ledger inode.
    with store_locked(Path(str(path) + ".lock")):
        yield


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def history(path, allow_missing=False):
    if allow_missing and not path.exists():
        return [], {}
    records, errors = read_records(path)
    current, lifecycle_errors = replay(records)
    if errors or lifecycle_errors:
        raise ValueError("; ".join(errors + lifecycle_errors))
    return records, current


def append_events(path, records, events):
    errors = validation_errors(records + events)
    if errors:
        raise ValueError("; ".join(errors))
    prefix = path.read_bytes() if path.exists() else b""
    suffix = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in events).encode("utf-8")
    # Logical append-only; atomic multi-event transactions avoid torn supersession.
    atomic_write(path, prefix + suffix)


def linked_plan(args):
    path = Path(args.plan).resolve(strict=True)
    content = path.read_bytes()
    text = content.decode("utf-8")
    phases = re.findall(r"^##\s+Phase\s+(\d+):", text, re.M)
    if phases.count(args.phase) != 1:
        raise ValueError("exact phase not found in plan")
    matches, phase = [], None
    for line in text.splitlines():
        heading = re.match(r"^##\s+Phase\s+(\d+):", line)
        if heading:
            phase = heading[1]
        elif re.match(r"^##\s", line):
            phase = None
        subphase = re.match(r"^###\s+Subphase\s+(\d+(?:\.\d+)+):", line)
        if subphase and subphase[1] == args.subphase:
            matches.append(phase)
    if matches != [args.phase]:
        raise ValueError("exact subphase not found in plan")
    return str(path), hashlib.sha256(content).hexdigest()


def event_for(row, event, status, reason):
    return {"schema_version": 1, "event_id": "devt-" + uuid4().hex,
            "decision_id": row["decision_id"], "timestamp": now(), "event": event,
            "status": status, "reason": reason, **{key: row[key] for key in LINK_FIELDS}}


def scoped(current, args):
    row = current.get(args.decision_id)
    if row is None:
        raise ValueError("decision_id not found")
    if row["task_id"] != args.task_id or row["plan"] != str(Path(args.plan).resolve()):
        raise ValueError("decision belongs to a different task/plan")
    return row


def check_task(row, path, require_active=False):
    """Bind to the runtime task contract when available, without registering tasks."""
    task = load_json(path.read_text(encoding="utf-8"))
    if not isinstance(task, dict):
        raise ValueError("task contract must be a JSON object")
    if (task.get("task_id") != row["task_id"] or task.get("plan") != row["plan"]
            or task.get("plan_hash") != row["plan_sha256"]):
        raise ValueError("task contract disagrees with exact task/plan snapshot")
    obligations = task.get("obligations")
    if not isinstance(obligations, list) or not all(isinstance(item, dict) for item in obligations):
        raise ValueError("invalid task obligations")
    if sum(item.get("id") == row["subphase"] for item in obligations) != 1:
        raise ValueError("exact subphase missing or duplicated in task obligations")
    if require_active and (task.get("status") != "active" or task.get("mode") != "execute"):
        raise ValueError("task contract does not authorize active execution")


def check_refs(current, state_file=None, evidence_file=None):
    for filename, field, keys in ((state_file, "state_event_ids", ("event_id",)),
                                  (evidence_file, "evidence_refs", ("evidence_id", "id", "event_id"))):
        if not filename:
            continue
        records, errors = read_records(Path(filename))
        if errors:
            raise ValueError("; ".join(errors))
        for row in current.values():
            for ref in row[field]:
                matches = [item for item in records if any(item.get(key) == ref for key in keys)]
                if len(matches) != 1:
                    raise ValueError(f"{field}: unresolved or ambiguous ref {ref}")
                item = matches[0]
                # Legacy proof records may omit task identity, but never accept explicit conflicts.
                for key in ("task_id", "phase", "subphase"):
                    if key in item and item[key] != row[key]:
                        raise ValueError(f"{field}: ref {ref} crosses {key}")
                if "plan_hash" in item and item["plan_hash"] != row["plan_sha256"]:
                    raise ValueError(f"{field}: ref {ref} crosses plan snapshot")
                if "obligation_id" in item and item["obligation_id"] != row["subphase"]:
                    raise ValueError(f"{field}: ref {ref} crosses exact obligation")
                if "plan" in item:
                    proof_plan = Path(item["plan"])
                    if not proof_plan.is_absolute():
                        proof_plan = Path(item.get("cwd", Path(filename).resolve().parent.parent)) / proof_plan
                    if str(proof_plan.resolve()) != row["plan"]:
                        raise ValueError(f"{field}: ref {ref} crosses plan")


def adr_content(row):
    metadata = {key: row[key] for key in ("schema_version", "decision_id", "event_id", "task_id",
                "plan", "plan_sha256", "phase", "subphase", "kind", "status", "timestamp",
                "durable", "supersedes", "evidence_refs", "state_event_ids")}
    # JSON scalar/list values are a YAML-compatible subset; no YAML dependency needed.
    frontmatter = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items())
    sections = [("Context and question", row["question"]), ("Decision", row["decision"]),
                ("Rationale", row["why"]), ("Alternatives considered", row["alternatives"]),
                ("Assumptions", row["assumptions"]), ("Self-critique", row["self_critique"]),
                ("Disconfirming evidence", row["disconfirming_evidence"]),
                ("Cheapest disconfirming test", row["disconfirming_test"]),
                ("Consequences and tradeoffs", row["tradeoffs"]),
                ("Reversibility", row["reversibility"]), ("Follow-up triggers", row["follow_up"])]
    body = ""
    for title, value in sections:
        text = "\n".join("- " + item for item in value) if isinstance(value, list) else value
        body += f"\n## {title}\n\n{text}\n"
    return f"---\n{frontmatter}\n---\n\n# {row['decision_id']}: {row['question'].splitlines()[0]}\n{body}".encode("utf-8")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("record", "validate", "summary", "promote", "status"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--file", default=str(DEFAULT_FILE), help="decision ledger (default .mega/decisions.jsonl)")
        if name in {"record", "status", "promote"}:
            cmd.add_argument("--task-id", required=True)
            cmd.add_argument("--plan", required=True)
        if name != "summary":
            cmd.add_argument("--task-file", help="runtime task contract; writes auto-detect .mega/tasks/TASK_ID.json")
        if name == "record":
            cmd.add_argument("--decision-id", default=None)
            cmd.add_argument("--phase", required=True)
            cmd.add_argument("--subphase", required=True)
            cmd.add_argument("--kind", choices=sorted(KINDS), required=True)
            cmd.add_argument("--durable", action="store_true")
            cmd.add_argument("--supersedes")
            for field in TEXT_FIELDS:
                flags = ["--" + field.replace("_", "-")]
                if field == "why":
                    flags.append("--rationale")
                cmd.add_argument(*flags, dest=field, required=True)
            cmd.add_argument("--alternative", action="append", required=True)
            cmd.add_argument("--assumption", action="append", required=True)
            cmd.add_argument("--evidence-ref", action="append", default=[])
            cmd.add_argument("--state-event-id", action="append", default=[])
        if name in {"record", "validate"}:
            cmd.add_argument("--state-file")
            cmd.add_argument("--evidence-file")
        if name in {"status", "promote"}:
            cmd.add_argument("--decision-id", required=True)
        if name == "status":
            cmd.add_argument("--status", choices=sorted(TRANSITIONS), required=True)
            cmd.add_argument("--reason", required=True)
            cmd.add_argument("--superseded-by", help="required for explicit supersession")
        if name == "promote":
            cmd.add_argument("--output", help="default docs/adr/DECISION_ID.md")
        if name == "summary":
            cmd.add_argument("--task-id")
            cmd.add_argument("--plan")
            cmd.add_argument("--kind", choices=sorted(KINDS))
            cmd.add_argument("--status", choices=sorted(TRANSITIONS))
            cmd.add_argument("--json", action="store_true")
    return result


def run(args):
    path = Path(args.file).resolve()
    with locked(path):
        records, current = history(path, allow_missing=args.command == "record")
        if args.command == "record":
            plan, digest = linked_plan(args)
            row = {"decision_id": args.decision_id if args.decision_id is not None else "dec-" + uuid4().hex,
                   "task_id": args.task_id, "plan": plan, "plan_sha256": digest,
                   "phase": args.phase, "subphase": args.subphase}
            row = {**event_for(row, "record", "proposed", args.why),
                   **{key: getattr(args, key) for key in TEXT_FIELDS},
                   "kind": args.kind, "durable": args.durable, "supersedes": args.supersedes,
                   "alternatives": args.alternative, "assumptions": args.assumption,
                   "evidence_refs": args.evidence_ref, "state_event_ids": args.state_event_id}
            errors = validation_errors(records + [row])
            if errors:
                raise ValueError("; ".join(errors))
            task_file = Path(args.task_file) if args.task_file else path.parent / "tasks" / f"{row['task_id']}.json"
            if args.task_file or task_file.exists():
                check_task(row, task_file, require_active=True)
            check_refs(replay(records + [row])[0], args.state_file, args.evidence_file)
            append_events(path, records, [row])
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
        elif args.command == "status":
            row = scoped(current, args)
            task_file = Path(args.task_file) if args.task_file else path.parent / "tasks" / f"{row['task_id']}.json"
            if args.task_file or task_file.exists():
                check_task(row, task_file, require_active=True)
            event = event_for(row, "status", args.status, args.reason)
            if args.superseded_by:
                event["superseded_by"] = args.superseded_by
            events = [event]
            if args.status in ACCEPTED and row["status"] not in ACCEPTED and row.get("supersedes"):
                old = current[row["supersedes"]]
                events.append({**event_for(old, "status", "superseded", args.reason),
                               "superseded_by": row["decision_id"]})
            append_events(path, records, events)
            print(json.dumps(replay(records + events)[0][row["decision_id"]], ensure_ascii=False, sort_keys=True))
        elif args.command == "validate":
            if args.task_file:
                for row in current.values():
                    check_task(row, Path(args.task_file))
            check_refs(current, args.state_file, args.evidence_file)
            print(f"Decision validation passed: {len(records)} events, {len(current)} decisions")
        elif args.command == "summary":
            rows = [row for row in current.values() if
                    (not args.task_id or row["task_id"] == args.task_id) and
                    (not args.plan or row["plan"] == str(Path(args.plan).resolve())) and
                    (not args.kind or row["kind"] == args.kind) and
                    (not args.status or row["status"] == args.status)]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, sort_keys=True))
            else:
                for row in rows:
                    print(f"{row['decision_id']} [{row['kind']}/{row['status']}] task={row['task_id']} plan={row['plan']} {row['subphase']}")
                    print(f"  {row['question']}\n  Chosen: {row['decision']}\n  Why: {row['why']}")
                    if row.get("superseded_by"):
                        print(f"  Superseded by: {row['superseded_by']}")
                print(f"{len(rows)} decisions")
        else:
            row = scoped(current, args)
            task_file = Path(args.task_file) if args.task_file else path.parent / "tasks" / f"{row['task_id']}.json"
            if args.task_file or task_file.exists():
                check_task(row, task_file, require_active=True)
            if row["status"] not in ACCEPTED or not row["durable"]:
                raise ValueError("promotion requires an accepted durable decision")
            output = Path(args.output or f"docs/adr/{row['decision_id']}.md").resolve()
            if output == path or output == Path(str(path) + ".lock") or output.suffix != ".md":
                raise ValueError("ADR output must be a Markdown file distinct from the ledger")
            if "adr_path" in row:
                if str(output) != row["adr_path"] or not output.exists() or hashlib.sha256(output.read_bytes()).hexdigest() != row["adr_sha256"]:
                    raise ValueError("promoted ADR is missing, changed, or at a different path")
                print(json.dumps({"adr_path": str(output), "decision_id": row["decision_id"], "already_promoted": True}))
                return
            content = adr_content(row)
            event = {**event_for(row, "promote", row["status"], "Promoted durable accepted decision"),
                     "adr_path": str(output), "adr_sha256": hashlib.sha256(content).hexdigest()}
            errors = validation_errors(records + [event])
            if errors:
                raise ValueError("; ".join(errors))
            with locked(output):
                if output.exists() and output.read_bytes() != content:
                    raise ValueError("ADR output already exists with different content")
                # Write ADR first; a crash leaves a matching file that a retry can adopt.
                if not output.exists():
                    atomic_write(output, content)
                append_events(path, records, [event])
            print(json.dumps(event, sort_keys=True))


def main():
    args = parser().parse_args()
    try:
        run(args)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(f"Decision {args.command} failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
