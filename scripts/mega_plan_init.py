#!/usr/bin/env python3
"""Create a canonical Megaskill execution plan skeleton."""

from __future__ import annotations

import argparse
import subprocess
import sys
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
        "## SOTA, Standards, And Best Practices",
        "- Current SOTA / prior art: <current best-known approaches for this capability>",
        "- Official docs, standards, specs, or platform guidance: <primary sources or local-doc fallback>",
        "- Mature libraries, frameworks, or built-in mechanisms: <prefer established mechanisms over hand-rolled logic>",
        "- Best-practice constraints to integrate: <security, accessibility, performance, reliability, API, or domain rules>",
        "- Rejected approaches: <options considered and why rejected>",
        "- Implementation decision: <design choice that follows from the research>",
        "",
        "## Dependency and Tooling Preflight",
        "- Required verification tools: <test runners, Playwright/browser smoke if UI/browser work is in scope, CLIs, renderers, or live probes>",
        "- Existing tooling found: <repo scripts and installed tools>",
        "- Install or repair commands: <project-local setup commands or no install is needed>",
        "- Browser/runtime binaries: <browser, runtime, device, or none>",
        "- Real blockers that would prevent setup: <approval, credentials, incompatible platform, external outage, destructive action, or product decision>",
        "",
        "## Deterministic Real-User Test",
        "- Entry point: <user-facing route, command, workflow, artifact, or API/tool entry>",
        "- User workflow: <core workflow a real user performs>",
        "- Stable inputs or fixtures: <seeded data, recorded fixture, deterministic local state>",
        "- User-observable assertions: <visible output, stdout/stderr, response shape, artifact readback>",
        "- Command: <repeatable command or no user-facing surface in scope>",
        "- Evidence to record: <mega_evidence.py command note and artifacts>",
        "",
        "## Fulfillment and Readback Proof",
        "- Requested final user-visible result: <artifact, file, record, deployed behavior, external state, or none>",
        "- Required write/mutation operation: <exact write, update, import, export, deploy, sync, or no mutation needed>",
        "- Readback surface: <same user/downstream-visible surface when practical>",
        "- Expected content, rows, fields, counts, or behavior: <acceptance assertions>",
        "- Command or tool call evidence: <commands, tool calls, logs, exports, screenshots>",
        "- Not-done conditions: <created-only, copied-only, route-only, disabled write API, stale output, partial data>",
        "",
        "## Armageddon Mode",
        "- Damage-scaled attack scope: <small | moderate | large | systemic scope>",
        "- Edge cases to try: <empty, long, invalid, repeated, narrow, missing, failed dependency>",
        "- Failure modes to simulate: <bad input, auth, network, config, downstream, cwd, timeout>",
        "- Optimization opportunities to inspect: <duplication, slow paths, unnecessary queries, tool friction>",
        "- Must-fix threshold: <what blocks done>",
        "- Evidence to record: <commands, screenshots, logs, fixtures, output>",
        "",
        "## Generality Guardrail",
        "- Existing mechanism to reuse: <shared service/tool/helper/pattern or none found>",
        "- Similar existing use cases: <paths or examples>",
        "- Recurrence likelihood: <low | medium | high and why>",
        "- General mechanism to create if none exists: <shared mechanism or not needed>",
        "- Specific use case implementation through the mechanism: <how this request uses the mechanism>",
        "- One-off justification, if any: <why isolated, low-risk, unlikely to recur>",
        "",
        "## Regression Guardrails",
        "- Planned edit surface: <files, modules, routes, configs, or systems>",
        "- Protected behaviors: <behavior that must remain unchanged>",
        "- Likely consumers: <callers, users, jobs, deploy/runtime surfaces>",
        "- Damage radius: <small | moderate | large | systemic>",
        "- Branch strategy: <current branch acceptable for small/moderate with reason; dedicated branch required for large/systemic regression risk>",
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
    parser.add_argument(
        "--dashboard",
        nargs="?",
        const="",
        help="generate a dashboard HTML file, optionally at this path",
    )
    parser.add_argument("--open", action="store_true", help="open generated dashboard")
    parser.add_argument("--no-open", action="store_true", help="do not open generated dashboard")
    args = parser.parse_args()

    content = render(args.title, args.goal, phase_names(args.phases))
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(content, encoding="utf-8")
    else:
        output_path = None
        print(content, end="")
    if args.dashboard is not None:
        if output_path is None:
            print("mega_plan_init --dashboard requires --output so the dashboard has a canonical plan file")
            return 2
        dashboard_path = Path(args.dashboard) if args.dashboard else Path(".mega/dashboards") / f"{output_path.stem}.html"
        command = [
            sys.executable,
            str(Path(__file__).with_name("mega_plan_dashboard.py")),
            str(output_path),
            "--output",
            str(dashboard_path),
        ]
        if args.no_open:
            command.append("--no-open")
        elif args.open:
            command.append("--open")
        else:
            command.append("--interactive")
        result = subprocess.run(command)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
