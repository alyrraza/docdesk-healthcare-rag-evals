"""The agreement measures of the judge calibration and the list of every disagreement (T100)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from docdesk.evals.calib_join import JudgedOutput
from docdesk.evals.calib_stats import (
    SINGLE_CLASS,
    UNSTABLE_SHARE,
    KappaInterval,
    agreement,
    cohen_kappa,
    confusion,
    kappa_interval,
    majority_share,
)
from docdesk.evals.stats import DEFAULT_RESAMPLES, DEFAULT_SEED

FAITH_LABELS = ("not faithful", "faithful")
KEY_LABELS = ("covered", "missing", "contradicted")
COVERED_LABELS = ("not covered", "covered")
CORRECT_LABELS = ("not correct", "correct")


@dataclass(frozen=True)
class Measure:
    """One agreement measure: the table and every number derived from it."""

    name: str
    labels: tuple[str, ...]
    n: int
    table: list[list[int]]
    agreement: float | None
    kappa: float | None
    kappa_text: str
    interval: KappaInterval | None
    majority: float
    unstable: bool


@dataclass(frozen=True)
class Detection:
    """Bad output detection: the reference says bad, did the judge flag it, and the reverse."""

    tp: int
    fn: int
    fp: int
    tn: int

    @property
    def recall(self) -> float | None:
        """Of the outputs the reference flags, the share the judge flagged."""
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def precision(self) -> float | None:
        """Of the outputs the judge flagged, the share the reference also flags."""
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None


@dataclass(frozen=True)
class Disagreement:
    """One place where the judge and the reference differ, as plain facts."""

    set_name: str
    output_id: str
    level: str
    reference: str
    judge: str
    text: str
    borderline: bool


@dataclass(frozen=True)
class SetResult:
    """All measures of one set (natural or synthetic), over the outputs given."""

    measures: dict[str, Measure]
    detection: Detection
    excluded: list[str] = field(default_factory=list)


def measure(
    name: str, pairs: Sequence[tuple[str, str]], groups: Sequence[int], labels: tuple[str, ...],
    *, resamples: int = DEFAULT_RESAMPLES, seed: int = DEFAULT_SEED,
) -> Measure:
    """Why: every measure is reported the same way, and an undefined kappa is never a number."""
    table = confusion(pairs, labels)
    if not pairs:
        return Measure(name, labels, 0, table, None, None, "no data", None, 0.0, False)
    value = cohen_kappa(table)
    share = majority_share(table)
    interval = kappa_interval(pairs, groups, labels, resamples=resamples, seed=seed)
    text = SINGLE_CLASS if value is None else f"{value:.3f}"
    return Measure(name, labels, len(pairs), table, agreement(table), value, text, interval,
                   share, share > UNSTABLE_SHARE)


def ref_faithful(item: JudgedOutput) -> bool:
    """Reference faithful: no unsupported claim and no contradiction."""
    return not item.ref_claims and not item.ref_contradicted


def correct(keys: Sequence[str]) -> bool:
    """Correct: every key point covered and none contradicted."""
    return all(key == "covered" for key in keys)


def evaluate(
    outputs: Sequence[JudgedOutput], *, resamples: int = DEFAULT_RESAMPLES, seed: int = DEFAULT_SEED
) -> SetResult:
    """Compute every measure; outputs with no judge faithfulness score are listed and left out."""
    # One item can give several outputs (B0 and a rerun), so a bootstrap resamples items.
    item_index = {item: n for n, item in enumerate(sorted({o.item_id for o in outputs}))}
    scored = [(item_index[o.item_id], o) for o in outputs if o.judge.faith_score is not None]
    faith = [("faithful" if ref_faithful(o) else "not faithful",
              "faithful" if o.judge.faith_score == 1.0 else "not faithful") for _, o in scored]
    keys = [(item_index[o.item_id], ref, judge) for o in outputs
            for ref, judge in zip(o.ref_keys, o.judge.key_labels, strict=True)]
    key_pairs = [(ref, judge) for _, ref, judge in keys]
    key_groups = [i for i, _, _ in keys]
    covered = [("covered" if ref == "covered" else "not covered",
                "covered" if judge == "covered" else "not covered") for ref, judge in key_pairs]
    item = [("correct" if correct(o.ref_keys) else "not correct",
             "correct" if correct(o.judge.key_labels) else "not correct")
            for o in outputs if o.ref_keys]
    item_groups = [item_index[o.item_id] for o in outputs if o.ref_keys]
    kw = {"resamples": resamples, "seed": seed}
    measures = {
        "faithfulness_item": measure("faithfulness_item", faith, [i for i, _ in scored],
                                     FAITH_LABELS, **kw),
        "key_point_3class": measure("key_point_3class", key_pairs, key_groups, KEY_LABELS, **kw),
        "key_point_binary": measure("key_point_binary", covered, key_groups, COVERED_LABELS, **kw),
        "correct_item": measure("correct_item", item, item_groups, CORRECT_LABELS, **kw),
    }
    return SetResult(measures, detection_of(faith),
                     [o.output_id for o in outputs if o.judge.faith_score is None])


def detection_of(faith: Sequence[tuple[str, str]]) -> Detection:
    """Count the bad outputs the judge caught or missed, and the good ones it flagged."""
    def count(reference: str, judge: str) -> int:
        return sum(1 for pair in faith if pair == (reference, judge))

    return Detection(count("not faithful", "not faithful"), count("not faithful", "faithful"),
                     count("faithful", "not faithful"), count("faithful", "faithful"))


def make(o: JudgedOutput, level: str, reference: str, judge: str, text: str) -> Disagreement:
    """Why: all three levels build the same record, so the report can list them together."""
    return Disagreement(o.set_name, o.output_id, level, reference, judge, text, o.borderline)


def faithfulness_disagreement(o: JudgedOutput) -> list[Disagreement]:
    """The item level faithfulness label, when reference and judge differ."""
    score = o.judge.faith_score
    if score is None or ref_faithful(o) == (score == 1.0):
        return []
    flagged = "; ".join(f"{claim} ({label})" for claim, label in o.judge.claims
                        if label != "supported") or "none"
    listed = "; ".join(f'"{claim}"' for claim in o.ref_claims) or "none"
    text = (f"reference: unsupported claims {listed}, contradicted "
            f"{'yes' if o.ref_contradicted else 'no'}; judge: score {score}, "
            f"flagged claims {flagged}")
    return [make(o, "faithfulness item", "faithful" if ref_faithful(o) else "not faithful",
                 "faithful" if score == 1.0 else "not faithful", text)]


def key_point_disagreements(o: JudgedOutput) -> list[Disagreement]:
    """Each key point where the three class labels differ."""
    pairs = zip(o.ref_keys, o.judge.key_labels, strict=True)
    return [make(o, "key point", ref, judge, f"key {number}: {o.key_points[number - 1]}")
            for number, (ref, judge) in enumerate(pairs, start=1) if ref != judge]


def keys_line(keys: Sequence[str]) -> str:
    """The key point labels of one side as one readable line."""
    return ", ".join(f"key {number} {label}" for number, label in enumerate(keys, start=1))


def correctness_disagreement(o: JudgedOutput) -> list[Disagreement]:
    """The item level correctness label, when reference and judge differ."""
    if not o.ref_keys or correct(o.ref_keys) == correct(o.judge.key_labels):
        return []
    text = f"reference: {keys_line(o.ref_keys)}; judge: {keys_line(o.judge.key_labels)}"
    return [make(o, "correctness item", "correct" if correct(o.ref_keys) else "not correct",
                 "correct" if correct(o.judge.key_labels) else "not correct", text)]


def disagreements(outputs: Sequence[JudgedOutput]) -> list[Disagreement]:
    """Every place the judge differs from the reference, in output order, facts only."""
    return [d for o in outputs
            for d in (faithfulness_disagreement(o) + key_point_disagreements(o)
                      + correctness_disagreement(o))]
