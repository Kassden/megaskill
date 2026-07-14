#!/usr/bin/env python3
"""Create a canonical Mega Skill execution plan skeleton."""

from __future__ import annotations

import argparse
from pathlib import Path


def phase_names(raw: str | None) -> list[str]:
    if not raw:
        return ["Discovery", "Implementation", "Verification"]
    names = [part.strip() for part in raw.split(",") if part.strip()]
    return names or ["Discovery", "Implementation", "Verification"]


def render(title: str, goal: str, phases: list[str]) -> str:
    lines: list[str] = [
        f"# {title}",
        "",
        "## GOAL",
        f"- {goal}",
        "",
        "## Acceptance Criteria",
        "- [ ] <measurable proof of success>",
        "",
        "## Research",
        "- Built-in options: <inspect first>",
        "- Off-the-shelf options: <inspect if relevant>",
        "- Official / standards sources: <cite when relevant>",
        "",
        "## Regression Guardrails",
        "- Planned edit surface: <files, modules, routes, configs, or systems>",
        "- Protected behaviors: <behavior that must remain unchanged>",
        "- Likely consumers: <callers, users, jobs, deploy/runtime surfaces>",
        "- Damage radius: <small | moderate | large | systemic>",
        "- Proof plan: <checks that prove the goal and protect adjacent behavior>",
        "",
    ]
    for idx, name in enumerate(phases, start=1):
        lines.extend(
            [
                f"## Phase {idx}: {name}",
                "",
                f"### Subphase {idx}.1: <subphase name>",
                f"- Commit: <single commit intent for Phase {idx}.1>",
                "- Tests: <specific tests/checks for this subphase>",
                "- Success Criteria: <what proves this subphase advances the GOAL>",
                "- Planned Touch Files:",
                "  - `<path>`",
                "- Checklist:",
                "  - [ ] <work item>",
                "  - [ ] <verification item>",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="plan title")
    parser.add_argument("--goal", required=True, help="measurable goal")
    parser.add_argument(
        "--phases",
        help="comma-separated phase names, default: Discovery,Implementation,Verification",
    )
    parser.add_argument("--output", "-o", help="write plan to this path")
    args = parser.parse_args()

    content = render(args.title, args.goal, phase_names(args.phases))
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
