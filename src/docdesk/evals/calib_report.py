"""Render the judge calibration summary as markdown (T100). The text holds no number of its own."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from docdesk.evals.calib_sheet import plain

TITLES = {
    "faithfulness_item": "Faithfulness, item level",
    "key_point_3class": "Key points, three classes",
    "key_point_binary": "Key points, covered or not",
    "correct_item": "Correctness, item level",
}
SET_TITLES = {"natural": "Natural outputs", "synthetic": "Synthetic outputs"}
VARIANT_TITLES = {"all": "All outputs", "without_borderline": "Without the borderline outputs"}


def number(value: float | None) -> str:
    """Three decimals, or n/a when there is no value."""
    return "n/a" if value is None else f"{value:.3f}"


def cell(text: object) -> str:
    """Keep a table cell on one line and keep a pipe inside it from splitting the row."""
    return plain(" ".join(str(text).split())).replace("|", "/")


def plain_tree(value: Any) -> Any:
    """Why: the style check bans em and en dashes, and label text is copied from models."""
    if isinstance(value, str):
        return plain(value)
    if isinstance(value, dict):
        return {key: plain_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain_tree(item) for item in value]
    return value


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    """A markdown table as lines."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]


def interval_text(m: Mapping[str, Any]) -> str:
    """The kappa interval and how many resamples it rests on."""
    found = m["interval"]
    if found is None or found["low"] is None:
        return "n/a"
    return f"{found['low']:.3f} to {found['high']:.3f} ({found['valid']} of {found['resamples']})"


def note_text(m: Mapping[str, Any]) -> str:
    """Why a kappa should be read with care, stated as a fact about the labels."""
    if m["kappa"] is None and m["n"]:
        return "one class only on one side, counts in the matrix"
    if m["unstable"]:
        return f"kappa unstable, one class has {m['majority_share'] * 100:.0f} percent of labels"
    return ""


def headline(measures: Mapping[str, Any]) -> list[str]:
    """One row per measure: n, raw agreement, kappa and its interval."""
    rows = [(TITLES[name], m["n"], number(m["agreement"]), m["kappa_text"], interval_text(m),
             note_text(m)) for name, m in measures.items()]
    return table(["Measure", "n", "Raw agreement", "Kappa", "95% interval (valid resamples)",
                  "Note"], rows)


def matrices(measures: Mapping[str, Any]) -> list[str]:
    """The confusion matrix of every measure, reference in rows and judge in columns."""
    lines: list[str] = []
    for name, m in measures.items():
        lines += ["", f"{TITLES[name]} (n {m['n']}, rows are the reference, columns the judge)", ""]
        rows = [[label, *counts] for label, counts in zip(m["labels"], m["table"], strict=True)]
        lines += table(["reference \\ judge", *m["labels"]], rows)
    return lines


def fraction(count: int, total: int, value: float | None) -> str:
    """Counts first, so a tiny denominator is visible next to the ratio."""
    return f"{count} of {total} ({number(value)})" if total else "n/a (no such outputs)"


def detection_lines(found: Mapping[str, Any]) -> list[str]:
    """Bad output detection from the faithfulness item table."""
    tp, fn, fp = found["tp"], found["fn"], found["fp"]
    return ["", "Bad output detection (reference lists an unsupported claim or a contradiction):",
            "",
            f"- recall: {fraction(tp, tp + fn, found['recall'])}. Of the outputs the reference "
            "flags, how many the judge flagged.",
            f"- precision: {fraction(tp, tp + fp, found['precision'])}. Of the outputs the judge "
            "flagged, how many the reference also flags."]


def variant_lines(name: str, found: Mapping[str, Any]) -> list[str]:
    """Headline table, matrices, detection and exclusions of one variant."""
    lines = [f"### {VARIANT_TITLES[name]} (n {found['n_outputs']})", ""]
    lines += headline(found["measures"]) + matrices(found["measures"])
    lines += detection_lines(found["detection"])
    excluded = found["excluded_no_faithfulness_score"]
    lines += ["", "Outputs with no judge faithfulness score (zero claims), left out of the "
              f"faithfulness measures: {', '.join(excluded) if excluded else 'none'}.", ""]
    return lines


def disagreement_lines(found: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every disagreement as a row of facts."""
    lines = ["### Disagreements", "", f"Number of disagreements: {len(found)}.", ""]
    if not found:
        return lines
    rows = [(d["output_id"], d["level"], d["reference"], d["judge"], d["text"],
             "yes" if d["borderline"] else "no") for d in found]
    header = ["Output", "Level", "Reference", "Judge", "Text", "Borderline"]
    return lines + table(header, rows) + [""]


def set_lines(name: str, found: Mapping[str, Any]) -> list[str]:
    """One whole set section."""
    lines = [f"## {SET_TITLES[name]}", "",
             f"{found['n_outputs']} outputs. Borderline output numbers on the sheet: "
             f"{', '.join(map(str, found['borderline_numbers'])) or 'none'}.", ""]
    for variant, body in found["variants"].items():
        lines += variant_lines(variant, body)
    return lines + disagreement_lines(found["disagreements"])


def top_lines(summary: Mapping[str, Any]) -> list[str]:
    """What a reader must know before any number."""
    natural, synthetic = summary["sets"]["natural"], summary["sets"]["synthetic"]
    boot = summary["bootstrap"]
    share = natural["reference_faithful"] / natural["n_outputs"]
    word = "almost all" if share >= 0.9 else "mostly"
    return [
        "# Judge calibration report", "",
        "Generated by scripts/calibration_report.py. Do not edit by hand.", "",
        summary["provenance"], "",
        f"- The sample is small: {natural['n_outputs']} natural and {synthetic['n_outputs']} "
        "synthetic outputs, so every interval is wide.",
        f"- Natural outputs are {word} faithful: {natural['reference_faithful']} of "
        f"{natural['n_outputs']} have no unsupported claim and no contradiction in the reference "
        "labels, so kappa on faithfulness is unstable there.",
        "- Synthetic outputs are a sensitivity check built by code (inserted or removed "
        "sentences). They are not real answers and are never pooled with the natural outputs.",
        f"- Intervals are {boot['confidence'] * 100:.0f} percent percentile bootstrap intervals "
        f"over whole outputs, {boot['resamples']} resamples, seed {boot['seed']}. A resample "
        "where one side has a single class has no kappa and is left out of the interval.",
        "- Kappa is reported as undefined when the reference or the judge uses one class only.",
        "- This report gives no pass or fail verdict.", "",
        f"Judge model: {summary['judge']['model']}. Prompts: "
        + ", ".join(f"{k} {v[:12]}" for k, v in summary["judge"]["prompts"].items()) + ".", ""]


def render_markdown(summary: Mapping[str, Any]) -> str:
    """The full report text."""
    lines = top_lines(summary)
    for name, found in summary["sets"].items():
        lines += set_lines(name, found)
    return "\n".join(lines).rstrip() + "\n"
