"""The judge calibration pool and a seeded, stratified sample of it (T099, AC-EVL-07).

Why a separate file: which outputs get hand labeled decides what the judge is measured on, so the
rule is code with tests, not a choice made while looking at the data.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass

from docdesk.evals.report_data import ResultRecord

SEED = 20261014
SAMPLE_SIZE = 40
CORE_CATEGORIES = ("single_fact", "multi_chunk")
# Answered outputs here are the best test of the judge, so every one is sampled.
MUST_HAVE_CATEGORIES = ("unanswerable", "adversarial")


def answer_hash(text: str) -> str:
    """Why: the manifest names an output by the hash of its text, so an edit is noticed."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Output:
    """One answered output of one run, with the chunk ids the answerer was shown."""

    run_id: str
    item_id: str
    category: str
    answer: str
    used_ids: tuple[str, ...]

    @property
    def answer_hash(self) -> str:
        """The hash that identifies this answer text."""
        return answer_hash(self.answer)


@dataclass(frozen=True)
class Sample:
    """The chosen outputs in sheet order, and how many slots could not be filled."""

    outputs: list[Output]
    shortfall: int


def pool_from_runs(runs: list[tuple[str, list[ResultRecord]]]) -> list[Output]:
    """Answered outputs of the runs; a repeat of the same item and answer text is dropped.

    The first run in the list wins a duplicate, so the order of the runs is the tie break.
    """
    pool: list[Output] = []
    seen: set[tuple[str, str]] = set()
    for run_id, records in runs:
        for record in sorted(records, key=lambda r: r.item_id):
            if record.metrics.get("status") != "ok" or record.metrics.get("outcome") != "answered":
                continue
            answer = record.trace.get("answer", "")
            if not answer or (record.item_id, answer) in seen:
                continue
            seen.add((record.item_id, answer))
            pool.append(Output(run_id, record.item_id, record.metrics["type"], answer,
                               tuple(record.trace.get("used_ids", []))))
    return pool


def core_quotas(sizes: dict[str, int], slots: int) -> dict[str, int]:
    """Split slots over the core categories in proportion to their pools, capped by each pool."""
    total = sum(sizes.values())
    if total <= slots:
        return dict(sizes)
    quotas = {name: slots * size // total for name, size in sizes.items()}
    by_remainder = sorted(sizes, key=lambda n: (-(slots * sizes[n] % total), n))
    while sum(quotas.values()) < slots:
        for name in by_remainder:
            if quotas[name] < sizes[name] and sum(quotas.values()) < slots:
                quotas[name] += 1
    return quotas


def sample_outputs(pool: list[Output], size: int = SAMPLE_SIZE, seed: int = SEED) -> Sample:
    """Every must-have output, then the core categories in proportion, then a seeded shuffle."""
    rng = random.Random(seed)
    ordered = sorted(pool, key=lambda o: (o.category, o.item_id, o.run_id, o.answer_hash))
    chosen = [o for o in ordered if o.category in MUST_HAVE_CATEGORIES]
    core = {name: [o for o in ordered if o.category == name] for name in CORE_CATEGORIES}
    slots = max(size - len(chosen), 0)
    quotas = core_quotas({name: len(found) for name, found in core.items()}, slots)
    for name in CORE_CATEGORIES:
        chosen += rng.sample(core[name], quotas[name])
    rng.shuffle(chosen)
    return Sample(chosen, max(size - len(chosen), 0))


def counts_by_category(outputs: list[Output]) -> dict[str, int]:
    """How many sampled outputs each category has, for the manifest and the final report."""
    return dict(sorted(Counter(o.category for o in outputs).items()))
