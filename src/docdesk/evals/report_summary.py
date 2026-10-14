"""The machine readable summary of a run, built by code so nobody has to write it by hand (F7)."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from docdesk.evals.report_data import Report
from docdesk.evals.report_latency import latency_stats
from docdesk.evals.report_sections import answerable_records, stage_split, strict_pass_rate


def summary_of(report: Report) -> dict[str, Any]:
    """Counts and rates that other scripts read; nothing that depends on the time of day."""
    records = report.run.records
    strict = strict_pass_rate(records)
    split = stage_split(records)
    usage = None
    if report.model_usage is not None:
        usage = {u.model: {"calls": u.calls, "cached_calls": u.cached_calls,
                           "tokens_billed": u.tokens_billed, "tokens_saved": u.tokens_saved,
                           **({"billed_by_slot": {str(s): t for s, t in u.billed_by_slot.items()}}
                              if u.billed_by_slot else {})}
                 for u in report.model_usage}
    return {
        "run_id": report.run.run_id,
        "config": report.run.config_id,
        "split": report.run.split,
        "mode": report.run.mode,
        "identity_legacy": bool((report.run.identity or {}).get("legacy")),
        "items_ran": report.total_ok,
        "items_not_run": [item for item, _ in report.not_run],
        "items_not_scored": [item for item, _ in report.not_scored],
        "answerable_ran": len(answerable_records(records)),
        "answerable_pass_strict": strict.passed,
        "overall_passed": sum(1 for r in records
                              if r.metrics.get("status") == "ok" and r.metrics.get("passed")),
        "stage_split": split.counts,
        "answerable_labels": dict(sorted(Counter(
            r.failure_label for r in answerable_records(records) if r.failure_label).items())),
        "judge_failures": report.judge_failures,
        "tokens_by_model": usage,
        "latency_ms": {stage: {"n": s.n, "p50": round(s.p50, 1), "p95": round(s.p95, 1)}
                       for stage, s in latency_stats(records).items()} or None,
    }


def summary_json(report: Report) -> str:
    """Stable text: sorted keys, two spaces, one trailing newline."""
    return json.dumps(summary_of(report), indent=2, sort_keys=True) + "\n"
