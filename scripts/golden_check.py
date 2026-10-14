"""Check one golden batch file against the live corpus and print the duplicate evidence report.

Usage:
    python scripts/golden_check.py evals/golden/batch1_single_fact.yaml

It validates the schema, every source key and quote, the alternates, the duplicate evidence
rule and, for multi chunk items, that the quotes land in different chunks of the stored (B0)
chunking. Exit code 1 when anything fails. It uses DATABASE_URL and reads no provider.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docdesk.core.config import get_settings
from docdesk.db.session import make_engine, make_session_factory
from docdesk.evals.golden.corpus import DatabaseCorpus, GoldenCorpus
from docdesk.evals.golden.duplicates import CorpusScan
from docdesk.evals.golden.evidence import ChunkNotLocated, QuoteNotFound
from docdesk.evals.golden.loader import (
    ResolvedItem,
    check_distinct_chunks,
    read_file,
    resolve_item,
)
from docdesk.evals.golden.report import absence_report, duplicate_report
from docdesk.ingestion.filestore import LocalFileStore


def check_batch(batch_file: Path, corpus: GoldenCorpus) -> tuple[list[ResolvedItem], list[str]]:
    """Resolve every item of one file; return the good ones and one line per problem."""
    items, problems = read_file(batch_file)
    scan, texts, good = CorpusScan(corpus), {}, []
    for item in items:
        try:
            resolved = resolve_item(item, corpus, texts, scan)
            check_distinct_chunks(resolved, corpus)
        except (ValueError, QuoteNotFound, ChunkNotLocated) as error:
            problems.append(f"{item.id}: {error}")
        else:
            good.append(resolved)
    return good, problems


def main(argv: list[str] | None = None) -> int:
    """Print the report and the problems of one batch file."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    settings = get_settings()
    engine = make_engine(settings.database_url)
    with make_session_factory(engine)() as session:
        corpus = DatabaseCorpus(session, LocalFileStore(Path(settings.upload_dir)))
        good, problems = check_batch(args.file, corpus)
    print(duplicate_report(good))
    print(absence_report(good))
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(f"{len(good)} items passed, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
