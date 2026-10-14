"""Scores one item: retrieval and citation metrics, the two judges, and the failure label."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from docdesk.evals.golden.loader import ResolvedItem
from docdesk.evals.judges.call import JudgeUsage
from docdesk.evals.judges.correctness import judge_correctness
from docdesk.evals.judges.faithfulness import judge_faithfulness
from docdesk.evals.judges.kit import JudgeKit
from docdesk.evals.labeler import LabelInput, label_failure
from docdesk.evals.metrics import retrieval as rm
from docdesk.evals.metrics.citation import citation_scores
from docdesk.evals.pipeline import PipelineOutput
from docdesk.llm.errors import LLMError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ItemScore:
    """What the runner stores for one item: small metrics, the label, and the full trace."""

    metrics: dict[str, Any]
    failure_label: str | None
    trace: dict[str, Any]


def retrieval_block(out: PipelineOutput, gold: list[frozenset[str]], k: int) -> dict[str, Any]:
    """The four retrieval metrics at k; None for items with no gold evidence."""
    return {
        "recall": rm.recall_at_k(out.retrieved_ids, gold, k),
        "hit": rm.hit_at_k(out.retrieved_ids, gold, k),
        "mrr": rm.reciprocal_rank(out.retrieved_ids, gold, k),
        "context_precision": rm.context_precision_at_k(out.retrieved_ids, gold, k),
    }


def attempt(ctx: dict[str, Any], name: str, item_id: str, call: Callable[[], Any]) -> None:
    """Run one judge; an LLM error is logged and recorded as that judge's status, not hidden."""
    try:
        ctx[name] = call()
    except LLMError as error:
        log.warning("judge %s failed for %s: %s", name, item_id, type(error).__name__)
        ctx[name] = None
        ctx[f"{name}_error"] = type(error).__name__


def run_judges(item: ResolvedItem, out: PipelineOutput, kit: JudgeKit, ctx: dict[str, Any]) -> None:
    """Call both judges for one item and put their results in ctx."""
    answered = out.outcome == "answered"
    question, item_id = item.item.question, item.item.id
    key_points = item.item.gold_facts if item.item.behavior == "answer" else []
    attempt(ctx, "faithfulness", item_id, lambda: judge_faithfulness(
        prompt=kit.faithfulness_prompt, parser=kit.faithfulness_parser, client=kit.client,
        model=kit.model, question=question, answer=out.answer, evidence=out.context,
        answered=answered))
    attempt(ctx, "correctness", item_id, lambda: judge_correctness(
        prompt=kit.correctness_prompt, parser=kit.correctness_parser, client=kit.client,
        model=kit.model, question=question, answer=out.answer, key_points=key_points,
        answered=answered))


def score_item(
    item: ResolvedItem,
    gold: list[frozenset[str]],
    out: PipelineOutput,
    kit: JudgeKit | None,
    top_k: int,
) -> ItemScore:
    """Build the metrics dict for one item; judges run only when a kit is given."""
    ctx: dict[str, Any] = {}
    if kit is not None and out.outcome is not None:
        run_judges(item, out, kit, ctx)
    faith, correct = ctx.get("faithfulness"), ctx.get("correctness")
    usage = [r.usage for r in (faith, correct) if r is not None]
    cites = citation_scores(out.cited_ids, gold)
    label = None
    if out.outcome is not None:
        label = label_failure(LabelInput(
            behavior=item.item.behavior, outcome=out.outcome, retrieval_ran=out.retrieval_ran,
            packed=out.packed, gold_sets=gold, candidate_ids=out.candidate_ids,
            retrieved_ids=out.retrieved_ids, used_ids=out.used_ids,
            faithfulness=faith.score if faith else None,
            correctness=correct.score if correct else None,
            contradicted=correct.contradicted if correct else 0))
    metrics: dict[str, Any] = {
        "status": "ok",
        "mode": "retrieval_only" if out.outcome is None else "full",
        "type": item.item.type,
        "behavior": item.item.behavior,
        "outcome": out.outcome,
        "group": item.evidence[0].source if item.evidence else item.item.id,
        **retrieval_block(out, gold, top_k),
        "citation_precision": cites.precision,
        "citation_recall": cites.recall,
        "faithfulness": faith.score if faith else None,
        "faithfulness_status": faith.status if faith else ctx.get("faithfulness_error"),
        "correctness": correct.score if correct else None,
        "correctness_status": correct.status if correct else ctx.get("correctness_error"),
        "contradicted": correct.contradicted if correct else 0,
        "passed": None if out.outcome is None else label is None,
        **totals(out, usage),
    }
    trace = {
        "answer": out.answer, "abstain_reason": out.abstain_reason,
        "retrieved_ids": out.retrieved_ids, "used_ids": out.used_ids, "cited_ids": out.cited_ids,
        "faithfulness_labels": [x.model_dump() for x in faith.labels] if faith else [],
        "correctness_labels": [x.model_dump() for x in correct.labels] if correct else [],
    }
    return ItemScore(metrics, label, trace)


def totals(out: PipelineOutput, judge_usage: list[JudgeUsage]) -> dict[str, Any]:
    """Tokens, cost and cache hits for the generator plus both judges."""
    cost = out.cost_usd + sum((u.cost_usd for u in judge_usage), Decimal("0"))
    return {
        "tokens_in": out.tokens_in + sum(u.tokens_in for u in judge_usage),
        "tokens_out": out.tokens_out + sum(u.tokens_out for u in judge_usage),
        "judge_tokens": sum(u.tokens_in + u.tokens_out for u in judge_usage),
        "cost_usd": str(cost),
        "cache_hits": out.cache_hits + sum(1 for u in judge_usage if u.cache_hit),
        "llm_calls": out.llm_calls + sum(u.calls for u in judge_usage),
    }
