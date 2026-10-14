"""The CI retrieval gate (T101, AC-EVL-06). Makes no model call and never reads the test split.

Usage (project root, OPENBLAS_NUM_THREADS=1, a migrated and EMPTY database in DATABASE_URL):
    python scripts/ci_gate.py                    compare with evals/ci/expected.json
    python scripts/ci_gate.py --write-baseline   store the current numbers (a deliberate decision)
    python scripts/ci_gate.py --baseline FILE    compare with another file (the F12 failure proof)
This is a smoke test for retrieval pipeline regressions of one config (b0). It is not a quality
drift detector: it cannot see a changed prompt, a changed corpus or a slow decline inside the
tolerance.
It loads the small corpus in evals/ci/corpus, retrieves the golden subset in evals/ci/golden with
the pinned B0 retrieval settings, and builds the numbers with scripts/b0_summary.py. Wiring over
real services, so no automated test; the decision rule is tested in ci_gate_compare.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from b0_rows import collect_rows
from b0_summary import summarize
from ci_gate_compare import baseline_record, gate_numbers, gate_problems
from docdesk.core.config import get_settings
from docdesk.db.models.documents import DocumentRow
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.evals.config import EvalConfig, load_eval_config
from docdesk.evals.golden.corpus import DatabaseCorpus
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.ingestion.seed.loader import ingest_all, register_corpus

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "evals" / "configs" / "b0.toml"
CORPUS_DIR = ROOT / "evals" / "ci" / "corpus" / "medlineplus"
GOLDEN_DIR = ROOT / "evals" / "ci" / "golden"
EXPECTED = ROOT / "evals" / "ci" / "expected.json"
STORE_DIR = ROOT / ".cache" / "ci_gate_files"


def load_fixture(
    session: Session,
    factory: sessionmaker[Session],
    store: LocalFileStore,
    encoder: Encoder,
    counter: TokenCounter,
    config: EvalConfig,
) -> None:
    """Register the small corpus as shared documents and ingest it with the pinned chunking."""
    if session.execute(select(func.count()).select_from(DocumentRow)).scalar_one():
        raise SystemExit("the gate needs an empty database, this one already has documents")
    admin = UserRepository(session).add("ci-gate@example.invalid", "not-a-real-hash", "admin")
    session.commit()
    documents = register_corpus(session, store, [CORPUS_DIR], admin.id)
    summary = ingest_all(
        factory, store, encoder, counter, [d.id for d in documents], config.ingest_config()
    )
    if summary.failed:
        raise SystemExit(f"fixture ingest failed: {summary.failed}")


def main(write_baseline: bool, baseline: Path = EXPECTED) -> int:
    """Build the numbers on the fixture corpus, then store them or compare them."""
    config = load_eval_config(CONFIG)
    settings, model_dir = get_settings(), Path(get_settings().model_dir)
    encoder = Encoder.from_directory(model_dir)
    counter = TokenCounter.from_file(model_dir / "tokenizer.json")
    factory = make_session_factory(make_engine(settings.database_url))
    shutil.rmtree(STORE_DIR, ignore_errors=True)
    store = LocalFileStore(STORE_DIR)
    with factory() as session:
        load_fixture(session, factory, store, encoder, counter, config)
        rows = collect_rows(session, DatabaseCorpus(session, store), encoder, config, GOLDEN_DIR)
    summary = summarize(rows, config.retrieval_config().top_k)
    record = baseline_record(summary, config.id, config.content_hash)
    print(f"ran {len(rows)} items, numbers {gate_numbers(summary)}")
    if write_baseline:
        EXPECTED.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {EXPECTED.relative_to(ROOT)}")
        return 0
    stored = json.loads(baseline.read_text(encoding="utf-8"))
    problems = gate_problems(record, stored, config.id, config.content_hash)
    for problem in problems:
        print(f"GATE FAIL {problem}")
    print("gate failed" if problems else "gate passed")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--baseline", type=Path, default=EXPECTED, help="compare with this file")
    args = parser.parse_args()
    sys.exit(main(args.write_baseline, args.baseline))
