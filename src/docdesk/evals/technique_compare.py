"""Paired comparison of a technique run against the baseline, per category and overall (Phase 5)."""

from __future__ import annotations

import json
from typing import Any

from docdesk.evals.identity import identity_warnings
from docdesk.evals.report_data import RESAMPLES, SEED, ResultRecord, RunData, value_of
from docdesk.evals.report_latency import latency_stats
from docdesk.evals.report_sections import is_strict_pass
from docdesk.evals.report_table import table
from docdesk.evals.report_usage import usage_from_records
from docdesk.evals.stats import paired_comparison

METRICS = ("strict_pass", "recall", "mrr", "faithfulness", "correctness")
ORDER = ("single_fact", "multi_chunk", "structured", "mixed", "unanswerable", "adversarial")


def ran(data: RunData) -> dict[str, ResultRecord]:
    """Items that ran with a score row; not run and not scored items are left out."""
    return {r.item_id: r for r in data.records if r.metrics.get("status") == "ok"}


def metric_value(record: ResultRecord, metric: str) -> float | None:
    """One value per item; strict pass is 0 or 1 for answerable items only."""
    if metric == "strict_pass":
        if record.metrics.get("behavior") != "answer":
            return None
        return float(is_strict_pass(record))
    return value_of(record, metric)


def row(metric: str, base: dict[str, ResultRecord], cand: dict[str, ResultRecord],
        ids: list[str]) -> dict[str, Any]:
    """The paired difference of one metric over the given items that both runs have a value for."""
    both = [i for i in ids if metric_value(base[i], metric) is not None
            and metric_value(cand[i], metric) is not None]
    if not both:
        return {"metric": metric, "n": 0}
    first = [metric_value(base[i], metric) for i in both]
    second = [metric_value(cand[i], metric) for i in both]
    groups = [base[i].metrics.get("group", i) for i in both]
    paired = paired_comparison(first, second, groups=groups,
                               n_resamples=RESAMPLES, seed=SEED)
    return {"metric": metric, "n": len(both), "baseline": sum(first) / len(both),
            "candidate": sum(second) / len(both), "difference": paired.mean_difference,
            "low": paired.low, "high": paired.high, "verdict": paired.verdict}


def wrong_abstains(records: dict[str, ResultRecord]) -> int:
    """Answerable items the system declined."""
    return sum(1 for r in records.values()
               if r.metrics.get("behavior") == "answer" and r.metrics.get("outcome") == "abstained")


def billed_tokens(data: RunData) -> int | None:
    """Tokens sent to the provider in this run; None when per call usage was never recorded."""
    usage = usage_from_records(data.records)
    return None if usage is None else sum(u.tokens_billed for u in usage)


MIN_LATENCY_ITEMS = 5


def p95_total(data: RunData) -> float | str | None:
    """The 95th percentile of total item time over non cached items; None if not recorded.

    With fewer than five non cached items a percentile says nothing, so the text says that.
    """
    stat = latency_stats(data.records).get("total_ms")
    if stat is None:
        return None
    return stat.p95 if stat.n >= MIN_LATENCY_ITEMS else "too few non cached items"


