"""Markdown for the report and the comparison (T095). No em or en dashes: the docs hook checks."""

from __future__ import annotations

from docdesk.evals.report_compare import Comparison
from docdesk.evals.report_data import (
    RESAMPLES,
    SEED,
    Category,
    MetricCell,
    Report,
)
from docdesk.evals.report_sections_md import (
    headline_lines,
    outcome_lines,
    stage_lines,
    usage_lines,
    worst_lines,
)
from docdesk.evals.report_table import table

COLUMNS = (
    ("pass_rate", "pass rate"), ("recall", "recall@k"), ("hit", "hit"), ("mrr", "MRR"),
    ("context_precision", "context precision"), ("citation_precision", "citation precision"),
    ("citation_recall", "citation recall"), ("faithfulness", "faithfulness"),
    ("correctness", "correctness"),
)


def format_cell(cell: MetricCell, category_n: int) -> str:
    """Mean and interval; n is shown when some items had no value (a judge failure, no gold)."""
    if cell.interval is None:
        return "n/a"
    i = cell.interval
    text = f"{i.estimate:.2f} [{i.low:.2f}, {i.high:.2f}]"
    return text if cell.n == category_n else f"{text} (n={cell.n})"


def category_row(c: Category) -> list[str]:
    """One table row: name, n, then every metric cell."""
    return [c.name, str(c.n)] + [format_cell(c.metrics[key], c.n) for key, _ in COLUMNS]


def counts_section(title: str, counts: dict[str, int], empty: str) -> list[str]:
    """A small label to count table, or one line saying there is nothing."""
    if not counts:
        return [f"## {title}", "", empty, ""]
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    rows = [[name, str(count)] for name, count in ordered]
    return [f"## {title}", "", *table(["label", "items"], rows), ""]


def report_markdown(report: Report) -> str:
    """The whole report as one markdown string."""
    run, a = report.run, report.abstention
    lines = [
        f"# Eval report, run {run.run_id}", "",
        f"Config {run.config_id}, split {run.split}, mode {run.mode}. "
        f"Items run: {report.total_ok}. Items not run: {len(report.not_run)}.", "",
        f"Intervals are 95 percent bootstrap intervals of the mean, {RESAMPLES} resamples, "
        f"seed {SEED}. "
        "Items that share a source document are resampled together. "
        "A cell shows n when some items had no value for it.", "",
        *headline_lines(report),
        "## Results per category", "",
        *table(["category", "items"] + [label for _, label in COLUMNS],
               [category_row(c) for c in [*report.categories, report.overall]]), "",
        "## Abstain and refusal", "",
        *table(["cell", "items"], [
            ["correct abstain", str(a.correct_abstain)], ["wrong abstain", str(a.wrong_abstain)],
            ["missed abstain", str(a.missed_abstain)], ["correct refusal", str(a.correct_refusal)],
            ["wrong refusal", str(a.wrong_refusal)], ["missed refusal", str(a.missed_refusal)],
            ["system errors", str(a.errors)],
        ]), "",
        *counts_section("Failure labels", report.failure_labels, "No failed items."),
    ]
    failures = {f"{judge}: {kind}": n for judge, kinds in report.judge_failures.items()
                for kind, n in kinds.items()}
    lines += counts_section("Judge failures", failures, "No judge parse failures or errors.")
    lines += [
        "## Tokens and cost", "",
        f"Tokens in {report.tokens_in}, tokens out {report.tokens_out}, "
        f"cost {report.cost_usd} USD, model calls {report.llm_calls}, "
        f"cache hits {report.cache_hits}. Runs stored before T098b count judge cache hits only.",
        "",
        *usage_lines(report), *stage_lines(report), *outcome_lines(report), *worst_lines(report),
        "## Not run", "",
    ]
    if report.not_run:
        lines += [f"- {item_id}: {reason}" for item_id, reason in report.not_run]
    else:
        lines.append("Every verified item ran.")
    return "\n".join(lines) + "\n"


def compare_markdown(result: Comparison) -> str:
    """The paired comparison as markdown; a gap inside the interval is no clear difference."""
    rows = []
    for row in result.rows:
        if row.paired is None:
            rows.append([row.metric, "0", "n/a", "n/a", "n/a"])
            continue
        p = row.paired
        rows.append([row.metric, str(row.n_paired), f"{p.mean_difference:+.3f}",
                     f"[{p.low:+.3f}, {p.high:+.3f}]", p.verdict])
    lines = [
        f"# Comparison, candidate {result.candidate_id} against baseline {result.baseline_id}", "",
        f"Paired on {result.shared} shared items. Difference is candidate minus baseline, "
        f"95 percent bootstrap interval, {RESAMPLES} resamples, seed {SEED}.", "",
        *table(["metric", "items", "difference", "interval", "verdict"], rows), "",
    ]
    for name, ids in (("only in the baseline", result.only_baseline),
                      ("only in the candidate", result.only_candidate)):
        if ids:
            lines.append(f"Items {name} (left out): {', '.join(ids)}.")
    return "\n".join(lines) + "\n"
