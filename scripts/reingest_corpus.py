"""Rebuild the seed corpus in DATABASE_URL with the chunking config of an eval config (T080a).

Usage:
    python scripts/reingest_corpus.py                   uses evals/configs/b0.toml
    python scripts/reingest_corpus.py --config FILE

It deletes the seed documents and their chunks, then runs the normal register and ingest steps
(duplicate detection stays on), then writes the corpus fingerprint. Uploaded documents are kept.
It refuses to run against a database whose name ends in _test.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from docdesk.core.config import get_settings
from docdesk.db.models.chunks import ChunkRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.evals.config import load_eval_config
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.ingestion.seed.loader import ingest_all, register_corpus
from docdesk.ingestion.seed.reset import clear_seed_corpus
from load_corpus import CORPUS_DIRS, ROOT

DEFAULT_CONFIG = ROOT / "evals" / "configs" / "b0.toml"


def chunk_total(session: Session) -> int:
    """Count every chunk in the database, including those of uploaded documents."""
    return session.execute(select(func.count()).select_from(ChunkRow)).scalar_one()


def main(argv: list[str] | None = None) -> int:
    """Clear, re-ingest with the config, store the fingerprint, and print the numbers."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    settings = get_settings()
    if (make_url(settings.database_url).database or "").endswith("_test"):
        raise SystemExit("Refusing to run: DATABASE_URL points at a test database")
    config = load_eval_config(args.config)
    ingest = config.ingest_config()
    model_dir = Path(settings.model_dir)
    encoder = Encoder.from_directory(model_dir)
    counter = TokenCounter.from_file(model_dir / "tokenizer.json")
    expected = config.corpus_fingerprint()
    actual = f"{encoder.model_name}@{encoder.revision}"
    if actual != expected.embedding_model:
        raise SystemExit(
            f"Encoder is {actual}, config {config.id} needs {expected.embedding_model}"
        )

    factory = make_session_factory(make_engine(settings.database_url))
    store = LocalFileStore(Path(settings.upload_dir))
    started = time.perf_counter()
    with factory() as session:
        admin = UserRepository(session).get_by_email(settings.admin_email or "")
        if admin is None:
            raise SystemExit("Admin user not found: run scripts/seed_admin.py --database main")
        before = chunk_total(session)
        cleared = clear_seed_corpus(session)
        session.commit()
        print(f"before: {cleared.documents} seed documents, {cleared.chunks} seed chunks")
        new_documents = register_corpus(session, store, CORPUS_DIRS, admin.id)
    ids = [document.id for document in new_documents]
    summary = ingest_all(factory, store, encoder, counter, ids, ingest)
    with factory() as session:
        after = chunk_total(session)
        if not summary.failed:
            FingerprintRepository(session).write(expected)
            session.commit()
    seconds = time.perf_counter() - started
    print(f"chunks in database: {before} before, {after} after ({ingest.chunker}, {ingest.size})")
    print(f"ready {summary.ready}, failed {len(summary.failed)}, took {seconds:.0f}s")
    for document_id, reason in summary.failed:
        print(f"FAILED {document_id}: {reason}")
    return 1 if summary.failed else 0


if __name__ == "__main__":
    sys.exit(main())
