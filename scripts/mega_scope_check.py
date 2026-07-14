#!/usr/bin/env python3
"""Compare planned touch files with current git changes."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


TOUCH_HEADINGS = {
    "planned touch files",
    "planned edit surface",
    "planned files",
    "edit surface",
}


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "not a git repository")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_changed_files(staged: bool) -> list[str]:
    diff_args = ["diff", "--name-only", "--diff-filter=ACMR"]
    if staged:
        diff_args.insert(1, "--cached")
        return run_git(diff_args)
    changed = run_git(diff_args)
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    return changed + untracked


def normalize(path: str) -> str:
    return path.strip().strip("`").strip("./")


def looks_like_path(value: str) -> bool:
    if not value or value.startswith("[") or value.endswith(":"):
        return False
    if any(token in value for token in ("<", ">", " ")):
        return False
    return "/" in value or "." in value


def parse_planned(plan: Path) -> set[str]:
    text = plan.read_text(encoding="utf-8")
    planned: set[str] = set()
    active = False
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower().rstrip(":")
        if stripped.startswith("#"):
            active = False
        if lower.lstrip("- ").rstrip(":") in TOUCH_HEADINGS:
            active = True
            candidate = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            if candidate and "<" not in candidate:
                for part in re.split(r"[, ]+", candidate):
                    if looks_like_path(normalize(part)):
                        planned.add(normalize(part))
            continue
        if active and stripped.startswith("- "):
            candidate = normalize(stripped[2:].strip())
            if looks_like_path(candidate):
                planned.add(candidate)
            continue
        if active and stripped == "":
            continue
        if active and not stripped.startswith((" ", "-")):
            active = False
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="path to markdown plan")
    parser.add_argument("--planned", action="append", default=[], help="additional planned file")
    parser.add_argument("--staged", action="store_true", help="check staged diff instead of working diff")
    parser.add_argument("--allow-unplanned", action="store_true", help="report but do not fail on unplanned files")
    args = parser.parse_args()

    planned = parse_planned(Path(args.plan)) | {normalize(p) for p in args.planned}
    changed = {normalize(p) for p in git_changed_files(args.staged)}
    unplanned = sorted(changed - planned) if planned else sorted(changed)
    untouched_planned = sorted(planned - changed)

    print("Mega scope check")
    print(f"- planned files: {len(planned)}")
    print(f"- changed files: {len(changed)}")
    if planned:
        print("- unplanned changed files:")
        for path in unplanned or ["<none>"]:
            print(f"  - {path}")
        print("- planned files not changed:")
        for path in untouched_planned or ["<none>"]:
            print(f"  - {path}")
    else:
        print("- no planned files found in plan or --planned args")
        for path in sorted(changed):
            print(f"  - {path}")

    if unplanned and not args.allow_unplanned:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
