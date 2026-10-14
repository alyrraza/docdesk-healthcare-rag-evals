"""The check command (T096): validate everything a run depends on, and run nothing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import EvalConfig, load_eval_config
from docdesk.evals.golden.corpus import GoldenCorpus
from docdesk.evals.golden.loader import count_items, load_golden
from docdesk.evals.judges.kit import load_judge_prompts
from docdesk.evals.preflight import check_fingerprint
from docdesk.prompts.loader import PromptFile, load_prompt

# What a check can legitimately fail with. Anything else is a bug and should show its traceback.
EXPECTED_ERRORS = (ValueError, RuntimeError, OSError)


def answer_prompt_for(config: EvalConfig, prompts_dir: Path) -> PromptFile:
    """Load the answer prompt file the config pins, such as prompts/answer/answer.v1.md."""
    pinned = config.values["prompt"]
    major = str(pinned["version"]).split(".")[0]
    return load_prompt(prompts_dir / pinned["name"] / f"{pinned['name']}.v{major}.md")


def run_step(name: str, work: Callable[[], str]) -> bool:
    """Print OK or FAIL for one check; a failed check does not hide the next one."""
    try:
        print(f"OK   {name}: {work()}")
        return True
    except EXPECTED_ERRORS as error:
        print(f"FAIL {name}: {error}")
        return False


def check_all(
    config_path: Path,
    session: Session,
    corpus: GoldenCorpus,
    golden_dir: Path,
    prompts_dir: Path,
) -> int:
    """Config hash, corpus fingerprint, prompt hash, judge prompts and golden loading."""
    holder: list[EvalConfig] = []

    def load_config() -> str:
        holder.append(load_eval_config(config_path))
        return f"{holder[0].id}, hash matches"

    if not run_step("config", load_config):
        return 1
    config = holder[0]

    def fingerprint() -> str:
        check_fingerprint(config, FingerprintRepository(session).read())
        return "stored corpus matches the config"

    def answer_prompt() -> str:
        prompt = answer_prompt_for(config, prompts_dir)
        config.check_prompt(prompt)
        return f"{prompt.name}@{prompt.version}, hash matches"

    def judge_prompts() -> str:
        found = load_judge_prompts(prompts_dir)
        return ", ".join(f"{p.name}@{p.version} {p.content_hash[:8]}" for p in found)

    def golden() -> str:
        total = count_items(golden_dir)
        dev = load_golden(golden_dir, "dev", corpus)
        return f"{len(dev)} verified dev items load and resolve, {total.verified} verified in all"

    results = [
        run_step("fingerprint", fingerprint),
        run_step("answer prompt", answer_prompt),
        run_step("judge prompts", judge_prompts),
        run_step("golden", golden),
    ]
    return 0 if all(results) else 1
