"""The eval runner (T094): check, load, run each item once, write a row per item, finish."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals import run_store
from docdesk.evals.config import EvalConfig
from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.loader import (
    ResolvedItem,
    SplitLockedError,
    gold_sets,
    load_golden,
)
from docdesk.evals.identity import build_identity
from docdesk.evals.judges.kit import JudgeKit
from docdesk.evals.pipeline import Pipeline
from docdesk.evals.preflight import check_run_allowed
from docdesk.evals.scoring import score_item
from docdesk.prompts.bundle import BundleParts, bundle_id
from docdesk.prompts.loader import PromptFile

log = logging.getLogger(__name__)

NOT_RUN_FIXTURE = "not run, needs T122"
NOT_RUN_ROUTE = "not run, needs the router and SQL branch"
# error_code values that mean the provider call failed, not that the system answered badly.
PROVIDER_ERRORS = ("llm_timeout", "llm_rate_limited", "llm_error")


@dataclass(frozen=True)
class RunOptions:
    """How to run: dev by default, the test split only with allow_test."""

    split: Literal["dev", "test"] = "dev"
    allow_test: bool = False
    retrieval_only: bool = False
    git_sha: str = "unknown"
    # Run only these item ids (all must be verified items of the split); None runs the split.
    items: tuple[str, ...] | None = None
    # A name stored on the run, such as "smoke 3 items".
    label: str | None = None
    # Tests turn this off so their rows are rolled back with the test session.
    commit: bool = True


@dataclass
class RunSummary:
    """What a call to run_eval did, for the CLI to print."""

    run_id: uuid.UUID
    total: int
    ran: int = 0
    skipped_done: int = 0
    not_run: int = 0
    not_scored: int = 0
    finished: bool = False
    parse_failures: dict[str, list[str]] = field(default_factory=dict)


class UnknownItemsError(ValueError):
    """Raised when --items names an id that is not a verified item of the chosen split."""


def select_items(loaded: list[ResolvedItem], wanted: tuple[str, ...] | None) -> list[ResolvedItem]:
    """Keep the wanted ids, or all; an id the split does not have is refused, never skipped."""
    if wanted is None:
        return loaded
    missing = sorted(set(wanted) - {r.item.id for r in loaded})
    if missing:
        raise UnknownItemsError(
            f"not verified items of this split: {', '.join(missing)}"
        )
    return [r for r in loaded if r.item.id in wanted]


def not_run_reason(item: ResolvedItem) -> str | None:
    """Items this version cannot run yet, with the reason that goes in the row and the report."""
    if item.item.fixture_documents:
        return NOT_RUN_FIXTURE
    if item.item.gold_route != "documents":
        return NOT_RUN_ROUTE
    return None


def run_bundle_id(config: EvalConfig, prompt: PromptFile) -> str:
    """The prompt bundle id of a full run: the same recipe the live API traces use."""
    parts = BundleParts(
        prompt.name,
        prompt.version,
        prompt.content_hash,
        config.values["models"]["generator"],
        {**prompt.params, **config.generation_params()},
        prompt.schema,
        config.retrieval_config().config_id,
    )
    return bundle_id(parts)


def run_eval(
    *,
    config: EvalConfig,
    answer_prompt: PromptFile,
    session: Session,
    corpus: GoldenCorpus,
    golden_dir: Path,
    pipeline: Pipeline,
    kit: JudgeKit | None,
    options: RunOptions = RunOptions(),  # noqa: B008 frozen dataclass, safe as a default
) -> RunSummary:
    """Run the verified items of one split, skipping rows already written by an earlier attempt."""
    if options.split == "test" and not options.allow_test:
        raise SplitLockedError("the test split is for final reports only, pass allow_test=True")
    if kit is None and not options.retrieval_only:
        raise ValueError("a full run needs the judges; pass kit or use retrieval_only")
    check_run_allowed(config, answer_prompt, FingerprintRepository(session).read(), kit)
    loaded = load_golden(golden_dir, options.split, corpus, allow_test=options.allow_test)
    items = sorted(select_items(loaded, options.items), key=lambda resolved: resolved.item.id)
    bundle = None if options.retrieval_only else run_bundle_id(config, answer_prompt)
    run = run_store.open_run(
        session,
        config_id=config.id,
        bundle_id=bundle,
        split=options.split,
        git_sha=options.git_sha,
        label=options.label,
        identity=build_identity(config, kit, [r.item.id for r in items]),
    )
    done = run_store.written_item_ids(session, run.id)
    summary = RunSummary(run.id, total=len(items))
    meta = {
        "config_hash": config.content_hash,
        "judge_model": config.values["models"]["judge"],
        "judge_prompts": kit.prompt_hashes() if kit else {},
    }
    top_k = config.retrieval_config().top_k
    for resolved in items:
        item_id = resolved.item.id
        if item_id in done:
            summary.skipped_done += 1
            continue
        if reason := not_run_reason(resolved):
            metrics = {"status": "not_run", "reason": reason, "type": resolved.item.type}
            run_store.add_result(session, run.id, item_id, metrics, None, meta)
            summary.not_run += 1
        else:
            started = time.perf_counter()
            output = pipeline.run(resolved.item.question, retrieval_only=options.retrieval_only)
            if output.error_code in PROVIDER_ERRORS:
                metrics = {"status": "not_scored", "reason": output.error_code,
                           "type": resolved.item.type}
                run_store.add_result(session, run.id, item_id, metrics, None, meta)
                summary.not_scored += 1
                if options.commit:
                    session.commit()
                continue
            score = score_item(resolved, gold_sets(resolved, corpus), output, kit, top_k)
            trace = {**meta, **score.trace}
            label = score.failure_label
            total_ms = (time.perf_counter() - started) * 1000.0
            run_store.add_result(
                session, run.id, item_id, score.metrics, label, trace, score.usage,
                {**score.latency, "total_ms": total_ms},
            )
            summary.ran += 1
        if options.commit:
            session.commit()
    complete = run_store.written_item_ids(session, run.id)
    summary.finished = all(r.item.id in complete for r in items)
    if summary.finished:
        run_store.finish_run(session, run)
    if options.commit:
        session.commit()
    if kit is not None:
        stored = {r.item_id: r.metrics for r in run_store.results_of(session, run.id)}
        summary.parse_failures = run_store.parse_failed_items(stored)
    log.info("run %s: %s", run.id, summary)
    return summary
