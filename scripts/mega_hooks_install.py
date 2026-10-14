#!/usr/bin/env python3
"""Reversibly install Megaskill hooks; preview by default, never grant trust.

The adjacent .megaskill-manifest.json stores exact owned definitions and the
original bytes (base64) for recovery. Uninstall merges against current content;
it never blindly restores a backup over subsequent user edits. TOML is edited
as text so comments, formatting, and unrelated tables survive.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile


EVENTS = (
    "UserPromptSubmit", "SessionStart", "PreCompact", "PostCompact", "Stop",
    "SubagentStart", "SubagentStop", "PreToolUse", "PostToolUse", "Interrupt",
)
RESTORATION_EVENTS = {"SessionStart", "UserPromptSubmit", "SubagentStart"}
OWNER = "megaskill-hooks-v1"


def definitions():
    handler = Path(__file__).resolve().with_name("mega_hooks.py")
    result = {}
    for event in EVENTS:
        command = shlex.join([sys.executable, str(handler), "--event", event])
        hook = {"type": "command", "command": command, "async": False,
                "timeout": 3 if event == "Interrupt" else 5,
                "statusMessage": f"Megaskill {event}"}
        if event in RESTORATION_EVENTS:
            hook["additionalContextLimit"] = 1500
        result[event] = {"hooks": [hook]}
    return result


def read_bytes(path):
    if path.is_symlink():
        raise ValueError(f"Refusing symlink: {path}")
    return path.read_bytes() if path.exists() else None


def parse(raw, toml):
    if raw is None:
        return {}
    if toml:
        import tomllib
        data = tomllib.loads(raw.decode("utf-8"))
    else:
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON key: {key}")
                result[key] = value
            return result
        def invalid_constant(value):
            raise ValueError(f"Invalid JSON constant: {value}")
        data = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
    if not isinstance(data, dict):
        raise ValueError("Config must be an object/table")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an object/table")
    for event in EVENTS:
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"hooks.{event} must be an array")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError(f"Invalid matcher group for {event}")
            if any(not isinstance(hook, dict) for hook in group["hooks"]):
                raise ValueError(f"Invalid handler for {event}")
    return data


def encode(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def toml_block(event, group):
    lines = [f"# BEGIN {OWNER} {event}", f"[[hooks.{event}]]",
             f"[[hooks.{event}.hooks]]"]
    for key, value in group["hooks"][0].items():
        lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    lines.append(f"# END {OWNER} {event}")
    return "\n" + "\n".join(lines) + "\n"


def manifest_path(target):
    return target.with_name(target.name + ".megaskill-manifest.json")


def load_manifest(path, target):
    raw = read_bytes(path)
    if raw is None:
        return None, None
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get("owner") != OWNER
            or data.get("target") != str(target)
            or not isinstance(data.get("entries"), dict)
            or not isinstance(data.get("created_hooks"), bool)):
        raise ValueError("Invalid ownership manifest")
    if "original" not in data or "original_sha256" not in data:
        raise ValueError("Missing recovery backup")
    original = data["original"]
    if original is not None:
        if not isinstance(original, str):
            raise ValueError("Invalid recovery backup")
        original = base64.b64decode(original, validate=True)
    if data.get("original_sha256") != digest(original):
        raise ValueError("Backup checksum mismatch")
    parse(original, target.suffix.lower() == ".toml")
    for event, record in data["entries"].items():
        if (event not in EVENTS or not isinstance(record, dict)
                or not isinstance(record.get("created_event"), bool)):
            raise ValueError("Invalid owned event")
        group = record.get("group")
        if (not isinstance(group, dict) or set(group) != {"hooks"}
                or not isinstance(group["hooks"], list) or len(group["hooks"]) != 1
                or not isinstance(group["hooks"][0], dict)
                or group["hooks"][0].get("statusMessage") != f"Megaskill {event}"):
            raise ValueError("Invalid owned definition")
        if target.suffix.lower() == ".toml" and record.get("block") != toml_block(event, group):
            raise ValueError("Invalid owned TOML block")
    return data, raw


def digest(raw):
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def atomic_write(path, raw):
    """Replace atomically, retaining permissions of an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def replace_if_unchanged(path, before, after):
    if read_bytes(path) != before:
        raise ValueError(f"Concurrent change detected: {path}")
    if after is None:
        if before is not None:
            path.unlink()
    else:
        atomic_write(path, after)


def transaction(target, before, after, sidecar, manifest_before, manifest_after):
    """Persist recovery/ownership first, then config; rollback ordinary failures."""
    if before == after and manifest_before == manifest_after:
        return
    replace_if_unchanged(sidecar, manifest_before, manifest_after)
    try:
        if before != after:
            replace_if_unchanged(target, before, after)
    except Exception:
        # Do not overwrite an external writer, even during rollback.
        if read_bytes(target) == after and after != before:
            replace_if_unchanged(target, after, before)
        replace_if_unchanged(sidecar, manifest_after, manifest_before)
        raise


