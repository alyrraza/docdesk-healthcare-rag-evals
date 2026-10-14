"""Run the two judges on the synthetic calibration outputs, as the eval runner does (T100).

The synthetic texts are in no run, so their judge labels do not exist yet. They are made with the
same prompts, parsers and judge model as the runner, against the context of the parent item.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from docdesk.evals.calib_sheet import ChunkView
from docdesk.evals.judges.call import JudgeUsage
from docdesk.evals.judges.correctness import judge_correctness
from docdesk.evals.judges.faithfulness import judge_faithfulness
from docdesk.evals.judges.kit import JudgeKit

FAITHFULNESS_OK = ("scored", "no_claims")


class JudgeRunError(RuntimeError):
    """A judge reply could not be used; the run stops instead of guessing a label."""


def context_text(chunks: Sequence[ChunkView]) -> str:
    """Why: the judge must see the context in the format the runner gave it (live_pipeline)."""
    return "\n\n".join(f"[c{n}] {chunk.title}\n{chunk.text}" for n, chunk in enumerate(chunks, 1))


def usage_total(*usages: JudgeUsage) -> dict[str, Any]:
    """Tokens, cost and cache hits of the calls made for one output."""
    return {
        "calls": sum(u.calls for u in usages),
        "tokens_in": sum(u.tokens_in for u in usages),
        "tokens_out": sum(u.tokens_out for u in usages),
        "cost_usd": str(sum((u.cost_usd for u in usages), Decimal("0"))),
        "cache_hits": sum(1 for u in usages if u.cache_hit),
    }


def judge_one(
    entry: Mapping[str, Any], question: str, facts: Sequence[str], context: str, kit: JudgeKit
) -> dict[str, Any]:
    """Both judges on one synthetic output; anything but a usable verdict raises."""
    name = entry["synthetic_id"]
    faith = judge_faithfulness(
        prompt=kit.faithfulness_prompt, parser=kit.faithfulness_parser, client=kit.client,
        model=kit.model, question=question, answer=entry["answer"], evidence=context,
        answered=True)
    if faith.status not in FAITHFULNESS_OK:
        raise JudgeRunError(f"{name}: faithfulness judge {faith.status}")
    correct = judge_correctness(
        prompt=kit.correctness_prompt, parser=kit.correctness_parser, client=kit.client,
        model=kit.model, question=question, answer=entry["answer"], key_points=facts,
        answered=True)
    if correct.status != "scored":
        raise JudgeRunError(f"{name}: correctness judge {correct.status}")
    return {
        "synthetic_id": name, "n": entry["n"], "parent_item_id": entry["parent_item_id"],
        "answer_hash": entry["answer_hash"],
        "faithfulness": {"status": faith.status, "score": faith.score,
                         "claims": [label.model_dump() for label in faith.labels]},
        "correctness": {"status": correct.status, "score": correct.score,
                        "key_points": [label.model_dump() for label in correct.labels]},
        "usage": usage_total(faith.usage, correct.usage),
    }


def judge_synthetic(
    manifest: Mapping[str, Any], questions: Mapping[str, str], facts: Mapping[str, Sequence[str]],
    contexts: Mapping[str, str], kit: JudgeKit,
) -> dict[str, Any]:
    """The results document for every synthetic output; nothing is returned if one fails."""
    results = []
    for entry in manifest["outputs"]:
        item_id = entry["parent_item_id"]
        results.append(judge_one(entry, questions[item_id], facts[item_id],
                                 contexts[entry["synthetic_id"]], kit))
    return {"judge_model": kit.model, "prompts": kit.prompt_hashes(), "results": results}
