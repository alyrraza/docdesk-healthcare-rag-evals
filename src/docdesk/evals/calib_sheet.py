"""The blind calibration sheet and its manifest (T099, AC-EVL-07).

Why blind: the owner's labels are the ground truth the judge is measured against. If the sheet
showed a judge label, a score or a pass flag, the labels would drift toward the judge and the
agreement number would be inflated. Nothing here takes a judge field as input: a SheetEntry holds
only the question, the answer, the packed context and the reference key points.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from docdesk.evals.calib_sample import Output

KEY_VALUES = ("covered", "missing", "contradicted")
YES_NO = ("yes", "no")
SECTION_HEADING = "## {n} of {total} | {item_id}"
LABELS_HEADING = "### Your labels"

INSTRUCTIONS = f"""# Calibration sheet

Label each output below from what you read here only. Do not look anything else up.

For each output:
- key N: say whether the answer covers key point N. Write one of {", ".join(KEY_VALUES)}.
  Use covered when the answer says it, missing when it does not, contradicted when it says the
  opposite. Extra true information is fine and is not an error. Decide from the answer text only.
- unsupported claims: list every claim in the answer that the context does not support, one per
  line starting with "- ", or on the same line. Write none if every claim is supported.
- contradicted: write yes if any claim in the answer goes against the context, otherwise no.

Every field of every output must be filled in. A blank field is refused when you apply the sheet.
Dashes in the source text were replaced by a plain hyphen so the style check passes.
Chunks are numbered c1, c2 and so on in the order the answerer saw them.
"""


@dataclass(frozen=True)
class ChunkView:
    """One chunk of the packed context, as the answerer saw it."""

    title: str
    text: str


@dataclass(frozen=True)
class SheetEntry:
    """Everything shown for one output, and nothing from a judge."""

    n: int
    output: Output
    question: str
    context: list[ChunkView]
    key_points: list[str]


def plain(text: str) -> str:
    """Why: the docs style check bans em and en dashes in every markdown file, sheets included."""
    return text.replace("—", "-").replace("–", "-")


def quote(text: str) -> list[str]:
    """Blockquote every line, so text from a model or a label can never look like a heading."""
    return [f"> {line}".rstrip() for line in plain(text).splitlines() or [""]]


def render_entry(entry: SheetEntry, total: int) -> list[str]:
    """One output: question, answer, context, key points and the empty fields to fill."""
    heading = SECTION_HEADING.format(n=entry.n, total=total, item_id=entry.output.item_id)
    lines = [heading, "", f"Question: {plain(entry.question)}", "", "### Answer", "",
             *quote(entry.output.answer), "", "### Context the answerer saw", ""]
    for number, chunk in enumerate(entry.context, start=1):
        lines += [f"[c{number}] {plain(chunk.title)}", *quote(chunk.text), ""]
    lines += ["### Key points", ""]
    if entry.key_points:
        lines += [f"{number}. {plain(point)}" for number, point in enumerate(entry.key_points, 1)]
    else:
        lines.append("This item has no key points.")
    lines += ["", LABELS_HEADING, ""]
    lines += [f"key {number}:" for number in range(1, len(entry.key_points) + 1)]
    return [*lines, "unsupported claims:", "contradicted:", ""]


def render_sheet(entries: list[SheetEntry]) -> str:
    """The whole sheet in sample order."""
    lines = [INSTRUCTIONS]
    for entry in entries:
        lines += render_entry(entry, len(entries))
    return "\n".join(lines)


def manifest_of(
    entries: list[SheetEntry], *, seed: int, pool_size: int, shortfall: int, created: date
) -> dict[str, Any]:
    """The sample as data: which run, item and answer each sheet number stands for."""
    counts = Counter(e.output.category for e in entries)
    return {
        "created_on": created.isoformat(),
        "seed": seed,
        "pool_size": pool_size,
        "sample_size": len(entries),
        "shortfall": shortfall,
        "per_category": dict(sorted(counts.items())),
        "outputs": [
            {"n": e.n, "run_id": e.output.run_id, "item_id": e.output.item_id,
             "category": e.output.category, "answer_hash": e.output.answer_hash,
             "key_points": len(e.key_points)}
            for e in entries
        ],
    }
