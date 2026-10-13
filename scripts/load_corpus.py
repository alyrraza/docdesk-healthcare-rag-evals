"""Register the downloaded corpus as shared documents and ingest it (T052).

Usage:
    python scripts/load_corpus.py --dry-run     chunk and embed only, no database writes
    python scripts/load_corpus.py               write to DATABASE_URL (needs migrations and admin)

Run scripts/fetch_openfda.py and scripts/fetch_medlineplus.py first.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from docdesk.core.config import get_settings
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.ingestion.pipeline import IngestConfig
from docdesk.ingestion.seed.loader import dry_run, ingest_all, register_corpus

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIRS = [ROOT / "data" / "corpus" / "openfda", ROOT / "data" / "corpus" / "medlineplus"]


def report_dry_run(encoder: Encoder, counter: TokenCounter, config: IngestConfig) -> int:
    """Measure the corpus without any database and print the numbers worth knowing."""
    started = time.perf_counter()
    report = dry_run(CORPUS_DIRS, encoder, counter, config)
    seconds = time.perf_counter() - started
    average = report.tokens / report.chunks if report.chunks else 0
    print(f"documents {report.documents}, chunks {report.chunks}, tokens {report.tokens}")
    print(f"average chunk {average:.0f} tokens, longest {report.max_chunk_tokens}")
    print(
        f"chunk and embed time {seconds:.1f}s ({report.chunks / max(seconds, 1e-9):.0f} chunks/s)"
    )
    for name, reason in report.failed:
        print(f"FAILED {name}: {reason}")
    return 1 if report.failed else 0


def load_for_real(encoder: Encoder, counter: TokenCounter, config: IngestConfig) -> int:
    """Register and ingest the corpus into DATABASE_URL, owned by the admin and shared."""
    settings = get_settings()
    factory = make_session_factory(make_engine(settings.database_url))
    store = LocalFileStore(Path(settings.upload_dir))
    with factory() as session:
        admin = UserRepository(session).get_by_email(settings.admin_email or "")
        if admin is None:
            raise SystemExit(
                "Admin user not found: run scripts/seed_admin.py --database main first"
            )
        new_documents = register_corpus(session, store, CORPUS_DIRS, admin.id)
    print(f"registered {len(new_documents)} new documents")

    def progress(done: int, total: int) -> None:
        if done % 25 == 0 or done == total:
            print(f"ingested {done}/{total}")

    ids = [document.id for document in new_documents]
    summary = ingest_all(factory, store, encoder, counter, ids, config, progress)
    print(f"ready {summary.ready}, failed {len(summary.failed)}")
    for document_id, reason in summary.failed:
        print(f"FAILED {document_id}: {reason}")
    return 1 if summary.failed else 0


def main(argv: list[str] | None = None) -> int:
    """Load the models once, then run the dry run or the real load."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    model_dir = Path(get_settings().model_dir)
    encoder = Encoder.from_directory(model_dir)
    counter = TokenCounter.from_file(model_dir / "tokenizer.json")
    config = IngestConfig()
    if args.dry_run:
        return report_dry_run(encoder, counter, config)
    return load_for_real(encoder, counter, config)


if __name__ == "__main__":
    sys.exit(main())
