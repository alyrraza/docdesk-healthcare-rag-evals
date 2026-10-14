"""Write the T097 summary of B0 retrieval on the dev split. Makes no model call, never reads test.

Usage (from the project root, OPENBLAS_NUM_THREADS=1):
    python scripts/b0_run.py [--out-dir evals/results]
It retrieves the same way the eval run does (top_n candidates, then top_k) and keeps the scores.
Like evals/cli_runtime.py this is wiring over real services, so it has no automated test; the
numbers come from scripts/b0_summary.py, which is tested.
"""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import replace
from pathlib import Path

from b0_render import render_markdown
from b0_summary import Hit, ItemRow, summarize, worst_items
from docdesk.api.query_deps import build_encoder
from docdesk.core.config import get_settings
from docdesk.db.session import default_session_factory
from docdesk.evals.cli_runtime import corpus_for
from docdesk.evals.config import load_eval_config
from docdesk.evals.golden.loader import gold_sets, load_golden
from docdesk.evals.runner import not_run_reason
from docdesk.retrieval.retriever import retrieve

CONFIG = Path("evals/configs/b0.toml")
GOLDEN = Path("evals/golden")


def main(out_dir: Path) -> None:
    """Retrieve every runnable verified dev item once and write the markdown and json."""
    config = load_eval_config(CONFIG)
    settings = config.retrieval_config()
    wide = replace(settings, top_k=settings.top_n)
    encoder = build_encoder(get_settings().model_dir)
    rows: list[ItemRow] = []
    with default_session_factory()() as session:
        corpus = corpus_for(session)
        items = load_golden(GOLDEN, "dev", corpus)  # split is fixed to dev, no allow_test
        for resolved in sorted(items, key=lambda r: r.item.id):
            if not_run_reason(resolved):
                continue
            result = retrieve(session, encoder, resolved.item.question, uuid.uuid4(), wide)
            ranked = [Hit(str(c.chunk_id), c.document_title, c.score, c.text)
                      for c in result.chunks]
            rows.append(ItemRow(
                resolved.item.id, resolved.item.type, resolved.item.behavior,
                resolved.item.question, gold_sets(resolved, corpus),
                [f"{e.source}: {e.text}" for e in resolved.evidence], ranked,
                resolved.evidence[0].source if resolved.evidence else resolved.item.id,
            ))
    summary = summarize(rows, settings.top_k)
    worst = worst_items(rows, settings.top_k)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "b0_retrieval_dev_summary.md").write_text(
        render_markdown(summary, worst), encoding="utf-8")
    (out_dir / "b0_retrieval_dev_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"ran {len(rows)} items, wrote summary to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("evals/results"))
    main(parser.parse_args().out_dir)