def compare_technique(name: str, baseline: RunData, candidate: RunData) -> dict[str, Any]:
    """Everything the technique report needs, as plain data."""
    base, cand = ran(baseline), ran(candidate)
    shared = sorted(base.keys() & cand.keys())
    answerable = [i for i in shared if metric_value(base[i], "strict_pass") is not None]
    gained = [i for i in answerable if is_strict_pass(cand[i]) and not is_strict_pass(base[i])]
    lost = [i for i in answerable if is_strict_pass(base[i]) and not is_strict_pass(cand[i])]
    kinds = [k for k in ORDER if any(base[i].metrics.get("type") == k for i in shared)]
    faith = row("faithfulness", base, cand, shared)
    lowered = faith.get("n", 0) > 0 and faith["difference"] < -1e-9
    improves = len(gained) - len(lost) >= 1
    warnings = identity_warnings(baseline.identity, candidate.identity)
    if baseline.split != candidate.split:
        warnings.insert(0, f"split differs: {baseline.split} against {candidate.split}")
    return {
        "technique": name, "baseline_run": baseline.run_id, "candidate_run": candidate.run_id,
        "baseline_config": baseline.config_id, "candidate_config": candidate.config_id,
        "split": candidate.split, "shared_items": len(shared), "warnings": warnings,
        "overall": [row(m, base, cand, shared) for m in METRICS],
        "categories": [{"name": k, "rows": [
            row(m, base, cand, [i for i in shared if base[i].metrics.get("type") == k])
            for m in METRICS]} for k in kinds],
        "strict_pass": {
            "answerable": len(answerable),
            "baseline": sum(is_strict_pass(base[i]) for i in answerable),
            "candidate": sum(is_strict_pass(cand[i]) for i in answerable),
            "gained": gained, "lost": lost},
        "wrong_abstain": {"baseline": wrong_abstains(base), "candidate": wrong_abstains(cand)},
        "tokens_billed": {"baseline": billed_tokens(baseline),
                          "candidate": billed_tokens(candidate)},
        "p95_total_ms": {"baseline": p95_total(baseline), "candidate": p95_total(candidate)},
        "rule": {"improves_by_one_item": improves, "faithfulness_lowered": lowered,
                 "kept": improves and not lowered},
    }


def technique_json(result: dict[str, Any]) -> str:
    """Stable json text for the committed results file."""
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def cell(r: dict[str, Any]) -> list[str]:
    """One table row of a metric comparison."""
    if not r.get("n"):
        return [r["metric"], "0", "n/a", "n/a", "n/a", "n/a", "n/a"]
    return [r["metric"], str(r["n"]), f"{r['baseline']:.2f}", f"{r['candidate']:.2f}",
            f"{r['difference']:+.3f}", f"[{r['low']:+.3f}, {r['high']:+.3f}]", r["verdict"]]


HEADER = ["metric", "items", "baseline", "candidate", "difference", "interval", "verdict"]


def technique_markdown(result: dict[str, Any]) -> str:
    """The report: headline counts, the rule, the overall table and one table per category."""
    s, rule = result["strict_pass"], result["rule"]
    tok, lat = result["tokens_billed"], result["p95_total_ms"]
    lines = [
        f"# {result['technique']} against the baseline, {result['split']} split", "",
        f"Candidate run {result['candidate_run']} (config {result['candidate_config']}), "
        f"baseline run {result['baseline_run']} (config {result['baseline_config']}). Paired on "
        f"{result['shared_items']} shared items. Difference is candidate minus baseline, "
        f"95 percent bootstrap interval, {RESAMPLES} resamples, seed {SEED}. "
        "A gap whose interval holds zero is no clear difference.", "",
        *[f"WARNING: {w}." for w in result["warnings"]],
        *([""] if result["warnings"] else []),
        f"Strict pass on answerable items: baseline {s['baseline']} of {s['answerable']}, "
        f"candidate {s['candidate']} of {s['answerable']}. "
        f"Gained: {', '.join(s['gained']) or 'none'}. Lost: {', '.join(s['lost']) or 'none'}.", "",
        "Rule for the final config: at least one item more than the baseline on the strict rate "
        f"({'met' if rule['improves_by_one_item'] else 'not met'}) and faithfulness not lowered "
        f"({'lowered' if rule['faithfulness_lowered'] else 'not lowered'}). Result: "
        f"{'kept' if rule['kept'] else 'not kept'}.", "",
        "Wrong abstains (answerable items declined): baseline "
        f"{result['wrong_abstain']['baseline']}, candidate {result['wrong_abstain']['candidate']}. "
        "Tokens billed: baseline "
        f"{fmt(tok['baseline'])}, candidate {fmt(tok['candidate'])}. p95 total latency over non "
        f"cached items, ms: baseline {fmt(lat['baseline'])}, "
        f"candidate {fmt(lat['candidate'])}.", "",
        "## Overall", "", *table(HEADER, [cell(r) for r in result["overall"]]), "",
    ]
    for c in result["categories"]:
        lines += [f"## {c['name']}", "", *table(HEADER, [cell(r) for r in c["rows"]]), ""]
    return "\n".join(lines)


def fmt(value: float | int | str | None) -> str:
    """A number, or the plain words for a value that was never recorded."""
    if isinstance(value, str):
        return value
    return "not recorded" if value is None else f"{value:.0f}"
