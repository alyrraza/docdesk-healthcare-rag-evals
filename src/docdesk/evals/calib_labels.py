"""Read the filled calibration sheet, check it is complete, and turn it into labels.yaml (T099).

A partial sheet is refused with the full list of what is missing, so the owner fixes it in one pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from docdesk.evals.calib_sheet import KEY_VALUES, LABELS_HEADING, YES_NO

SECTION = re.compile(r"^## (\d+) of (\d+) \| (\S+)\s*$", re.MULTILINE)
KEY_LINE = re.compile(r"^key (\d+):[ \t]*(.*?)[ \t]*$")
CLAIMS_LINE = re.compile(r"^unsupported claims:[ \t]*(.*?)[ \t]*$")
CONTRADICTED_LINE = re.compile(r"^contradicted:[ \t]*(.*?)[ \t]*$")
BULLET = re.compile(r"^-[ \t]+(.+?)[ \t]*$")


class LabelError(ValueError):
    """The sheet cannot be applied; the message lists every problem found."""


@dataclass
class FilledOutput:
    """What the owner wrote for one output, as text, before any validation."""

    item_id: str
    keys: dict[int, str] = field(default_factory=dict)
    claims: list[str] = field(default_factory=list)
    has_claims_field: bool = False
    contradicted: str = ""


def parse_fields(body: str) -> FilledOutput:
    """Read the label lines of one section; bullets under the claims field belong to it."""
    filled = FilledOutput("")
    in_claims = False
    for line in body.splitlines():
        if match := KEY_LINE.match(line):
            filled.keys[int(match[1])], in_claims = match[2], False
        elif match := CLAIMS_LINE.match(line):
            filled.has_claims_field, in_claims = True, True
            if match[1]:
                filled.claims.append(match[1])
        elif match := CONTRADICTED_LINE.match(line):
            filled.contradicted, in_claims = match[1], False
        elif in_claims and (match := BULLET.match(line)):
            filled.claims.append(match[1])
    return filled


def parse_sheet(text: str) -> dict[int, FilledOutput]:
    """One FilledOutput per section of the sheet, by its number."""
    heads = list(SECTION.finditer(text))
    parsed: dict[int, FilledOutput] = {}
    for position, head in enumerate(heads):
        end = heads[position + 1].start() if position + 1 < len(heads) else len(text)
        section = text[head.end():end]
        _, _, labels = section.partition(LABELS_HEADING)
        filled = parse_fields(labels)
        filled.item_id = head[3]
        parsed[int(head[1])] = filled
    return parsed


def problems_of(number: int, entry: dict[str, Any], filled: FilledOutput | None) -> list[str]:
    """Everything wrong with one output: missing, blank or not an allowed value."""
    name = f"output {number} ({entry['item_id']})"
    if filled is None:
        return [f"{name}: not in the sheet"]
    found = []
    if filled.item_id != entry["item_id"]:
        found.append(f"{name}: the sheet shows {filled.item_id}")
    for key in range(1, entry["key_points"] + 1):
        value = filled.keys.get(key, "").lower()
        if not value:
            found.append(f"{name}: key {key} is blank")
        elif value not in KEY_VALUES:
            found.append(
                f"{name}: key {key} is '{filled.keys[key]}', allowed: {', '.join(KEY_VALUES)}")
    if not filled.claims:
        found.append(f"{name}: unsupported claims is blank (write none if there are none)")
    elif any(c.lower() == "none" for c in filled.claims) and len(filled.claims) > 1:
        found.append(f"{name}: unsupported claims says none and also lists claims")
    value = filled.contradicted.lower()
    if not value:
        found.append(f"{name}: contradicted is blank")
    elif value not in YES_NO:
        found.append(f"{name}: contradicted is '{filled.contradicted}', allowed: yes, no")
    return found


def apply_sheet(
    parsed: dict[int, FilledOutput], manifest: dict[str, Any], *, by: str, today: date
) -> dict[str, Any]:
    """Validate every output of the manifest against the sheet and build the labels document."""
    wanted = {entry["n"]: entry for entry in manifest["outputs"]}
    problems = [p for n, entry in wanted.items() for p in problems_of(n, entry, parsed.get(n))]
    problems += [f"output {n}: in the sheet but not in the manifest"
                 for n in parsed if n not in wanted]
    if problems:
        raise LabelError(f"the sheet is not complete ({len(problems)} problems):\n"
                         + "\n".join(f"- {p}" for p in problems))
    labels = []
    for n, entry in wanted.items():
        filled = parsed[n]
        labels.append({
            "n": n, "run_id": entry["run_id"], "item_id": entry["item_id"],
            "answer_hash": entry["answer_hash"],
            "key_points": [filled.keys[k].lower() for k in range(1, entry["key_points"] + 1)],
            "unsupported_claims": [c for c in filled.claims if c.lower() != "none"],
            "contradicted": filled.contradicted.lower() == "yes",
        })
    return {"labeled_by": by, "labeled_on": today.isoformat(), "labels": labels}
