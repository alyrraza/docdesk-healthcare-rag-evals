"""Loads a pinned eval config and refuses it when its content no longer matches its hash."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docdesk.context.budget import ContextBudget
from docdesk.db.repositories.fingerprint import CorpusFingerprint
from docdesk.ingestion.pipeline import IngestConfig
from docdesk.llm.pacer import GROQ_FREE_LIMITS, ModelLimits
from docdesk.prompts.loader import PromptFile
from docdesk.retrieval.types import RetrievalConfig

# Every key a config may hold, and the code that reads it. A key not listed here is refused, so a
# config can never carry a setting that silently does nothing (review finding F3). A technique
# that needs a new key adds it here in the same change that reads it.
KNOWN_KEYS: dict[str, frozenset[str]] = {
    "id": frozenset(),
    "content_hash": frozenset(),
    "chunking": frozenset({"strategy", "size", "overlap"}),
    "embedding": frozenset({"model", "revision"}),
    "retrieval": frozenset({"mode", "top_n", "top_k", "rrf_k"}),
    "rerank": frozenset({"enabled"}),
    "packer": frozenset({"max_per_document"}),
    "budget": frozenset(
        {"total", "system", "schema", "evidence", "history", "question", "reserve"}
    ),
    "prompt": frozenset({"name", "version", "content_hash"}),
    "models": frozenset({"generator", "judge", "temperature", "max_output_tokens"}),
    "abstain": frozenset({"threshold"}),
    # Free form tables keyed by prompt name@version or by model id; read by judge_pins and
    # model_limits.
    "judge_prompts": frozenset(),
    "limits": frozenset(),
}
FREE_TABLES = ("judge_prompts", "limits")


class ConfigKeyError(ValueError):
    """The config holds a key no code reads, so it would change nothing."""


class UnsupportedConfig(ValueError):
    """The config asks for something that is not implemented; running it would be a silent no-op."""


class ConfigHashMismatch(ValueError):
    """The file was edited without a new hash; a baseline is never edited, only replaced."""


def content_hash(values: dict[str, Any]) -> str:
    """Hash of every value except the hash itself; key order and comments do not matter."""
    body = {key: value for key, value in values.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Groq free tier per model per day (evals.md, measured 2026-10-13). The guard stops at 85 percent.
DEFAULT_DAILY_TOKENS = 200_000

# The judge prompts this harness version was calibrated with. A config may override them in a
# [judge_prompts] table; an edit to a judge prompt file must become a new version and new pins.
DEFAULT_JUDGE_PINS = {
    "judge_faithfulness@2.0.0": "23b3fee6a584bfdc1ef6ef13cb8418907b3eaec1a2a6b417c956ceefc71534fc",
    "judge_correctness@2.0.0": "a49dd90ae421f479f7f2a58554064e302f7879b6ff75c0963f8232a7a9c2d631",
}


class PromptPinMismatch(ValueError):
    """The prompt in use is not the one the config pinned; a prompt edit must be a new version."""


@dataclass(frozen=True)
class EvalConfig:
    """Everything that shapes an eval result, with the id and hash stored beside each result."""

    id: str
    content_hash: str
    values: dict[str, Any]

    def retrieval_config(self) -> RetrievalConfig:
        """Build the retriever settings the pipeline understands from the pinned values."""
        section = self.values["retrieval"]
        return RetrievalConfig(
            mode=section["mode"],
            top_n=section["top_n"],
            top_k=section["top_k"],
            rrf_k=section["rrf_k"],
        )

    def ingest_config(self) -> IngestConfig:
        """Chunking settings the corpus must be built with for this config to be valid."""
        section = self.values["chunking"]
        return IngestConfig(
            chunker=section["strategy"], size=section["size"], overlap=section["overlap"]
        )

    def corpus_fingerprint(self) -> CorpusFingerprint:
        """What the database fingerprint must equal; the model string matches chunk rows."""
        chunking = self.ingest_config()
        model = self.values["embedding"]
        name = model["model"].rsplit("/", 1)[-1]
        return CorpusFingerprint(
            chunker=chunking.chunker,
            chunk_size=chunking.size,
            overlap=chunking.overlap,
            embedding_model=f"{name}@{model['revision']}",
        )

    def check_prompt(self, prompt: PromptFile) -> None:
        """Refuse a prompt other than the pinned one, so an edit cannot move a baseline."""
        pinned = self.values["prompt"]
        label = f"{prompt.name}@{prompt.version}"
        if (prompt.name, prompt.version) != (pinned["name"], pinned["version"]):
            raise PromptPinMismatch(
                f"{self.id} pins {pinned['name']}@{pinned['version']}, the active prompt is {label}"
            )
        if prompt.content_hash != pinned["content_hash"]:
            raise PromptPinMismatch(
                f"{label} no longer matches the hash pinned in {self.id}. "
                "Do not edit a pinned prompt: make a new version and a new config id."
            )

    def generation_params(self) -> dict[str, Any]:
        """The generator sampling settings this config sets; they reach every generator call."""
        models = self.values["models"]
        return {
            "temperature": models["temperature"],
            "max_output_tokens": models["max_output_tokens"],
        }

    def judge_pins(self) -> dict[str, str]:
        """Judge prompt name@version to content hash: the config's own table, else the default."""
        return dict(self.values.get("judge_prompts", DEFAULT_JUDGE_PINS))

    def model_limits(self, model: str) -> tuple[int, ModelLimits]:
        """Daily token limit and per minute limits of one model: the config's [limits] table for
        that model, else the Groq free tier defaults."""
        entry = self.values.get("limits", {}).get(model)
        if entry is None:
            return DEFAULT_DAILY_TOKENS, GROQ_FREE_LIMITS
        for key in ("daily_tokens", "tokens_per_minute", "requests_per_minute"):
            if key not in entry:
                raise ValueError(f"[limits] for {model} in {self.id} is missing {key}")
        return entry["daily_tokens"], ModelLimits(
            entry["tokens_per_minute"], entry["requests_per_minute"]
        )

    def context_budget(self) -> ContextBudget:
        """Build the token budget; ContextBudget itself checks that the slots add up."""
        return ContextBudget(**self.values["budget"])


def check_keys(values: dict[str, Any], name: str) -> None:
    """Refuse unknown keys and settings that are asked for but not implemented."""
    for key, value in values.items():
        if key not in KNOWN_KEYS:
            raise ConfigKeyError(f"{name}: unknown key {key!r}, no code reads it")
        if isinstance(value, dict) and key not in FREE_TABLES:
            unknown = sorted(set(value) - KNOWN_KEYS[key])
            if unknown:
                raise ConfigKeyError(f"{name}: unknown key {key}.{unknown[0]}, no code reads it")
    if values.get("rerank", {}).get("enabled"):
        raise UnsupportedConfig(
            f"{name}: rerank.enabled is true but no reranker is implemented (T109 is open)"
        )


def load_eval_config(path: Path) -> EvalConfig:
    """Read the file and check its hash, so a result can always name the exact config it used."""
    values = tomllib.loads(path.read_text(encoding="utf-8"))
    actual = content_hash(values)
    if values.get("content_hash") != actual:
        raise ConfigHashMismatch(
            f"{path.name} does not match its content_hash. If the change is intended, make a "
            f"new config id (b1, b2) with hash {actual}; never edit a frozen baseline."
        )
    check_keys(values, path.name)
    return EvalConfig(id=values["id"], content_hash=actual, values=values)


if __name__ == "__main__":
    # Prints the hash to paste into a new config file: python -m docdesk.evals.config FILE
    print(content_hash(tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
