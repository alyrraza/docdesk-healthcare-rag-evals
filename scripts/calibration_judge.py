"""Judge the synthetic calibration outputs with the same two judges as the eval runner (T100).

Usage:
    python scripts/calibration_judge.py --check
        spends no tokens: rebuilds each parent's packed context and checks the judge call the
        original run made for it is in the cache, so the rebuilt context is the exact one
    python scripts/calibration_judge.py --run
        runs --check first and stops if it fails, then judges the 10 synthetic texts through the
        cache, budget guard, pacer and client, and writes
        evals/calibration/judge_results_synthetic.yaml

Dev runs only. Nothing is overwritten. A parse failure or provider error stops the run, a budget
stop exits 2 and a rerun continues, because finished calls are cached.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from calibration_synthetic import SYNTHETIC, SynthSource, sheet_entries
from docdesk.evals.budget import BudgetStop
from docdesk.evals.cache import DEFAULT_CACHE_DIR, CachedClient
from docdesk.evals.calib_judge import context_text, judge_synthetic
from docdesk.evals.calib_sample import pool_from_runs
from docdesk.evals.judges.faithfulness import judge_faithfulness
from docdesk.evals.judges.kit import JudgeKit, load_judge_kit
from docdesk.llm.client import LLMClient, LLMRequest, LLMResult

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path("evals") / "calibration" / "judge_results_synthetic.yaml"
CONFIG = Path("evals") / "configs" / "b0.toml"


class CacheMiss(Exception):
    """The call is not in the cache; the check client never calls a model."""


class CacheOnly:
    """The inner client of the check: any call that reaches it is a cache miss, never a request."""

    def complete(self, request: LLMRequest) -> LLMResult:
        """Why: the check must be able to spend nothing, even by mistake."""
        raise CacheMiss(request.model)


@dataclass(frozen=True)
class Wiring:
    """What the script needs from outside; tests pass fakes, the real one is built in `real()`."""

    source: SynthSource
    live_client: Callable[[], LLMClient]
    judge_model: str
    prompts_dir: Path = Path("prompts")
    cache_dir: Path = DEFAULT_CACHE_DIR


def real() -> Wiring:
    """The real database, config and call layers; the only place a provider key is read."""
    from calibration_sheet import db_chunks, db_runs
    from calibration_synthetic import db_candidates
    from docdesk.evals.cli_runtime import llm_stack_for
    from docdesk.evals.config import load_eval_config

    config = load_eval_config(ROOT / CONFIG)
    return Wiring(SynthSource(db_runs, db_chunks, db_candidates), lambda: llm_stack_for(config),
                  config.values["models"]["judge"])


def parent_records(manifest: dict, wiring: Wiring) -> list:
    """The stored rows of the parent runs, to compare the judge setup that produced them."""
    runs = sorted({o["parent_run_id"] for o in manifest["outputs"]})
    return [record for _, rows in wiring.source.runs(runs) for record in rows]


def check_judge_setup(manifest: dict, wiring: Wiring) -> None:
    """Stop if the judge model or prompts differ from those stored with the natural labels."""
    kit = load_judge_kit(wiring.prompts_dir, CachedClient(CacheOnly()), wiring.judge_model)
    expected = {"judge_model": kit.model, "judge_prompts": kit.prompt_hashes()}
    for record in parent_records(manifest, wiring):
        for field, value in expected.items():
            if record.trace.get(field) != value:
                raise SystemExit(f"{record.item_id}: stored {field} differs from the judge in use")


def context_misses(manifest: dict, wiring: Wiring, root: Path) -> list[str]:
    """Parents whose original faithfulness call is not in the cache under the rebuilt context."""
    client = CachedClient(CacheOnly(), wiring.cache_dir)
    kit = load_judge_kit(wiring.prompts_dir, client, wiring.judge_model)
    runs = sorted({o["parent_run_id"] for o in manifest["outputs"]})
    parents = {(o.run_id, o.item_id, o.answer_hash): o
               for run in wiring.source.runs(runs) for o in pool_from_runs([run])}
    misses = []
    entries = sheet_entries(manifest, wiring.source, root)
    for out, entry in zip(manifest["outputs"], entries, strict=True):
        parent = parents[(out["parent_run_id"], out["parent_item_id"], out["parent_answer_hash"])]
        try:
            judge_faithfulness(
                prompt=kit.faithfulness_prompt, parser=kit.faithfulness_parser, client=kit.client,
                model=kit.model, question=entry.question, answer=parent.answer,
                evidence=context_text(entry.context), answered=True)
        except CacheMiss:
            misses.append(f"{out['parent_item_id']} (run {out['parent_run_id'][:8]})")
    return misses


def check(manifest: dict, wiring: Wiring, root: Path) -> int:
    """Report whether every rebuilt context matches the one the original judge saw."""
    check_judge_setup(manifest, wiring)
    misses = context_misses(manifest, wiring, root)
    if misses:
        print("context check FAILED, no cached judge call for: " + ", ".join(misses))
        return 1
    print(f"context check passed for {len(manifest['outputs'])} parents, 0 tokens spent")
    return 0


def run(manifest: dict, wiring: Wiring, root: Path) -> int:
    """Judge every synthetic output and write the results file."""
    target = root / RESULTS
    if target.exists():
        raise SystemExit(f"{target} already exists; it is never overwritten")
    if check(manifest, wiring, root) != 0:
        raise SystemExit("stopped: the rebuilt context is not the one the original judge saw")
    entries = sheet_entries(manifest, wiring.source, root)
    kit: JudgeKit = load_judge_kit(wiring.prompts_dir, wiring.live_client(), wiring.judge_model)
    questions = {e.output.item_id: e.question for e in entries}
    facts = {e.output.item_id: e.key_points for e in entries}
    contexts = {o["synthetic_id"]: context_text(e.context)
                for o, e in zip(manifest["outputs"], entries, strict=True)}
    try:
        document = judge_synthetic(manifest, questions, facts, contexts, kit)
    except BudgetStop as stop:
        print(f"budget stop: {stop}. Rerun the same command later, finished calls are cached.")
        return 2
    target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    usage = [r["usage"] for r in document["results"]]
    print(f"wrote {target} ({len(usage)} outputs); tokens in {sum(u['tokens_in'] for u in usage)}, "
          f"tokens out {sum(u['tokens_out'] for u in usage)}, "
          f"cache hits {sum(u['cache_hits'] for u in usage)}")
    return 0


def main(
    argv: list[str] | None = None, project_root: Path = ROOT, wiring: Wiring | None = None
) -> int:
    """Pick check or run; exactly one is required so a spend is never an accident."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="spend no tokens, verify the context")
    mode.add_argument("--run", action="store_true", help="judge the synthetic outputs")
    args = parser.parse_args(argv)
    manifest = yaml.safe_load((project_root / SYNTHETIC).read_text(encoding="utf-8"))
    chosen = wiring or real()
    if args.check:
        return check(manifest, chosen, project_root)
    return run(manifest, chosen, project_root)


if __name__ == "__main__":
    raise SystemExit(main())
