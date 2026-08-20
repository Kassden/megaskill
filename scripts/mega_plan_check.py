#!/usr/bin/env python3
"""Validate a Megaskill markdown plan."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PHASE_RE = re.compile(r"^## Phase\s+\d+:", re.MULTILINE)
SUBPHASE_RE = re.compile(r"^### Subphase\s+\d+(?:\.\d+)+:", re.MULTILINE)
UI_RE = re.compile(
    r"\b(ui|frontend|browser|visual|layout|responsive|screenshot|canvas|3d|game|landing page)\b",
    re.IGNORECASE,
)
BROWSER_PROOF_RE = re.compile(
    r"\b(playwright|browser smoke|screenshot|visual|pixel|canvas|accessibility|axe)\b",
    re.IGNORECASE,
)
TOOLING_INSTALL_RE = re.compile(
    r"\b(npm install|npm i|pnpm add|yarn add|bun add|pip install|uv add|cargo add|playwright install|install or repair|no install is needed)\b",
    re.IGNORECASE,
)
REAL_BLOCKER_RE = re.compile(
    r"\b(approval|credential|auth|incompatible platform|external outage|destructive|product decision|registry outage|real blocker)\b",
    re.IGNORECASE,
)
LOOPHOLE_RE = re.compile(
    r"\b(only if already available|if already available|otherwise use|skip(?:ped)? because .*not installed|not installed.*skip)\b",
    re.IGNORECASE,
)
USER_SURFACE_RE = re.compile(
    r"\b(interface|app|cli|tool|workflow|user-facing|user facing|browser|ui|frontend|api|agent surface)\b",
    re.IGNORECASE,
)
DETERMINISTIC_RE = re.compile(
    r"\b(entry point|user workflow|stable inputs|fixtures|user-observable|observable assertions|command)\b",
    re.IGNORECASE,
)
ARMAGEDDON_RE = re.compile(
    r"\b(edge cases|failure modes|attack scope|must-fix|must fix|optimization opportunities|adversarial)\b",
    re.IGNORECASE,
)
GENERALITY_RE = re.compile(
    r"\b(existing mechanism|general mechanism|similar existing|recurrence|one-off justification|specific use case)\b",
    re.IGNORECASE,
)
SOTA_RE = re.compile(
    r"\b(sota|state of the art|prior art|official|standards?|specs?|platform guidance|best practices?|mature librar(?:y|ies)|frameworks?|built-?in|rejected approaches?|implementation decision)\b",
    re.IGNORECASE,
)
FULFILLMENT_RE = re.compile(
    r"\b(final user-visible result|user-visible result|artifact|record|deployment|external state|required write|mutation operation|readback surface|expected content|rows|fields|counts|behavior|tool call evidence|not-done conditions|not done conditions)\b",
    re.IGNORECASE,
)
HAPPY_PATH_ONLY_RE = re.compile(
    r"\b(happy path only|only happy path|manual inspection only|no edge cases|skip armageddon)\b",
    re.IGNORECASE,
)
BESPOKE_WITHOUT_GENERALITY_RE = re.compile(
    r"\b(one-off|bespoke|specific to this one case|hard-?coded to this example)\b",
    re.IGNORECASE,
)
CREATION_ONLY_RE = re.compile(
    r"\b(created? (?:the |a |new )?(?:file|sheet|doc(?:ument)?|artifact|record|folder)|cop(?:y|ied) (?:the |a )?(?:template|file|sheet|doc(?:ument)?|artifact)|converted (?:the |a )?(?:template|file|sheet|doc(?:ument)?|artifact)|rout(?:e|ed) to (?:the )?(?:right|correct) tool)\b",
    re.IGNORECASE,
)
WRITE_MUTATION_RE = re.compile(
    r"\b(write|wrote|update|updated|mutation|mutate|populate|insert|upsert|import|export|deploy|sync|index|send)\b",
    re.IGNORECASE,
)
READBACK_ASSERTION_RE = re.compile(
    r"\b(readback|read back|export|compare|assert|verify|verified|expected content|rows?|fields?|counts?|totals?|behavior|side effect|side-effect)\b",
    re.IGNORECASE,
)
CONTENT_ASSERTION_RE = re.compile(
    r"\b(content|rows?|fields?|counts?|totals?|values?|formulas?|status|metadata|behavior|clauses?|tables?|assertions?)\b",
    re.IGNORECASE,
)
HIGH_RISK_RADIUS_RE = re.compile(r"\b(large|systemic)\b", re.IGNORECASE)
BRANCH_STRATEGY_RE = re.compile(
    r"\b(branch|feature branch|dedicated branch|risk branch|isolation branch|separate branch|worktree)\b",
    re.IGNORECASE,
)
NO_BRANCH_RE = re.compile(
    r"\b(no branch|current branch|main directly|trunk directly|same branch)\b",
    re.IGNORECASE,
)


@dataclass
class Section:
    heading: str
    body: str


def split_sections(text: str) -> list[Section]:
    matches = list(re.finditer(r"^(#{2,3})\s+(.+)$", text, re.MULTILINE))
    sections: list[Section] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append(Section(match.group(0), text[start:end]))
    return sections


def has_checklist(body: str) -> bool:
    return bool(re.search(r"^\s*-\s+\[[ xX]\]\s+\S", body, re.MULTILINE))


def field_value(body: str, label: str) -> str:
    pattern = rf"^\s*-\s+{re.escape(label)}:\s*(.+)$"
    match = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def validate(text: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r"^#\s+\S", text, re.MULTILINE):
        errors.append("missing top-level title (# Title)")
    for required in [
        "## GOAL",
        "## Research",
        "## SOTA, Standards, And Best Practices",
        "## Dependency and Tooling Preflight",
        "## Deterministic Real-User Test",
        "## Fulfillment and Readback Proof",
        "## Armageddon Mode",
        "## Generality Guardrail",
    ]:
        if required not in text:
            errors.append(f"missing required section: {required}")
    phases = list(PHASE_RE.finditer(text))
    subphases = list(SUBPHASE_RE.finditer(text))
    if not phases:
        errors.append("missing at least one '## Phase N:' section")
    if not subphases:
        errors.append("missing at least one '### Subphase N.N:' section")

    for idx, phase in enumerate(phases):
        end = phases[idx + 1].start() if idx + 1 < len(phases) else len(text)
        body = text[phase.end() : end]
        if not SUBPHASE_RE.search(body):
            errors.append(f"{phase.group(0)} has no subphase")

    for section in split_sections(text):
        if not section.heading.startswith("### Subphase "):
            continue
        body = section.body
        for field in ["- Commit:", "- Tests:", "- Success Criteria:"]:
            if field not in body:
                errors.append(f"{section.heading} missing {field}")
        if "- Checklist:" not in body:
            errors.append(f"{section.heading} missing - Checklist:")
        elif not has_checklist(body):
            errors.append(f"{section.heading} has no checklist items")

    tooling_section = ""
    sota_section = ""
    deterministic_section = ""
    fulfillment_section = ""
    armageddon_section = ""
    generality_section = ""
    regression_section = ""
    sections = split_sections(text)
    for section in sections:
        if section.heading == "## Dependency and Tooling Preflight":
            tooling_section = section.body
        elif section.heading == "## SOTA, Standards, And Best Practices":
            sota_section = section.body
        elif section.heading == "## Deterministic Real-User Test":
            deterministic_section = section.body
        elif section.heading == "## Fulfillment and Readback Proof":
            fulfillment_section = section.body
        elif section.heading == "## Armageddon Mode":
            armageddon_section = section.body
        elif section.heading == "## Generality Guardrail":
            generality_section = section.body
        elif section.heading == "## Regression Guardrails":
            regression_section = section.body
    if sota_section and not SOTA_RE.search(sota_section):
        errors.append("## SOTA, Standards, And Best Practices must document prior art, official docs/standards, mature libraries, best practices, rejected approaches, or implementation decision")
    if tooling_section:
        if not TOOLING_INSTALL_RE.search(tooling_section) and not REAL_BLOCKER_RE.search(tooling_section):
            errors.append("## Dependency and Tooling Preflight must name install/repair commands, no-install rationale, or real blockers")
        if UI_RE.search(text) and not BROWSER_PROOF_RE.search(tooling_section):
            errors.append("UI/browser-facing plan must name browser smoke, Playwright, screenshot, visual, pixel, canvas, or accessibility proof")
    if deterministic_section:
        if USER_SURFACE_RE.search(text) and not DETERMINISTIC_RE.search(deterministic_section):
            errors.append("## Deterministic Real-User Test must name entry point, workflow, stable inputs/fixtures, observable assertions, or command")
    if fulfillment_section and not FULFILLMENT_RE.search(fulfillment_section):
        errors.append("## Fulfillment and Readback Proof must name final result, required write/mutation, readback surface, expected content/counts/behavior, evidence, or not-done conditions")
    if armageddon_section and not ARMAGEDDON_RE.search(armageddon_section):
        errors.append("## Armageddon Mode must name edge cases, failure modes, attack scope, optimization opportunities, or must-fix threshold")
    if generality_section and not GENERALITY_RE.search(generality_section):
        errors.append("## Generality Guardrail must document existing mechanism, recurrence, general mechanism decision, or one-off justification")
    if regression_section:
        branch_strategy = field_value(regression_section, "Branch strategy")
        damage_radius = field_value(regression_section, "Damage radius")
        if not branch_strategy:
            errors.append("## Regression Guardrails must include Branch strategy")
        elif "<" not in damage_radius and HIGH_RISK_RADIUS_RE.search(damage_radius):
            if NO_BRANCH_RE.search(branch_strategy) or not BRANCH_STRATEGY_RE.search(branch_strategy):
                errors.append("large/systemic regression risk must use a separate branch or explicitly named isolation branch strategy")
    if LOOPHOLE_RE.search(text):
        errors.append("plan contains verification loophole language such as 'only if already available' or skip-on-missing-tooling")
    if HAPPY_PATH_ONLY_RE.search(text):
        errors.append("plan contains weak verification language such as happy-path-only, manual-inspection-only, or skipped Armageddon checks")
    if BESPOKE_WITHOUT_GENERALITY_RE.search(text) and not generality_section:
        errors.append("plan mentions bespoke/one-off behavior but lacks ## Generality Guardrail")
    if CREATION_ONLY_RE.search(text) and fulfillment_section:
        write_value = field_value(fulfillment_section, "Required write/mutation operation")
        readback_value = field_value(fulfillment_section, "Readback surface")
        expected_value = field_value(fulfillment_section, "Expected content, rows, fields, counts, or behavior")
        if (
            not WRITE_MUTATION_RE.search(write_value)
            or not READBACK_ASSERTION_RE.search(readback_value)
            or not CONTENT_ASSERTION_RE.search(expected_value)
        ):
            errors.append("plan mentions creation/copy/routing but ## Fulfillment and Readback Proof lacks write/mutation plus readback/content assertions")
    elif CREATION_ONLY_RE.search(text) and not fulfillment_section:
        errors.append(
            "plan mentions creation/copy/routing but ## Fulfillment and Readback Proof lacks write/mutation plus readback/content assertions"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", help="path to markdown plan")
    args = parser.parse_args()

    text = Path(args.plan).read_text(encoding="utf-8")
    errors = validate(text)
    if errors:
        print("Mega plan check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Mega plan check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
