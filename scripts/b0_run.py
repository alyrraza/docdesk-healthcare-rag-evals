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
from pathlib import Path

from b0_render import render_markdown
from b0_rows import collect_rows
from b0_summary import summarize, worst_items
from docdesk.api.query_deps import build_encoder
from docdesk.core.config import get_settings
from docdesk.db.session import default_session_factory
from docdesk.evals.cli_runtime import corpus_for
from docdesk.evals.config import load_eval_config

CONFIG = Path("evals/configs/b0.toml")
GOLDEN = Path("evals/golden")


def main(out_dir: Path) -> None:
    """Retrieve every runnable verified dev item once and write the markdown and json."""
    config = load_eval_config(CONFIG)
    settings = config.retrieval_config()
    encoder = build_encoder(get_settings().model_dir)
    with default_session_factory()() as session:
        rows = collect_rows(session, corpus_for(session), encoder, config, GOLDEN)
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
