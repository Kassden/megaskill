#!/usr/bin/env python3
"""Generate a self-contained Megaskill plan dashboard."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_STATE = Path(".mega/state.jsonl")
DEFAULT_EVIDENCE = Path(".mega/evidence.jsonl")


@dataclass
class Section:
    heading: str
    body: str


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def split_sections(text: str) -> list[Section]:
    matches = list(re.finditer(r"^(#{2,3})\s+(.+)$", text, re.MULTILINE))
    sections: list[Section] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append(Section(match.group(0), text[start:end].strip()))
    return sections


def title(text: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "Megaskill Plan"


def section_body(sections: list[Section], heading: str) -> str:
    for section in sections:
        if section.heading == heading:
            return section.body
    return ""


def field_value(body: str, label: str) -> str:
    pattern = rf"^\s*-\s+{re.escape(label)}:\s*(.+)$"
    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def phase_sections(sections: list[Section]) -> list[tuple[str, list[Section]]]:
    phases: list[tuple[str, list[Section]]] = []
    current: tuple[str, list[Section]] | None = None
    for section in sections:
        if section.heading.startswith("## Phase "):
            current = (section.heading.replace("## ", ""), [])
            phases.append(current)
        elif section.heading.startswith("### Subphase ") and current is not None:
            current[1].append(section)
    return phases


def read_jsonl(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    if not path.exists():
        return [], []
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: {exc.msg}")
            continue
        if isinstance(record, dict):
            records.append(record)
        else:
            errors.append(f"line {line_no}: record is not an object")
    return records, errors


def block(text: str) -> str:
    if not text:
        return "<p class=\"muted\">No canonical content recorded.</p>"
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    items = [line for line in lines if line.lstrip().startswith(("- ", "- [", "  - "))]
    if items and len(items) == len(lines):
        rendered_items = []
        for item in items:
            cleaned = item.lstrip()
            if cleaned.startswith("- [") and "] " in cleaned:
                cleaned = "- " + cleaned.split("] ", 1)[1]
            if cleaned.startswith("- "):
                cleaned = cleaned[2:]
            rendered_items.append(f"<li>{html.escape(cleaned)}</li>")
        rendered = "".join(rendered_items)
        return f"<ul>{rendered}</ul>"
    return "".join(f"<p>{html.escape(line)}</p>" for line in lines)


def status_for(records: list[dict[str, object]], phase: str, subphase: str = "") -> str:
    candidates = [
        str(record.get("status", ""))
        for record in records
        if str(record.get("phase", "")) in phase and (not subphase or str(record.get("subphase", "")) in subphase)
    ]
    for status in ["failed", "blocked", "active", "done", "archived", "planned"]:
        if status in candidates:
            return status
    return "planned"


def card(label: str, value: str) -> str:
    return f"<div class=\"card\"><strong>{html.escape(label)}</strong><span>{html.escape(value or 'Not recorded')}</span></div>"


def render_dashboard(plan_path: Path, state_path: Path, evidence_path: Path, generated_at: str | None = None) -> str:
    text = plan_path.read_text(encoding="utf-8")
    sections = split_sections(text)
    plan_title = title(text)
    state_records, state_errors = read_jsonl(state_path)
    evidence_records, evidence_errors = read_jsonl(evidence_path)
    regression = section_body(sections, "## Regression Guardrails")
    damage = field_value(regression, "Damage radius")
    branch = field_value(regression, "Branch strategy")
    proof = field_value(regression, "Proof plan")
    generated = generated_at or now()

    phase_html: list[str] = []
    for phase, subphases in phase_sections(sections):
        phase_status = status_for(state_records, phase)
        sub_html = []
        for subphase in subphases:
            body = subphase.body
            sub_status = status_for(state_records, phase, subphase.heading.replace("### ", ""))
            sub_html.append(
                "<div class=\"subphase\">"
                f"<h4>{html.escape(subphase.heading.replace('### ', ''))} <span class=\"pill {html.escape(sub_status)}\">{html.escape(sub_status)}</span></h4>"
                f"<p><strong>Commit:</strong> {html.escape(field_value(body, 'Commit'))}</p>"
                f"<p><strong>Tests:</strong> {html.escape(field_value(body, 'Tests'))}</p>"
                f"<p><strong>Success:</strong> {html.escape(field_value(body, 'Success Criteria'))}</p>"
                "</div>"
            )
        phase_html.append(
            f"<article class=\"phase {html.escape(phase_status)}\"><h3>{html.escape(phase)} "
            f"<span class=\"pill {html.escape(phase_status)}\">{html.escape(phase_status)}</span></h3>"
            + "".join(sub_html)
            + "</article>"
        )

    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(record.get('timestamp', '')))}</td>"
        f"<td>{html.escape(str(record.get('phase', '')))}</td>"
        f"<td>{html.escape(str(record.get('command', '')))}</td>"
        f"<td>{html.escape(str(record.get('exit_code', '')))}</td>"
        f"<td>{html.escape(str(record.get('state_event_id', '')))}</td>"
        "</tr>"
        for record in evidence_records[-25:]
    ) or "<tr><td colspan=\"5\" class=\"muted\">No evidence records yet.</td></tr>"
    state_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(record.get('timestamp', '')))}</td>"
        f"<td>{html.escape(str(record.get('phase', '')))}</td>"
        f"<td>{html.escape(str(record.get('subphase', '')))}</td>"
        f"<td>{html.escape(str(record.get('kind', '')))}</td>"
        f"<td>{html.escape(str(record.get('status', '')))}</td>"
        f"<td>{html.escape(str(record.get('summary', '')))}</td>"
        "</tr>"
        for record in state_records[-50:]
    ) or "<tr><td colspan=\"6\" class=\"muted\">No ordered state records yet.</td></tr>"
    no_go = state_errors + evidence_errors + [
        str(record.get("summary", ""))
        for record in state_records
        if str(record.get("status", "")) in {"failed", "blocked"}
    ] + [
        str(record.get("note", ""))
        for record in evidence_records
        if int(record.get("exit_code", 0)) != 0
    ]
    no_go_html = "".join(f"<li>{html.escape(item)}</li>" for item in no_go if item) or "<li>No failed or blocked records in the loaded ledgers.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(plan_title)} Dashboard</title>
  <style>
    :root {{ color-scheme: light; --ink: #182126; --muted: #5b666d; --line: #c9d0cc; --paper: #f7f8f5; --panel: #fff; --accent: #1f6f78; --warn: #9a5d00; --danger: #9f2e24; --ok: #1d6b45; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.45; }}
    header {{ padding: 28px 36px 18px; border-bottom: 1px solid var(--line); background: #eef2ee; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 16px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 10px; font-size: 16px; letter-spacing: 0; }}
    h4 {{ margin: 0 0 8px; font-size: 14px; letter-spacing: 0; }}
    p, li, td, th, span {{ font-size: 14px; }}
    code {{ background: #edf0ed; padding: 1px 4px; border-radius: 4px; }}
    main {{ display: grid; grid-template-columns: minmax(240px, 340px) minmax(0, 1fr); min-height: calc(100vh - 104px); }}
    nav {{ padding: 24px; border-right: 1px solid var(--line); background: #f1f4f1; position: sticky; top: 0; height: 100vh; overflow: auto; }}
    nav a {{ display: block; color: var(--accent); text-decoration: none; margin: 0 0 10px; font-size: 14px; font-weight: 600; }}
    section {{ padding: 28px 36px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    section:nth-child(even) {{ background: #fbfcfa; }}
    .subtitle, .muted {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fff; }}
    .card strong {{ display: block; margin-bottom: 4px; font-size: 13px; }}
    .card span {{ color: var(--muted); overflow-wrap: anywhere; }}
    .phase {{ border-left: 4px solid var(--accent); padding: 12px 14px; margin: 12px 0; background: #f3f8f8; border-radius: 0 8px 8px 0; }}
    .phase.failed, .phase.blocked {{ border-left-color: var(--danger); background: #fff4f2; }}
    .phase.active {{ border-left-color: var(--warn); background: #fff8e9; }}
    .phase.done {{ border-left-color: var(--ok); background: #f1faf4; }}
    .subphase {{ border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; }}
    .pill {{ display: inline-block; margin-left: 8px; padding: 1px 6px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); font-size: 12px; }}
    .pill.done {{ color: var(--ok); border-color: var(--ok); }}
    .pill.active, .pill.blocked {{ color: var(--warn); border-color: var(--warn); }}
    .pill.failed {{ color: var(--danger); border-color: var(--danger); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2ee; }}
    @media (max-width: 900px) {{ main {{ display: block; }} nav {{ position: relative; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }} section {{ padding: 24px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(plan_title)}</h1>
    <p class="subtitle">Generated Megaskill dashboard. Canonical inputs are the plan, ordered state ledger, and verification evidence ledger.</p>
  </header>
  <main>
    <nav>
      <a href="#truth">Current Source Of Truth</a>
      <a href="#objective">Objective</a>
      <a href="#acceptance">Acceptance</a>
      <a href="#regression">Regression Radius</a>
      <a href="#proof">Proof Surfaces</a>
      <a href="#phases">Phases</a>
      <a href="#state">Ordered State</a>
      <a href="#evidence">Evidence</a>
      <a href="#gates">Go / No-Go Gates</a>
      <a href="#archive">Archive</a>
    </nav>
    <div>
      <section id="truth"><h2>Current Source Of Truth</h2><div class="grid">
        {card("Plan", str(plan_path))}
        {card("State ledger", str(state_path))}
        {card("Evidence ledger", str(evidence_path))}
        {card("Generated", generated)}
        {card("Damage radius", damage)}
        {card("Branch strategy", branch)}
      </div></section>
      <section id="objective"><h2>Objective</h2>{block(section_body(sections, "## GOAL"))}</section>
      <section id="acceptance"><h2>Acceptance</h2>{block(section_body(sections, "## Acceptance Criteria"))}</section>
      <section id="regression"><h2>Regression Radius</h2>{block(regression)}<p><strong>Proof plan:</strong> {html.escape(proof or "Not recorded")}</p></section>
      <section id="proof"><h2>Proof Surfaces</h2><h3>Deterministic Real-User Test</h3>{block(section_body(sections, "## Deterministic Real-User Test"))}<h3>Fulfillment And Readback</h3>{block(section_body(sections, "## Fulfillment and Readback Proof"))}<h3>Armageddon Mode</h3>{block(section_body(sections, "## Armageddon Mode"))}<h3>Generality Guardrail</h3>{block(section_body(sections, "## Generality Guardrail"))}</section>
      <section id="phases"><h2>Phases</h2>{"".join(phase_html) or '<p class="muted">No phases found.</p>'}</section>
      <section id="state"><h2>Ordered State</h2><table><tr><th>Time</th><th>Phase</th><th>Subphase</th><th>Kind</th><th>Status</th><th>Summary</th></tr>{state_rows}</table></section>
      <section id="evidence"><h2>Evidence</h2><table><tr><th>Time</th><th>Phase</th><th>Command</th><th>Exit</th><th>State Event</th></tr>{evidence_rows}</table></section>
      <section id="gates"><h2>Go / No-Go Gates</h2><ul>{no_go_html}</ul></section>
      <section id="archive"><h2>Archive</h2><p>Archived or superseded phases remain evidence only. The canonical plan and ledgers above own current execution state.</p></section>
    </div>
  </main>
</body>
</html>
"""


def should_open(args: argparse.Namespace) -> bool:
    if args.no_open:
        return False
    if args.open:
        return True
    return bool(args.interactive and not os.environ.get("CI"))


def write_dashboard(args: argparse.Namespace) -> Path:
    plan_path = Path(args.plan)
    output = Path(args.output) if args.output else Path(".mega/dashboards") / f"{plan_path.stem}.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_dashboard(plan_path, Path(args.state), Path(args.evidence), args.generated_at),
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="canonical Megaskill markdown plan")
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--output", "-o")
    parser.add_argument("--open", action="store_true", help="open the generated dashboard")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument("--interactive", action="store_true", help="open by default when not in CI")
    parser.add_argument("--generated-at", help="fixed timestamp for deterministic tests")
    args = parser.parse_args()

    output = write_dashboard(args)
    print(f"generated dashboard: {output}")
    if should_open(args):
        webbrowser.open(output.resolve().as_uri())
        print(f"opened dashboard: {output.resolve().as_uri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