def inspect(target, uninstall=False, apply=False, status=False):
    target = Path(os.path.abspath(Path(target).expanduser()))
    toml = target.suffix.lower() == ".toml"
    if target.suffix.lower() not in {".json", ".toml"}:
        raise ValueError("Target must be a .json or .toml config")
    raw = read_bytes(target)
    config = parse(raw, toml)
    sidecar = manifest_path(target)
    manifest, manifest_raw = load_manifest(sidecar, target)
    wanted = definitions()
    hooks = config.get("hooks", {})
    installed = [event for event, group in wanted.items() if group in hooks.get(event, [])]
    report = {"target": str(target), "installed": len(installed) == len(EVENTS),
              "installed_events": installed, "trusted": "unknown",
              "manifest": str(sidecar), "action": "status" if status else
              ("uninstall" if uninstall else "install"), "dry_run": not apply}
    if status:
        report["definitions"] = wanted
        report["trust_review"] = "Review and trust exact definitions through native /hooks after install."
        return report
    original = (base64.b64decode(manifest["original"]) if manifest and
                manifest["original"] is not None else None)
    if manifest is None:
        original = raw
        manifest = {"owner": OWNER, "target": str(target), "entries": {},
                    "created_hooks": "hooks" not in config,
                    "original": base64.b64encode(raw).decode("ascii") if raw is not None else None,
                    "original_sha256": digest(raw)}
    updated = copy.deepcopy(config)
    text = raw.decode("utf-8") if raw is not None else ""
    changed, preserved = [], []
    if uninstall:
        for event, record in list(manifest["entries"].items()):
            groups = updated.get("hooks", {}).get(event, [])
            group = record["group"]
            block = record.get("block", "")
            if group in groups and (not toml or block in text):
                groups.remove(group)  # One exact owned occurrence, never same-label matches.
                if toml:
                    text = text.replace(block, "", 1)
                if not groups and record["created_event"]:
                    del updated["hooks"][event]
                changed.append(event)
            elif any(h.get("statusMessage") == f"Megaskill {event}"
                     for g in groups for h in g["hooks"]):
                preserved.append(event)
                continue
            del manifest["entries"][event]
        if not updated.get("hooks") and manifest["created_hooks"]:
            updated.pop("hooks", None)
        after = text.encode("utf-8") if toml else encode(updated)
        # Only restore original bytes when the merged result has no later edits.
        if (toml and after == (original or b"")) or (not toml and updated == parse(original, toml)):
            after = original
        if not changed:
            after = raw
    else:
        if not manifest["entries"]:
            manifest["created_hooks"] = "hooks" not in config
        for event, group in wanted.items():
            created_event = event not in updated.get("hooks", {})
            groups = updated.setdefault("hooks", {}).setdefault(event, [])
            record = manifest["entries"].get(event)
            if record and (record["group"] != group or record["group"] not in groups):
                raise ValueError(f"Owned {event} changed; uninstall before reinstalling")
            collisions = [h for g in groups for h in g["hooks"]
                          if h.get("statusMessage") == f"Megaskill {event}"]
            if group in groups:
                continue  # Preexisting exact definitions are not adopted.
            if collisions:
                raise ValueError(f"Conflicting Megaskill {event} definition")
            groups.append(group)
            record = {"group": group, "created_event": created_event}
            if toml:
                block = toml_block(event, group)
                record["block"] = block
                text += block
            manifest["entries"][event] = record
            changed.append(event)
        after = (text.encode("utf-8") if toml else encode(updated)) if changed else raw
    parse(after, toml)  # TOML append may conflict with a preexisting inline table.
    report.update(changed_events=changed, preserved_modified_events=preserved)
    if apply and (changed or manifest_raw is not None):
        transaction(target, raw, after, sidecar, manifest_raw, encode(manifest))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="After install, review and trust exact definitions through native /hooks. "
               "This installer never changes trusted hashes or config trust settings.")
    parser.add_argument("--target", default="~/.codex/hooks.json", help="JSON or TOML hook config")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--uninstall", action="store_true", help="Remove exact owned definitions")
    mode.add_argument("--status", action="store_true",
                      help="Show definitions and installed state; trust is unknown")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Explicit preview; do not write")
    args = parser.parse_args(argv)
    if args.apply and (args.dry_run or args.status):
        parser.error("--apply cannot be combined with --dry-run or --status")
    try:
        result = inspect(args.target, args.uninstall, args.apply, args.status)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"megaskill hooks: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
