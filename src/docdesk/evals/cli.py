"""Command line for the eval harness: run, report, compare, check (T096).

python -m docdesk.evals.cli check
python -m docdesk.evals.cli run --retrieval-only        # no model call at all, safe for CI
python -m docdesk.evals.cli run                         # dev split, generator and judges
python -m docdesk.evals.cli report [RUN_ID] [--out FILE]
python -m docdesk.evals.cli compare BASELINE_RUN_ID CANDIDATE_RUN_ID
Exit codes: 0 done, 1 refused or failed, 2 stopped by the daily token guard (progress is saved).
"""

from __future__ import annotations

import argparse
import uuid
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from docdesk.evals.budget import BudgetStop
from docdesk.evals.cache import DEFAULT_CACHE_DIR
from docdesk.evals.cli_check import answer_prompt_for, check_all
from docdesk.evals.config import EvalConfig, PromptPinMismatch, load_eval_config
from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.loader import SplitLockedError
from docdesk.evals.judges.kit import JudgeKit
from docdesk.evals.pipeline import Pipeline
from docdesk.evals.preflight import FingerprintMismatch
from docdesk.evals.report import compare_markdown, report_markdown
from docdesk.evals.report_compare import compare_runs
from docdesk.evals.report_data import build_report, load_run_data
from docdesk.evals.report_usage import usage_from_cache
from docdesk.evals.run_store import latest_run_id
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.prompts.loader import PromptFile

REFUSALS = (SplitLockedError, FingerprintMismatch, PromptPinMismatch)


@dataclass
class Runtime:
    """Everything the commands need from outside, so tests can pass fakes."""

    open_session: Callable[[], AbstractContextManager[Session]]
    corpus_for: Callable[[Session], GoldenCorpus]
    pipeline_for: Callable[[Session, EvalConfig, PromptFile, bool], Pipeline]
    judge_kit_for: Callable[[EvalConfig], JudgeKit]
    golden_dir: Path = Path("evals/golden")
    prompts_dir: Path = Path("prompts")
    git_sha: str = "unknown"
    commit: bool = True
    # Where the cache entries are read back for the tokens per model table of the report.
    cache_dir: Path = DEFAULT_CACHE_DIR


def build_parser() -> argparse.ArgumentParser:
    """The four commands and their options."""
    parser = argparse.ArgumentParser(prog="docdesk.evals.cli", description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=Path("evals/configs/b0.toml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="validate config, fingerprint, prompts, golden set")
    run = commands.add_parser("run", help="run the verified items of one split")
    run.add_argument("--split", choices=("dev", "test"), default="dev")
    run.add_argument("--allow-test", action="store_true", help="needed for the test split")
    run.add_argument("--retrieval-only", action="store_true", help="no model calls at all")
    report = commands.add_parser("report", help="print the report of a run (default: the newest)")
    report.add_argument("run_id", nargs="?")
    report.add_argument("--out", type=Path)
    compare = commands.add_parser("compare", help="paired comparison of two runs")
    compare.add_argument("baseline")
    compare.add_argument("candidate")
    compare.add_argument("--out", type=Path)
    return parser


def cmd_run(rt: Runtime, args: argparse.Namespace) -> int:
    """Run one split. A refusal exits 1, a budget stop exits 2 with how to continue."""
    config = load_eval_config(args.config)
    prompt = answer_prompt_for(config, rt.prompts_dir)
    options = RunOptions(
        split=args.split,
        allow_test=args.allow_test,
        retrieval_only=args.retrieval_only,
        git_sha=rt.git_sha,
        commit=rt.commit,
    )
    with rt.open_session() as session:
        try:
            if args.split == "test" and not args.allow_test:
                raise SplitLockedError("the test split needs the --allow-test flag")
            kit = None if args.retrieval_only else rt.judge_kit_for(config)
            pipeline = rt.pipeline_for(session, config, prompt, args.retrieval_only)
            summary = run_eval(
                config=config,
                answer_prompt=prompt,
                session=session,
                corpus=rt.corpus_for(session),
                golden_dir=rt.golden_dir,
                pipeline=pipeline,
                kit=kit,
                options=options,
            )
        except BudgetStop as stop:
            print(stop)
            return 2
        except REFUSALS as refusal:
            print(f"refused: {refusal}")
            return 1
    print(
        f"run {summary.run_id}: ran {summary.ran}, skipped (already done) {summary.skipped_done}, "
        f"not run {summary.not_run}, of {summary.total} verified {args.split} items"
    )
    for judge, failures in summary.parse_failures.items():
        print(f"judge {judge}: {len(failures)} parse failures")
    return 0


def write_or_print(text: str, out: Path | None) -> None:
    """Print the markdown, or save it as utf-8 and say where."""
    if out is None:
        print(text)
    else:
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")


def cmd_report(rt: Runtime, args: argparse.Namespace) -> int:
    """Print the report of one run."""
    with rt.open_session() as session:
        run_id = uuid.UUID(args.run_id) if args.run_id else latest_run_id(session)
        report = build_report(load_run_data(session, run_id), usage_from_cache(rt.cache_dir))
        write_or_print(report_markdown(report), args.out)
    return 0


def cmd_compare(rt: Runtime, args: argparse.Namespace) -> int:
    """Print the paired comparison of two runs."""
    with rt.open_session() as session:
        baseline = load_run_data(session, uuid.UUID(args.baseline))
        candidate = load_run_data(session, uuid.UUID(args.candidate))
        write_or_print(compare_markdown(compare_runs(baseline, candidate)), args.out)
    return 0


def main(argv: Sequence[str] | None = None, runtime: Runtime | None = None) -> int:
    """Parse the arguments and run one command; the real runtime is built only when needed."""
    args = build_parser().parse_args(argv)
    if runtime is None:
        from docdesk.evals.cli_runtime import default_runtime

        runtime = default_runtime()
    if args.command == "check":
        with runtime.open_session() as session:
            return check_all(
                args.config, session, runtime.corpus_for(session),
                runtime.golden_dir, runtime.prompts_dir,
            )
    commands = {"run": cmd_run, "report": cmd_report, "compare": cmd_compare}
    return commands[args.command](runtime, args)


if __name__ == "__main__":
    raise SystemExit(main())
