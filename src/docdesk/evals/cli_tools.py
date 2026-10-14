"""Extra commands of the eval CLI: rescore a stored run, check that a report file is fresh."""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from docdesk.db.models.evals import EvalResultRow
from docdesk.evals import run_store
from docdesk.evals.report import report_markdown
from docdesk.evals.report_data import build_report, load_run_data
from docdesk.evals.report_summary import summary_json
from docdesk.evals.rescore import rescored

if TYPE_CHECKING:  # cli imports this file, so the import is for type checkers only
    from docdesk.evals.cli import Runtime


def add_tool_parsers(commands: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register rescore and verify-report on the main parser."""
    rescore = commands.add_parser("rescore", help="apply the one pass rule to a stored run")
    rescore.add_argument("run_id")
    rescore.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    verify = commands.add_parser("verify-report", help="fail when a report file is stale")
    verify.add_argument("run_id")
    verify.add_argument("--report", type=Path, required=True)
    verify.add_argument("--summary", type=Path)


def stale(committed: str, fresh: str) -> bool:
    """Why: line endings differ between machines and must not make a report look stale."""
    return committed.replace("\r\n", "\n") != fresh.replace("\r\n", "\n")


def cmd_rescore(rt: Runtime, args: argparse.Namespace) -> int:
    """Re-apply the pass rule to stored rows; no model is called, a dry run writes nothing."""
    run_id = uuid.UUID(args.run_id)
    changed = 0
    with rt.open_session() as session:
        for row in run_store.results_of(session, run_id):
            new = rescored(row.metrics, row.failure_label, row.trace)
            if not new.changed:
                continue
            changed += 1
            print(f"{row.item_id}: {row.failure_label} -> {new.failure_label}")
            if args.apply:
                stored = session.get(EvalResultRow, (run_id, row.item_id))
                stored.metrics, stored.failure_label, stored.trace = (
                    new.metrics, new.failure_label, new.trace)
        if args.apply:
            session.commit()
    print(f"{changed} rows {'rescored' if args.apply else 'would change (dry run)'}")
    return 0


def cmd_verify_report(rt: Runtime, args: argparse.Namespace) -> int:
    """Regenerate the report (and summary) from the stored run and compare with the files."""
    with rt.open_session() as session:
        report = build_report(load_run_data(session, uuid.UUID(args.run_id)))
    pairs = [(args.report, report_markdown(report))]
    if args.summary is not None:
        pairs.append((args.summary, summary_json(report)))
    bad = [path for path, fresh in pairs
           if stale(path.read_text(encoding="utf-8"), fresh)]
    for path in bad:
        print(f"STALE {path}: differs from what the code regenerates from run {args.run_id}")
    print("reports are fresh" if not bad else f"{len(bad)} stale file(s)")
    return 1 if bad else 0
