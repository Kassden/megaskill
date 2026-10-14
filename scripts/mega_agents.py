#!/usr/bin/env python3
"""Track bounded, task/parent-owned children; native tools alone close threads."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile


ROLES = {
    "thinker": "Explore assumptions, alternatives and disconfirming evidence.",
    "planner": "Define scoped work, dependencies and acceptance criteria.",
    "executor": "Implement within the assigned edit set.",
    "tester": "Exercise behavior and adversarial cases; report evidence.",
    "verifier": "Independently check acceptance criteria and outcome readback.",
    "orchestrator": "Coordinate dependencies and handoff; never spawn descendants.",
}
DEFAULT_MAX_OPEN = 3


def _text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(
        ord(c) < 32 for c in value
    ):
        raise ValueError(f"{field} must be a nonempty, trimmed string without control characters")
    return value


def _limit(value) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("max_open must be a positive integer")
    return value


def _edits(value, root: Path) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("edit_set must be a list of literal paths")
    paths = []
    workspace = root.resolve().parent
    for raw in value:
        _text(raw, "edit path")
        if any(c in raw for c in "*?[]"):
            raise ValueError("edit paths must be literal, not globs")
        path = Path(raw)
        path = (workspace / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_relative_to(workspace) or path.is_relative_to(root.resolve()):
            raise ValueError("edit paths must stay within workspace and outside registry root")
        paths.append(str(path))
    return sorted(set(paths))


def _receipt(value, agent_id: str) -> dict:
    # Bind the unmodified native result to the exact call, not a claimed closed flag.
    if not isinstance(value, dict) or value.get("tool") not in ("close_agent", "multi_agent_v1__close_agent"):
        raise ValueError("receipt must identify native close_agent")
    if value.get("arguments") not in ({"id": agent_id}, {"target": agent_id}):
        raise ValueError("receipt arguments must identify this exact child")
    result = value.get("result")
    if not isinstance(result, dict) or set(result) not in ({"status"}, {"previous_status"}):
        raise ValueError("receipt result must contain native status or previous_status")
    status = result.get("previous_status", result.get("status"))
    if isinstance(status, str) and status in {"pending_init", "running", "shutdown", "interrupted"}:
        return value
    if isinstance(status, dict) and len(status) == 1:
        key = next(iter(status))
        if (key == "completed" and (status[key] is None or isinstance(status[key], str))
                or key == "errored" and isinstance(status[key], str)):
            return value
    raise ValueError("unsupported or unsuccessful native close result")


def _read(root: Path) -> dict:
    path = root / "agents.json"
    if not path.exists():
        return {"version": 1, "agents": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("unsupported agent registry")
    if not isinstance(data.get("agents"), list):
        raise ValueError("registry agents must be a list")
    ids = set()
    for row in data["agents"]:
        if not isinstance(row, dict):
            raise ValueError("invalid agent record")
        for field in ("agent_id", "task_id", "parent_session_id", "objective", "verification"):
            _text(row.get(field), field)
        if row["agent_id"] in ids or row["agent_id"] == row["parent_session_id"]:
            raise ValueError("duplicate or self-owned child")
        ids.add(row["agent_id"])
        if (not isinstance(row.get("role"), str) or row["role"] not in ROLES
                or row.get("status") not in ("assigned", "completed", "closed")):
            raise ValueError("invalid agent role or status")
        _limit(row.get("max_open"))
        if row.get("edit_set") != _edits(row.get("edit_set"), root):
            raise ValueError("registry edit paths must be canonical")
        if row["status"] == "closed":
            _receipt(row.get("close_receipt"), row["agent_id"])
        elif "close_receipt" in row:
            raise ValueError("open child has a close receipt")
    if any(row["parent_session_id"] in ids for row in data["agents"]):
        raise ValueError("registry contains recursive ownership")
    return data


@contextmanager
def _transaction(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    # Lock a stable inode; agents.json itself is replaced atomically.
    with (root / ".agents.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = _read(root)
        before = json.dumps(data, sort_keys=True)
        yield data
        after = json.dumps(data, sort_keys=True)
        if before == after:
            return
        fd, name = tempfile.mkstemp(prefix=".agents-", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(after + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, root / "agents.json")
        finally:
            if os.path.exists(name):
                os.unlink(name)


def _owner(task_id: str, parent_session_id: str):
    _text(task_id, "task_id")
    _text(parent_session_id, "parent_session_id")


def _owned(data: dict, task_id: str, parent_session_id: str) -> list:
    return [row for row in data["agents"] if row["task_id"] == task_id
            and row["parent_session_id"] == parent_session_id]


def _spawn_check(data: dict, task_id: str, parent_session_id: str) -> dict:
    if any(row["agent_id"] == parent_session_id for row in data["agents"]):
        return {"allowed": False, "reason": "recursive spawning by a registered child is forbidden"}
    owned = _owned(data, task_id, parent_session_id)
    limit = owned[0]["max_open"] if owned else DEFAULT_MAX_OPEN
    if any(row["max_open"] != limit for row in owned):
        raise ValueError("inconsistent owner quota in registry")
    count = sum(row["status"] != "closed" for row in owned)
    return {"allowed": count < limit, "open_count": count, "max_open": limit,
            "reason": "owned child slot available" if count < limit else
            "open owned child quota exceeded; completed children still count"}


def check_spawn(root: Path, task_id: str, parent_session_id: str) -> dict:
    """Read-only PreToolUse decision; actual spawned IDs arrive in PostToolUse."""
    _owner(task_id, parent_session_id)
    return _spawn_check(_read(root), task_id, parent_session_id)


def assign(root: Path, task_id: str, parent_session_id: str, agent_id: str,
           role: str, objective: str, edit_set: list[str], verification: str,
           max_open: int = DEFAULT_MAX_OPEN) -> dict:
    """Register a native child ID; never invoke a spawn tool."""
    _owner(task_id, parent_session_id)
    _text(agent_id, "agent_id")
    _text(objective, "objective")
    _text(verification, "verification")
    if not isinstance(role, str) or role not in ROLES:
        raise ValueError("unknown responsibility")
    _limit(max_open)
    edits = _edits(edit_set, root)
    with _transaction(root) as data:
        if agent_id == parent_session_id or any(
            row["agent_id"] == parent_session_id or row["parent_session_id"] == agent_id
            for row in data["agents"]
        ):
            raise ValueError("recursive spawning/self-ownership is forbidden")
        existing = next((row for row in data["agents"] if row["agent_id"] == agent_id), None)
        refining = (existing is not None and existing["task_id"] == task_id
                    and existing["parent_session_id"] == parent_session_id
                    and existing.get("scope_confirmed") is False and existing["status"] != "closed")
        if existing is not None and not refining:
            raise ValueError("child ID is already registered; ownership cannot be reassigned")
        owned = _owned(data, task_id, parent_session_id)
        if any(row["max_open"] != max_open for row in owned):
            raise ValueError("max_open is fixed for this task and parent")
        if not refining and sum(row["status"] != "closed" for row in owned) >= max_open:
            raise ValueError("open owned child quota exceeded; completed children still count")
        for row in data["agents"]:
            if row["status"] == "closed" or row is existing:
                continue
            for left in map(Path, edits):
                for right in map(Path, row["edit_set"]):
                    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
                        raise ValueError(f"edit set overlaps open child {row['agent_id']}")
        if refining:
            row = existing
            row.update(role=role, objective=objective, edit_set=edits,
                       verification=verification, scope_confirmed=True)
        else:
            row = dict(agent_id=agent_id, task_id=task_id, parent_session_id=parent_session_id,
                       role=role, objective=objective, edit_set=edits, verification=verification,
                       max_open=max_open, status="assigned")
            data["agents"].append(row)
    return row


def list_agents(root: Path, task_id: str, parent_session_id: str) -> list:
    _owner(task_id, parent_session_id)
    return _owned(_read(root), task_id, parent_session_id)


def open_agents(root: Path, task_id: str) -> list:
    """Return unclosed records for this exact task across its parents, read-only."""
    _text(task_id, "task_id")
    return [row for row in _read(root)["agents"]
            if row["task_id"] == task_id and row["status"] != "closed"]


def _change(root: Path, task_id: str, parent_session_id: str, agent_id: str,
            receipt: dict | None = None) -> dict:
    _owner(task_id, parent_session_id)
    _text(agent_id, "agent_id")
    if receipt is not None:
        _receipt(receipt, agent_id)
    with _transaction(root) as data:
        row = next((row for row in _owned(data, task_id, parent_session_id)
                    if row["agent_id"] == agent_id), None)
        if row is None:
            raise ValueError("child is not owned by this exact task and parent")
        if row["status"] == "closed":
            if receipt is not None and row["close_receipt"] == receipt:
                return row
            raise ValueError("closed child cannot be completed or have its receipt replaced")
        row["status"] = "closed" if receipt is not None else "completed"
        if receipt is not None:
            row["close_receipt"] = receipt
    return row


def complete(root: Path, task_id: str, parent_session_id: str, agent_id: str) -> dict:
    return _change(root, task_id, parent_session_id, agent_id)


def close(root: Path, task_id: str, parent_session_id: str, agent_id: str, receipt: dict) -> dict:
    _receipt(receipt, agent_id)
    return _change(root, task_id, parent_session_id, agent_id, receipt)


def cleanup(root: Path, task_id: str, parent_session_id: str) -> dict:
    """Report exact calls; do not write storage or close native children."""
    ids = [row["agent_id"] for row in list_agents(root, task_id, parent_session_id)
           if row["status"] != "closed"]
    return {"task_id": task_id, "parent_session_id": parent_session_id,
            "owned_ids": ids, "required_native_close_calls": [
                {"tool": "close_agent", "arguments": {"target": agent_id}} for agent_id in ids
            ]}


def _observe_tool(payload: dict, root: Path, task_id: str, parent: str) -> dict:
    tool = payload.get("tool_name")
    if tool not in ("spawn_agent", "multi_agent_v1__spawn_agent", "close_agent", "multi_agent_v1__close_agent"):
        return {"observed": False, "reason": "unrelated tool"}
    inputs, response = payload.get("tool_input"), payload.get("tool_response")
    if not isinstance(inputs, dict) or not isinstance(response, dict):
        raise ValueError("native tool_input and tool_response must be JSON objects")
    if tool.endswith("close_agent"):
        if "target" in inputs and "id" in inputs:
            raise ValueError("ambiguous close target/id arguments")
        agent_id = _text(inputs.get("target", inputs.get("id")), "close target")
        if not any(row["agent_id"] == agent_id for row in list_agents(root, task_id, parent)):
            return {"observed": False, "reason": "child not owned"}
        proof = {"tool": tool, "arguments": inputs, "result": response}
        row = close(root, task_id, parent, agent_id, proof)
        return {"observed": True, "agent": row}
    if "agent_id" not in response:
        return {"observed": False, "reason": "spawn response has no child ID"}
    if any(key in response for key in ("error", "isError")):
        raise ValueError("spawn response contains error fields")
    agent_id = _text(response["agent_id"], "spawned agent_id")
    with _transaction(root) as data:
        existing = next((row for row in data["agents"] if row["agent_id"] == agent_id), None)
        if existing is not None:
            if existing["task_id"] != task_id or existing["parent_session_id"] != parent:
                return {"observed": False, "reason": "child not owned"}
            # A delayed spawn result must not erase assignment, completion, or closure.
            return {"observed": True, "agent": existing}
        if agent_id == parent or any(row["parent_session_id"] == agent_id for row in data["agents"]):
            raise ValueError("recursive spawning/self-ownership is forbidden")
        check = _spawn_check(data, task_id, parent)
        if "open_count" not in check:
            raise ValueError(check["reason"])
        raw_role = inputs.get("role", inputs.get("agent_type", "default"))
        if isinstance(raw_role, str) and raw_role.startswith("megaskill-"):
            raw_role = raw_role.removeprefix("megaskill-")
        role = raw_role if isinstance(raw_role, str) and raw_role in ROLES else (
            "thinker" if raw_role == "explorer" else "executor")
        message = inputs.get("message", inputs.get("prompt", ""))
        objective = " ".join(message.split())[:240].strip() if isinstance(message, str) else ""
        _text(objective or "Confirm scope from native spawn instructions", "spawn objective")
        row = dict(agent_id=agent_id, task_id=task_id, parent_session_id=parent,
                   role=role, objective=objective or "Confirm scope from native spawn instructions",
                   edit_set=[], verification="Parent must confirm verification criteria",
                   max_open=check["max_open"], status="assigned", scope_confirmed=False,
                   spawn_receipt={"tool": tool, "arguments": inputs, "result": response})
        # PostToolUse cannot undo a native spawn. Keep raced/excess children visible for cleanup.
        if not check["allowed"]:
            row["policy_violation"] = check["reason"]
        data["agents"].append(row)
    return {"observed": True, "agent": row, "role_metadata": {
        "role": role, "description": ROLES[role], "scope_confirmed": False}}


def observe(payload: dict, root: Path, task_id: str) -> dict:
    """Observe lifecycle or actual native tool results, preserving exact ownership."""
    _text(task_id, "task_id")
    if not isinstance(payload, dict):
        raise ValueError("hook payload must be an object")
    event = payload.get("hook_event_name")
    if event not in ("SubagentStart", "SubagentStop", "PostToolUse"):
        raise ValueError("unsupported subagent hook event")
    parent = _text(payload.get("session_id"), "session_id")
    if "task_id" in payload and payload["task_id"] != task_id:
        return {"observed": False, "reason": "task mismatch"}
    if event == "PostToolUse":
        return _observe_tool(payload, root, task_id, parent)
    agent_id = _text(payload.get("agent_id"), "agent_id")
    if not any(row["agent_id"] == agent_id for row in list_agents(root, task_id, parent)):
        return {"observed": False, "reason": "child not owned"}
    with _transaction(root) as data:
        row = next(row for row in _owned(data, task_id, parent) if row["agent_id"] == agent_id)
        if row["status"] == "closed":
            return {"observed": False, "reason": "child already closed"}
        row["status"] = "assigned" if event == "SubagentStart" else "completed"
        row["last_observation"] = {"event": event,
                                   "timestamp": datetime.now(timezone.utc).isoformat()}
    return {"observed": True, "agent": row}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("roles", help="on-demand responsibilities; no mandatory roster")
    for name in ("assign", "list", "complete", "close", "cleanup"):
        command = sub.add_parser(name)
        command.add_argument("--root", type=Path, default=Path.cwd() / ".mega",
                             help="registry directory (workspace/.mega)")
        command.add_argument("--task-id", required=True)
        command.add_argument("--parent-session-id", required=True)
        if name in {"assign", "complete", "close"}:
            command.add_argument("--agent-id", required=True)
        if name == "assign":
            command.add_argument("--role", choices=ROLES, required=True)
            command.add_argument("--objective", required=True)
            command.add_argument("--edit", action="append", default=[], dest="edit_set")
            command.add_argument("--verification", required=True)
            command.add_argument("--max-open", type=int, default=DEFAULT_MAX_OPEN)
        if name == "close":
            command.add_argument("--receipt", required=True, type=Path,
                                 help="JSON call/result receipt file; '-' reads stdin")
    args = vars(parser.parse_args(argv))
    name = args.pop("command")
    try:
        if name == "roles":
            result = ROLES
        else:
            if name == "close":
                path = args["receipt"]
                args["receipt"] = json.loads(sys.stdin.read() if str(path) == "-"
                                             else path.read_text(encoding="utf-8"))
            result = {"assign": assign, "list": list_agents, "complete": complete,
                      "close": close, "cleanup": cleanup}[name](**args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
