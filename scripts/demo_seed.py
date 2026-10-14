"""Load the 20 document demo corpus so retrieval works in about a minute, without the full ingest.

Usage (project root, a migrated database; inside Docker: docker compose exec api python ...):
    python scripts/demo_seed.py
It creates the admin from ADMIN_EMAIL and ADMIN_PASSWORD, syncs the answer prompt, registers the
fixture corpus in evals/ci/corpus as shared documents and ingests it with the pinned B0 chunking.
Running it again changes nothing. It makes no model call and needs no provider key.
"""

from __future__ import annotations

from pathlib import Path

from docdesk.auth.seed import ensure_admin
from docdesk.core.config import get_settings
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.evals.config import load_eval_config
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.ingestion.seed.loader import ingest_all, register_corpus
from docdesk.prompts.registry import activate, sync_prompts

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "evals" / "configs" / "b0.toml"
CORPUS_DIR = ROOT / "evals" / "ci" / "corpus" / "medlineplus"


def main() -> None:
    """Why: a stranger needs a working retrieval in minutes, not after the 25 minute full ingest."""
    settings = get_settings()
    if not (settings.admin_email and settings.admin_password):
        raise SystemExit("Set ADMIN_EMAIL and ADMIN_PASSWORD, see python scripts/make_env.py")
    config = load_eval_config(CONFIG)
    model_dir = Path(settings.model_dir)
    encoder = Encoder.from_directory(model_dir)
    counter = TokenCounter.from_file(model_dir / "tokenizer.json")
    factory = make_session_factory(make_engine(settings.database_url))
    store = LocalFileStore(Path(settings.upload_dir))
    with factory() as session:
        admin, _ = ensure_admin(session, settings.admin_email, settings.admin_password)
        sync_prompts(session, ROOT / "prompts")
        activate(session, "answer", "1.0.0", admin.id)
        documents = register_corpus(session, store, [CORPUS_DIR], admin.id)
        session.commit()
    print(f"registered {len(documents)} new documents")
    if documents:
        summary = ingest_all(
            factory, store, encoder, counter, [d.id for d in documents], config.ingest_config()
        )
        if summary.failed:
            raise SystemExit(f"ingest failed for {len(summary.failed)} documents: {summary.failed}")
    print("demo corpus ready, try: python scripts/demo_retrieve.py \"<question>\"")


if __name__ == "__main__":
    main()
