"""The real wiring for the eval CLI: database, embedding model, Groq key, cache and guards.

Nothing here runs in the automated tests. The CLI tests pass fakes through `Runtime`.
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from docdesk.api.query_deps import build_counter, build_encoder, build_llm
from docdesk.core.config import get_settings
from docdesk.db.session import default_session_factory
from docdesk.evals.budget import TokenLedger
from docdesk.evals.cli import Runtime
from docdesk.evals.config import EvalConfig
from docdesk.evals.golden.corpus import DatabaseCorpus, GoldenCorpus
from docdesk.evals.judges.kit import JudgeKit, load_judge_kit
from docdesk.evals.live_pipeline import LivePipeline
from docdesk.evals.pipeline import Pipeline
from docdesk.evals.stack import build_llm_stack
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.llm.client import LLMClient
from docdesk.llm.pacer import GROQ_FREE_LIMITS, Pacer
from docdesk.prompts.loader import PromptFile

LEDGER_PATH = Path(".cache/ledger.json")
# Groq free tier, per model per day (evals.md, measured 2026-10-13). The guard stops at 85 percent.
GROQ_DAILY_TOKENS = 200_000


def git_sha() -> str:
    """The commit the run was made on, so a result can be tied to its code."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unknown"


_STACKS: dict[str, LLMClient] = {}


def llm_stack_for(config: EvalConfig) -> LLMClient:
    """Cache, budget guard, pacer, Groq client; one stack per run, so one pacer per key."""
    if config.id not in _STACKS:
        _STACKS[config.id] = new_stack(config)
    return _STACKS[config.id]


def new_stack(config: EvalConfig) -> LLMClient:
    """Build the layers around the real Groq client; the one place a real model is reached."""
    key = get_settings().groq_api_key
    if key is None or not key.get_secret_value():
        raise SystemExit("GROQ_API_KEY is missing in .env, a full run cannot call a model")
    models = {config.values["models"]["generator"], config.values["models"]["judge"]}
    ledger = TokenLedger(LEDGER_PATH, {model: GROQ_DAILY_TOKENS for model in models})
    pacer = Pacer({model: GROQ_FREE_LIMITS for model in models})
    return build_llm_stack(build_llm(key.get_secret_value()), ledger=ledger, pacer=pacer)


def pipeline_for(
    session: Session, config: EvalConfig, prompt: PromptFile, retrieval_only: bool
) -> Pipeline:
    """The live pipeline. A retrieval only run gets no model client at all."""
    settings = get_settings()
    return LivePipeline(
        session=session,
        encoder=build_encoder(settings.model_dir),
        counter=build_counter(settings.model_dir),
        llm=None if retrieval_only else llm_stack_for(config),
        prompt=prompt,
        config=config,
        # Any id works: retrieval is scoped to shared documents, which the seed corpus is.
        user_id=uuid.uuid4(),
    )


def judge_kit_for(config: EvalConfig) -> JudgeKit:
    """Judges read their model id from the pinned config."""
    return load_judge_kit(Path("prompts"), llm_stack_for(config), config.values["models"]["judge"])


def corpus_for(session: Session) -> GoldenCorpus:
    """The stored corpus, for resolving gold evidence."""
    return DatabaseCorpus(session, LocalFileStore(Path(get_settings().upload_dir)))


def default_runtime() -> Runtime:
    """The runtime used when the CLI is run from the command line."""
    return Runtime(
        open_session=default_session_factory(),
        corpus_for=corpus_for,
        pipeline_for=pipeline_for,
        judge_kit_for=judge_kit_for,
        git_sha=git_sha(),
    )
