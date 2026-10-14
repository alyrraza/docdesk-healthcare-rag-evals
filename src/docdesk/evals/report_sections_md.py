"""Markdown for the answerable item sections of the report (T098a). No dash characters."""

from __future__ import annotations

from docdesk.evals.report_data import Report
from docdesk.evals.report_sections import (
    OUTCOMES,
    STAGES,
    label_by_outcome,
    stage_split,
    strict_pass_rate,
    worst_answered,
)
from docdesk.evals.report_table import table

STAGE_NAMES = {
    "retrieval": "retrieval (gold not in top k)",
    "packing": "packing (gold in top k, dropped before the prompt)",
    "generation": "generation (gold in the prompt)",
    "pass": "pass",
}


def headline_lines(report: Report) -> list[str]:
    """The answerable only pass rate first, next to the overall rate."""
    strict = strict_pass_rate(report.run.records)
    overall = report.overall.metrics["pass_rate"].interval
    rate = strict.cell.interval
    strict_text = ("n/a" if rate is None
                   else f"{rate.estimate:.2f} [{rate.low:.2f}, {rate.high:.2f}]")
    overall_text = ("n/a" if overall is None
                    else f"{overall.estimate:.2f} [{overall.low:.2f}, {overall.high:.2f}]")
    return [
        f"Headline: {strict.passed} of {strict.n} answerable items pass strictly "
        f"(faithfulness 1.0 and correctness 1.0), rate {strict_text}. "
        f"The overall pass rate is {overall_text} over {report.total_ok} items.",
        "",
        "Unanswerable items pass by abstaining, so they raise the overall pass rate. "
        "The headline leaves them out.", "",
    ]


def stage_lines(report: Report) -> list[str]:
    """Answerable items by the stage that failed them, with the labels behind each stage."""
    split = stage_split(report.run.records)
    rows = [[STAGE_NAMES[s], str(split.counts[s]),
             ", ".join(f"{k} {v}" for k, v in split.labels[s].items())] for s in STAGES]
    before_model = split.counts["retrieval"] + split.counts["packing"]
    return [
        "## Where answerable items fail", "",
        f"Answerable items that ran: {split.n}. A failed item has one primary label.", "",
        *table(["stage", "items", "labels"], rows), "",
        f"Retrieval and packing together are the stages before the model: "
        f"{before_model} of {split.n}.", "",
    ]


def outcome_lines(report: Report) -> list[str]:
    """Failure label by outcome for every item that ran, so wrong abstains show under a label."""
    rows = [[label, *(str(counts.get(o, 0)) for o in OUTCOMES)]
            for label, counts in label_by_outcome(report.run.records).items()]
    return [
        "## Failure label by outcome", "",
        "An answerable item that abstained is a wrong abstain, listed under its first label.",
        "", *table(["label", *OUTCOMES], rows), "",
    ]


def usage_lines(report: Report) -> list[str]:
    """Tokens and cost per model for this run only, billed apart from cached."""
    if report.model_usage is None:
        return ["## Tokens and cost per model", "",
                "The per run token numbers are not available for this run: it was stored before "
                "per call usage was recorded, and the cache folder cannot say which run a "
                "call belonged to.", ""]
    if not report.model_usage:
        return []
    rows = [[u.model, str(u.calls), str(u.cached_calls), str(u.tokens_billed),
             str(u.tokens_saved), f"{u.cost_billed:.6f}"] for u in report.model_usage]
    return [
        "## Tokens and cost per model", "",
        "This run only. Billed tokens were sent to the provider. Saved tokens were answered by "
        "the cache and cost nothing this run. Cost is the list price equivalent of the billed "
        "calls.", "",
        *table(["model", "calls", "cached calls", "tokens billed", "tokens saved",
                "cost billed USD"], rows), "",
    ]


def worst_lines(report: Report) -> list[str]:
    """The five answered items with the lowest judge score, one line of counts each."""
    worst = worst_answered(report.run.records)
    if not worst:
        return []
    items = [f"{n}. {w.item_id} ({w.item_type}), label {w.label or 'none'}: {w.line}"
             for n, w in enumerate(worst, start=1)]
    return ["## Worst five answered items", "",
            "Ranked by the lower of faithfulness and correctness, then by item id.", "", *items, ""]
