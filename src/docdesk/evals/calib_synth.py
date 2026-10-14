"""Choose and build synthetic calibration outputs from the natural ones (T099, AC-EVL-07).

Why synthetic: the natural outputs are almost all faithful, so a judge that says "supported" to
everything would still score well on them. A few outputs with a known flaw (an unsupported
sentence added, or content cut) show whether the judge notices. These are a sensitivity check and
are reported apart from the natural outputs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Any

from docdesk.evals.calib_sample import Output, answer_hash
from docdesk.evals.calib_synth_text import (
    add_insertion,
    insertion_sentences,
    keep_first_sentence,
    split_sentences,
)

INSERTIONS = 5
OMISSIONS = 5
DASHES = ("—", "–")


def drug_of(title: str) -> str:
    """Why: two documents are the same drug when their label titles give the same name."""
    return title.lower().removesuffix(" drug label").strip()


@dataclass(frozen=True)
class Parent:
    """A natural output with what the rules need: its question, key points and drugs in context."""

    output: Output
    question: str
    key_points: int
    drugs: frozenset[str]


@dataclass(frozen=True)
class Candidate:
    """One chunk of a drug label that a sentence may be taken from."""

    chunk_id: str
    doc_source: str
    drug: str
    text: str


@dataclass(frozen=True)
class Synthetic:
    """One built output, its parent and (for an insertion) the document the sentence came from."""

    parent: Parent
    kind: str
    answer: str
    source_document: str | None = None


def has_dash(text: str) -> bool:
    """Why: the sheet and manifest may not hold em or en dashes, so such text is not used."""
    return any(dash in text for dash in DASHES)


def pick_omissions(parents: list[Parent], rng: random.Random) -> list[Synthetic]:
    """Multi chunk items with 2 or more sentences and key points; the first sentence is kept."""
    first_of_item: dict[str, Parent] = {}
    for p in parents:
        usable = p.output.category == "multi_chunk" and p.key_points >= 2
        if usable and len(split_sentences(p.output.answer)) >= 2:
            cut = keep_first_sentence(p.output.answer)
            if not has_dash(cut):
                first_of_item.setdefault(p.output.item_id, p)
    chosen = rng.sample(sorted(first_of_item), min(OMISSIONS, len(first_of_item)))
    return [Synthetic(first_of_item[i], "omission",
                      keep_first_sentence(first_of_item[i].output.answer)) for i in chosen]


def options_for(
    parent: Parent, candidates: list[Candidate], taken: set[str]
) -> list[tuple[Candidate, str]]:
    """Sentences of another drug from chunks the answerer did not see, one document once."""
    seen = f"{parent.question} {parent.output.answer}".lower()
    found = []
    for c in candidates:
        if c.chunk_id in parent.output.used_ids or c.doc_source in taken:
            continue
        if c.drug in parent.drugs or c.drug in seen:
            continue
        found += [(c, s) for s in insertion_sentences(c.text, c.drug) if not has_dash(s)]
    return found


def pick_insertions(
    parents: list[Parent], candidates: list[Candidate], rng: random.Random
) -> list[Synthetic]:
    """Append one concrete sentence from another drug to answers of items not yet used."""
    pool = [p for p in parents if not has_dash(p.output.answer)]
    rng.shuffle(pool)
    built: list[Synthetic] = []
    taken: set[str] = set()
    for p in pool:
        if len(built) == INSERTIONS:
            break
        options = options_for(p, candidates, taken)
        if options:
            chunk, sentence = rng.choice(options)
            taken.add(chunk.doc_source)
            built.append(Synthetic(p, "insertion", add_insertion(p.output.answer, sentence),
                                   chunk.doc_source))
    return built


def build_synthetic(
    parents: list[Parent], candidates: list[Candidate], *, seed: int
) -> list[Synthetic]:
    """Omissions first (fewer items qualify), then insertions on other items, then a shuffle."""
    rng = random.Random(seed)
    ordered = sorted(parents, key=lambda p: (p.output.item_id, p.output.run_id,
                                             p.output.answer_hash))
    omissions = pick_omissions(ordered, rng)
    used = {s.parent.output.item_id for s in omissions}
    rest = [p for p in ordered if p.output.item_id not in used]
    by_item = {p.output.item_id: p for p in reversed(rest)}  # the first row of an item wins
    insertions = pick_insertions(sorted(by_item.values(), key=lambda p: p.output.item_id),
                                 sorted(candidates, key=lambda c: c.chunk_id), rng)
    everything = omissions + insertions
    rng.shuffle(everything)
    return everything


def manifest_synthetic(items: list[Synthetic], *, seed: int, created: date) -> dict[str, Any]:
    """The set as data. The perturbation type lives here and never in the sheet."""
    outputs = []
    for n, item in enumerate(items, start=1):
        entry: dict[str, Any] = {
            "n": n, "synthetic_id": f"syn-{n:02d}",
            "parent_item_id": item.parent.output.item_id,
            "parent_run_id": item.parent.output.run_id,
            "parent_answer_hash": item.parent.output.answer_hash,
            "perturbation": item.kind, "answer": item.answer,
            "answer_hash": answer_hash(item.answer), "key_points": item.parent.key_points,
        }
        if item.source_document:
            entry["source_document"] = item.source_document
        outputs.append(entry)
    counts = {kind: sum(1 for i in items if i.kind == kind) for kind in ("insertion", "omission")}
    return {"created_on": created.isoformat(), "seed": seed, "sample_size": len(items),
            "counts": counts, "outputs": outputs}
