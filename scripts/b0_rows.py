"""Retrieve every runnable verified dev item once and keep the ranked chunks (T097, T101).

Shared by scripts/b0_run.py (the real corpus) and scripts/ci_gate.py (the small CI corpus), so
both build their numbers from the same rows and the same summary code. Wiring over a database
and an encoder, so it has no automated test of its own; the pure parts are tested in b0_summary.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from sqlalchemy.orm import Session

from b0_summary import Hit, ItemRow
from docdesk.evals.config import EvalConfig
from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.loader import gold_sets, load_golden
from docdesk.evals.runner import not_run_reason
from docdesk.retrieval.retriever import QueryEncoder, retrieve


def collect_rows(
    session: Session,
    corpus: GoldenCorpus,
    encoder: QueryEncoder,
    config: EvalConfig,
    golden_dir: Path,
) -> list[ItemRow]:
    """Why: one place turns golden items into ranked rows, and the split is fixed to dev."""
    settings = config.retrieval_config()
    wide = replace(settings, top_k=settings.top_n)
    rows: list[ItemRow] = []
    items = load_golden(golden_dir, "dev", corpus)  # no allow_test, the test split stays locked
    for resolved in sorted(items, key=lambda r: r.item.id):
        if not_run_reason(resolved):
            continue
        result = retrieve(session, encoder, resolved.item.question, uuid.uuid4(), wide)
        ranked = [Hit(str(c.chunk_id), c.document_title, c.score, c.text) for c in result.chunks]
        rows.append(ItemRow(
            resolved.item.id, resolved.item.type, resolved.item.behavior,
            resolved.item.question, gold_sets(resolved, corpus),
            [f"{e.source}: {e.text}" for e in resolved.evidence], ranked,
            resolved.evidence[0].source if resolved.evidence else resolved.item.id,
        ))
    return rows
