"""The owner's review loop: golden drafts out as a markdown sheet, decisions back in."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from docdesk.evals.golden.probe import Probe, render_probe
from docdesk.evals.golden.schema import GoldenItem

BATCH_LINE = re.compile(r"^Batch file:\s*(.+?)\s*$", re.MULTILINE)
ITEM_HEADING = re.compile(r"^## (gi-\d{3})\s*$", re.MULTILINE)
DECISION_LINE = re.compile(r"^Decision:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
DECISION_KINDS = ("OK", "FIX", "DROP")


class SheetError(ValueError):
    """The sheet or the batch file cannot be read the way the review loop needs."""


@dataclass(frozen=True)
class Decision:
    """What the owner wrote for one item: OK, FIX with a note, DROP, or nothing yet."""

    kind: str
    note: str = ""


@dataclass(frozen=True)
class ParsedSheet:
    """A sheet read back: the batch file it came from and a decision per item id."""

    batch_file: str
    decisions: dict[str, Decision]


@dataclass
class ApplyResult:
    """What an apply did, so the owner sees every item that still needs work."""

    verified: list[str] = field(default_factory=list)
    fix: list[tuple[str, str]] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    undecided: list[str] = field(default_factory=list)


def render_absence(item: GoldenItem, probe: Probe | None) -> list[str]:
    """For an item without an answer: why, what code proved absent, and what retrieval finds."""
    if item.answerable:
        return []
    lines = [f"- why there is no answer: {item.no_evidence_reason}"]
    if item.absent_terms:
        lines.append(
            f"- absent terms: {', '.join(item.absent_terms)} (scope: {item.absence_scope})"
        )
    return lines + (render_probe(probe) if probe else [])


def render_injection(item: GoldenItem) -> list[str]:
    """For an injected instruction item: the canary and the full text of each poisoned fixture."""
    if item.canary is None:
        return []
    lines = [f"- canary: {item.canary}"]
    for number, fixture in enumerate(item.fixture_documents, start=1):
        lines += [f"- fixture {number}: {fixture.title}", f"  > {' '.join(fixture.text.split())}"]
    return lines


def render_item(item: GoldenItem, titles: dict[str, str], probe: Probe | None = None) -> str:
    """One item's block: every field the owner needs to judge the question, answer and quotes."""
    lines = [
        f"## {item.id}",
        "",
        f"- category: {item.type}",
        f"- split: {item.split}",
        f"- question: {item.question}",
        f"- expected behavior: {item.behavior}",
        "- reference answer:",
        *[f"  - {fact}" for fact in item.gold_facts],
    ]
    for number, entry in enumerate(item.gold_evidence, start=1):
        title = titles.get(entry.source, "title unknown")
        lines += [
            f"- evidence {number}: {entry.source}",
            f"  - document: {title}",
            f"  > {entry.text}",
        ]
    lines += render_absence(item, probe)
    lines += render_injection(item)
    return "\n".join([*lines, "", "Decision:", ""])


def render_sheet(
    items: list[GoldenItem],
    titles: dict[str, str],
    batch_file: str,
    probes: Mapping[str, Probe] | None = None,
) -> str:
    """The whole review sheet; the owner types a decision after each `Decision:` line."""
    header = [
        f"# Golden review: {Path(batch_file).stem}",
        "",
        f"Batch file: {batch_file}",
        "",
        "After each `Decision:` write one of: `OK`, `FIX: <note>` or `DROP`.",
        "OK means the question, the reference answer and the quote are all correct and the",
        "answer is fully supported by the quote alone.",
        "",
    ]
    blocks = [render_item(item, titles, (probes or {}).get(item.id)) for item in items]
    return "\n".join(header) + "\n" + "\n".join(blocks)


def parse_decision(item_id: str, text: str) -> Decision:
    """Read one decision line; an unknown word is an error, never a silent skip."""
    if not text:
        return Decision("UNDECIDED")
    kind, _, note = text.partition(":")
    kind = kind.strip().upper()
    if kind not in DECISION_KINDS:
        raise SheetError(f"{item_id}: decision {text!r} is not OK, FIX: <note> or DROP")
    return Decision(kind, note.strip())


def parse_sheet(text: str) -> ParsedSheet:
    """Read the batch file path and every item's decision from a filled in sheet."""
    batch = BATCH_LINE.search(text)
    if batch is None:
        raise SheetError("the sheet has no 'Batch file:' line")
    headings = list(ITEM_HEADING.finditer(text))
    decisions: dict[str, Decision] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        found = DECISION_LINE.search(text[heading.end() : end])
        item_id = heading.group(1)
        decisions[item_id] = parse_decision(item_id, found.group(1) if found else "")
    return ParsedSheet(batch.group(1), decisions)


def apply_decisions(sheet: ParsedSheet, by: str, today: date) -> ApplyResult:
    """Mark OK items verified in the batch file; FIX and DROP items are listed, not deleted."""
    path = Path(sheet.batch_file)
    entries: list[dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in entries}
    unknown = [item_id for item_id in sheet.decisions if item_id not in by_id]
    if unknown:
        raise SheetError(f"the sheet names items that are not in {path.name}: {', '.join(unknown)}")
    result = ApplyResult()
    for item_id, decision in sheet.decisions.items():
        if decision.kind == "OK":
            by_id[item_id].update(verified=True, verified_by=by, verified_on=today)
            result.verified.append(item_id)
        elif decision.kind == "UNDECIDED":
            result.undecided.append(item_id)
        else:
            by_id[item_id]["verified"] = False
            if decision.kind == "FIX":
                result.fix.append((item_id, decision.note))
            else:
                result.dropped.append(item_id)
    dump = yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=10000)
    path.write_text(dump, encoding="utf-8")
    return result
