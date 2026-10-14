"""Join the stored judge labels to the reference labels, on run id, item id and answer hash (T100).

Any gap stops the join with an error that names it: a changed answer, a missing row or a judge
call that failed must never become a quiet disagreement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from docdesk.evals.calib_sample import answer_hash
from docdesk.evals.report_data import ResultRecord

FAITHFULNESS_OK = ("scored", "no_claims")


class JoinError(ValueError):
    """The two sides cannot be joined; the message says which output and why."""


@dataclass(frozen=True)
class JudgeSide:
    """What the judges said about one output, in the same shape for natural and synthetic."""

    faith_status: str
    faith_score: float | None
    claims: list[tuple[str, str]]
    key_labels: list[str]


@dataclass(frozen=True)
class JudgedOutput:
    """One output with the reference labels, the judge's labels and whether it is borderline."""

    set_name: str
    n: int
    output_id: str
    item_id: str
    borderline: bool
    key_points: list[str]
    ref_keys: list[str]
    ref_claims: list[str]
    ref_contradicted: bool
    judge: JudgeSide


def judge_side(name: str, faith: Mapping[str, Any], corr: Mapping[str, Any]) -> JudgeSide:
    """Why: both sources are checked the same way, so a failed judge call stops either set."""
    if faith["status"] not in FAITHFULNESS_OK:
        raise JoinError(f"{name}: faithfulness judge status is {faith['status']}")
    if corr["status"] != "scored":
        raise JoinError(f"{name}: correctness judge status is {corr['status']}")
    ordered = sorted(corr["labels"], key=lambda label: label["point"])
    return JudgeSide(
        faith["status"], faith["score"], [(c["claim"], c["label"]) for c in faith["labels"]],
        [label["label"] for label in ordered])


def record_side(name: str, record: ResultRecord) -> JudgeSide:
    """The judge labels the runner stored in a result row."""
    faith = {"status": record.metrics.get("faithfulness_status"),
             "score": record.metrics.get("faithfulness"),
             "labels": record.trace.get("faithfulness_labels", [])}
    corr = {"status": record.metrics.get("correctness_status"),
            "labels": record.trace.get("correctness_labels", [])}
    return judge_side(name, faith, corr)


def result_side(name: str, result: Mapping[str, Any]) -> JudgeSide:
    """The judge labels saved in judge_results_synthetic.yaml."""
    faith, corr = result["faithfulness"], result["correctness"]
    return judge_side(
        name, {"status": faith["status"], "score": faith["score"], "labels": faith["claims"]},
        {"status": corr["status"], "labels": corr["key_points"]})


def reference(name: str, entry: Mapping[str, Any], label: Mapping[str, Any]) -> None:
    """The label entry must be the one the manifest names, or the join would pair wrong rows."""
    for field in ("n", "answer_hash"):
        if label[field] != entry[field]:
            raise JoinError(f"{name}: the labels {field} differs from the manifest")
    if len(label["key_points"]) != entry["key_points"]:
        raise JoinError(f"{name}: the labels have {len(label['key_points'])} key points, "
                        f"the manifest has {entry['key_points']} key points")


def build(
    set_name: str, name: str, entry: Mapping[str, Any], item_id: str, label: Mapping[str, Any],
    side: JudgeSide, facts: Sequence[str], borderline: frozenset[int],
) -> JudgedOutput:
    """Assemble one JudgedOutput after checking the key point counts agree everywhere."""
    if not (len(facts) == len(side.key_labels) == len(label["key_points"])):
        raise JoinError(f"{name}: key point counts differ between the golden item, the labels "
                        "and the judge")
    return JudgedOutput(
        set_name, entry["n"], str(entry.get("synthetic_id", entry["n"])), item_id,
        entry["n"] in borderline, list(facts), list(label["key_points"]),
        list(label["unsupported_claims"]), bool(label["contradicted"]), side)


def join_natural(
    manifest: Mapping[str, Any], labels: Mapping[str, Any],
    rows: Mapping[str, Sequence[ResultRecord]], facts: Mapping[str, Sequence[str]],
    borderline: frozenset[int],
) -> list[JudgedOutput]:
    """Natural outputs: the stored row of (run id, item id) must still hold the sampled answer."""
    by_n = {label["n"]: label for label in labels["labels"]}
    joined = []
    for entry in manifest["outputs"]:
        item_id = entry["item_id"]
        name = f"{item_id} (output {entry['n']})"
        label = by_n.get(entry["n"])
        if label is None or (label["run_id"], label["item_id"]) != (entry["run_id"], item_id):
            raise JoinError(f"{name}: no label for this run and item")
        reference(name, entry, label)
        found = [r for r in rows.get(entry["run_id"], []) if r.item_id == item_id]
        if not found:
            raise JoinError(f"{name}: no stored row in run {entry['run_id']}")
        if answer_hash(str(found[0].trace.get("answer", ""))) != entry["answer_hash"]:
            raise JoinError(f"{name}: the stored answer hash differs from the manifest")
        side = record_side(name, found[0])
        joined.append(build("natural", name, entry, item_id, label, side, facts[item_id],
                            borderline))
    return joined


def join_synthetic(
    manifest: Mapping[str, Any], labels: Mapping[str, Any], results: Mapping[str, Any],
    facts: Mapping[str, Sequence[str]], borderline: frozenset[int],
) -> list[JudgedOutput]:
    """Synthetic outputs: the judge result must be for the exact text of the manifest."""
    by_n = {label["n"]: label for label in labels["labels"]}
    by_id = {result["synthetic_id"]: result for result in results["results"]}
    joined = []
    for entry in manifest["outputs"]:
        name = entry["synthetic_id"]
        result, label = by_id.get(name), by_n.get(entry["n"])
        if result is None:
            raise JoinError(f"{name}: no judge result in the results file")
        if label is None or label["synthetic_id"] != name:
            raise JoinError(f"{name}: no label for this output")
        if answer_hash(entry["answer"]) != entry["answer_hash"]:
            raise JoinError(f"{name}: the manifest text does not match its own hash")
        if result["answer_hash"] != entry["answer_hash"]:
            raise JoinError(f"{name}: the judged text hash differs from the manifest")
        reference(name, entry, label)
        side = result_side(name, result)
        item_id = entry["parent_item_id"]
        joined.append(build("synthetic", name, entry, item_id, label, side, facts[item_id],
                            borderline))
    return joined
