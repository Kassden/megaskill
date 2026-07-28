#!/usr/bin/env python3
"""Check whether the staged diff looks like one atomic commit."""

from __future__ import annotations

import argparse
import subprocess
from collections import defaultdict
from pathlib import Path


DOC_EXT = {".md", ".mdx", ".rst", ".txt"}
ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf"}
CONFIG_NAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "next.config.js",
    "next.config.ts",
    "Dockerfile",
    "docker-compose.yml",
}
GENERATED_HINTS = {"lock", "dist", "build", "generated", ".snap"}


def in_git_repo() -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git command failed")
    return result.stdout


def staged_files() -> list[str]:
    out = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [line.strip() for line in out.splitlines() if line.strip()]


def category(path: str) -> str:
    p = Path(path)
    name = p.name
    suffix = p.suffix.lower()
    lowered = path.lower()
    if name in CONFIG_NAMES or path.startswith((".github/", ".vercel/", "infra/")):
        return "config"
    if "/test" in lowered or "test/" in lowered or ".test." in lowered or ".spec." in lowered:
        return "tests"
    if suffix in DOC_EXT or path.startswith("docs/"):
        return "docs"
    if suffix in ASSET_EXT or path.startswith(("public/", "assets/")):
        return "assets"
    return "code"


def generated(path: str) -> bool:
    lowered = path.lower()
    return any(hint in lowered for hint in GENERATED_HINTS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-top-levels", type=int, default=3)
    parser.add_argument("--allow-mixed", action="store_true")
    args = parser.parse_args()

    if not in_git_repo():
        print("Mega commit check unavailable: current directory is not inside a git repository.")
        print("Fallback evidence: list changed/generated artifacts, record hashes or file sizes, and attach render/readback checks with mega_evidence.py.")
        return 2

    files = staged_files()
    if not files:
        print("Mega commit check failed: no staged files.")
        return 1

    categories: dict[str, list[str]] = defaultdict(list)
    top_levels: dict[str, list[str]] = defaultdict(list)
    generated_files: list[str] = []
    for path in files:
        categories[category(path)].append(path)
        top_levels[path.split("/", 1)[0]].append(path)
        if generated(path):
            generated_files.append(path)

    failures: list[str] = []
    category_set = set(categories)
    allowed_sets = [
        {"code"},
        {"tests"},
        {"docs"},
        {"config"},
        {"assets"},
        {"code", "tests"},
        {"docs", "assets"},
        {"config", "tests"},
    ]
    if category_set not in allowed_sets and not args.allow_mixed:
        failures.append(f"mixed categories: {', '.join(sorted(category_set))}")
    if len(top_levels) > args.max_top_levels and not args.allow_mixed:
        failures.append(f"too many top-level areas: {', '.join(sorted(top_levels))}")
    if generated_files and len(files) != len(generated_files) and not args.allow_mixed:
        failures.append("generated-looking files mixed with hand edits")

    print("Mega commit check")
    print(f"- staged files: {len(files)}")
    print("- categories:")
    for cat, paths in sorted(categories.items()):
        print(f"  - {cat}: {len(paths)}")
    print("- top-level areas:")
    for top, paths in sorted(top_levels.items()):
        print(f"  - {top}: {len(paths)}")

    if failures:
        print("Mega commit check failed:")
        for failure in failures:
            print(f"- {failure}")
        print("Suggested split groups:")
        for cat, paths in sorted(categories.items()):
            print(f"- {cat}:")
            for path in paths:
                print(f"  - {path}")
        return 1

    print("Mega commit check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
