#!/usr/bin/env python3
"""Validate a Megaskill markdown plan."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PHASE_RE = re.compile(r"^## Phase\s+\d+:", re.MULTILINE)
SUBPHASE_RE = re.compile(r"^### Subphase\s+\d+(?:\.\d+)+:", re.MULTILINE)


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


def validate(text: str) -> list[str]:
    errors: list[str] = []
    if not re.search(r"^#\s+\S", text, re.MULTILINE):
        errors.append("missing top-level title (# Title)")
    for required in ["## GOAL", "## Research"]:
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
