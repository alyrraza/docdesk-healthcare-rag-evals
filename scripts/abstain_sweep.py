"""Write the T102a abstain threshold trade-off report. Dev split only, no model call.

Usage (project root, OPENBLAS_NUM_THREADS=1):
    python scripts/abstain_sweep.py [--out-dir evals/results]
Top-1 scores come from re-running B0 retrieval (scripts/b0_rows.py, dense, deterministic) and
outcomes from the stored B0 full dev run named in evals/results/b0_dev_summary.json. It reads the
database and changes nothing in it. Wiring over real services, so no automated test; the numbers
come from scripts/abstain_tradeoff.py, which is tested.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from abstain_tradeoff import Probe, build_report
from abstain_tradeoff_render import render_markdown
from b0_rows import collect_rows
from docdesk.api.query_deps import build_encoder
from docdesk.core.config import get_settings
from docdesk.db.models.evals import EvalResultRow
from docdesk.db.session import default_session_factory
from docdesk.evals.cli_runtime import corpus_for
from docdesk.evals.config import load_eval_config

CONFIG = Path("evals/configs/b0.toml")
GOLDEN = Path("evals/golden")
RESULTS = Path("evals/results")
KIND = {"single_fact": "answerable", "multi_chunk": "answerable",
        "unanswerable": "unanswerable", "adversarial": "adversarial"}


def main(out_dir: Path) -> None:
    """Pair each dev item's top-1 score with its stored B0 outcome, then write md and json."""
    summary = json.loads((RESULTS / "b0_dev_summary.json").read_text(encoding="utf-8"))
    config = load_eval_config(CONFIG)
    encoder = build_encoder(get_settings().model_dir)
    with default_session_factory()() as session:
        rows = collect_rows(session, corpus_for(session), encoder, config, GOLDEN)
        stored = {
            r.item_id: r.metrics.get("outcome")
            for r in session.execute(
                select(EvalResultRow).where(EvalResultRow.run_id == uuid.UUID(summary["run_id"]))
            ).scalars()
        }
    probes = [Probe(r.id, KIND[r.type], r.ranked[0].score, stored[r.id]) for r in rows]
    print(f"{len(probes)} items, stored B0 run {summary['run_id']}")
    reference = json.loads((RESULTS / "b0_retrieval_dev_summary.json").read_text(encoding="utf-8"))
    for item_type, spread in reference["top1_scores"].items():
        mine = [r.ranked[0].score for r in rows if r.type == item_type]
        same = (min(mine), max(mine)) == (spread["min"], spread["max"])
        print(f"top-1 range {item_type}: {'matches' if same else 'DIFFERS from'} the summary")
    report = build_report(probes)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "abstain_threshold_tradeoff.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "abstain_threshold_tradeoff.md").write_text(
        render_markdown(report), encoding="utf-8", newline="\n")
    print(f"wrote the report to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=RESULTS)
    main(parser.parse_args().out_dir)
