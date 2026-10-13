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
from docdesk.prompts.loader import PromptFile
from docdesk.retrieval.types import RetrievalConfig


class ConfigHashMismatch(ValueError):
    """The file was edited without a new hash; a baseline is never edited, only replaced."""


def content_hash(values: dict[str, Any]) -> str:
    """Hash of every value except the hash itself; key order and comments do not matter."""
    body = {key: value for key, value in values.items() if key != "content_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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

    def context_budget(self) -> ContextBudget:
        """Build the token budget; ContextBudget itself checks that the slots add up."""
        return ContextBudget(**self.values["budget"])


def load_eval_config(path: Path) -> EvalConfig:
    """Read the file and check its hash, so a result can always name the exact config it used."""
    values = tomllib.loads(path.read_text(encoding="utf-8"))
    actual = content_hash(values)
    if values.get("content_hash") != actual:
        raise ConfigHashMismatch(
            f"{path.name} does not match its content_hash. If the change is intended, make a "
            f"new config id (b1, b2) with hash {actual}; never edit a frozen baseline."
        )
    return EvalConfig(id=values["id"], content_hash=actual, values=values)


if __name__ == "__main__":
    # Prints the hash to paste into a new config file: python -m docdesk.evals.config FILE
    print(content_hash(tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
