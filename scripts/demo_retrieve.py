"""Retrieve chunks for one question with the pinned B0 settings. No model call, no API key.

Usage (project root, a database filled by scripts/demo_seed.py):
    python scripts/demo_retrieve.py "How does rubella show up in someone who gets symptoms?"
    python scripts/demo_retrieve.py "<question>" --expect seed:medlineplus:medlineplus-387
With --expect the exit code is 1 unless that document is in the top results (used by CI).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from docdesk.core.config import get_settings
from docdesk.db.models.documents import DocumentRow
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.evals.config import load_eval_config
from docdesk.retrieval.retriever import retrieve

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "evals" / "configs" / "b0.toml"


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk reduced to what a person reads in a terminal."""

    source: str
    title: str
    score: float
    text: str


def expected_rank(hits: list[Hit], source: str) -> int | None:
    """Why: the CI smoke needs one yes or no on whether the known document came back."""
    return next((i for i, hit in enumerate(hits, start=1) if hit.source == source), None)


def format_hits(hits: list[Hit], snippet_chars: int = 110) -> list[str]:
    """Why: a stranger should see rank, score, document and a short quote, not a JSON blob."""
    return [
        f"{i}  {h.score:.3f}  {h.source}  {h.title}  {' '.join(h.text.split())[:snippet_chars]}"
        for i, h in enumerate(hits, start=1)
    ]


def main(question: str, expect: str | None) -> int:
    """Run the retrieval stages only and print the ranked chunks."""
    config = load_eval_config(CONFIG)
    settings = get_settings()
    encoder = Encoder.from_directory(Path(settings.model_dir))
    factory = make_session_factory(make_engine(settings.database_url))
    with factory() as session:
        result = retrieve(session, encoder, question, uuid.uuid4(), config.retrieval_config())
        sources = dict(session.execute(select(DocumentRow.id, DocumentRow.source)).all())
    hits = [Hit(sources[c.document_id], c.document_title, c.score, c.text) for c in result.chunks]
    print("\n".join(format_hits(hits)) or "no chunks found, run scripts/demo_seed.py first")
    if expect is None:
        return 0
    rank = expected_rank(hits, expect)
    print(f"expected {expect}: " + (f"found at rank {rank}" if rank else "NOT FOUND"))
    return 0 if rank else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--expect", help="source key of the document that must be in the results")
    args = parser.parse_args()
    sys.exit(main(args.question, args.expect))
