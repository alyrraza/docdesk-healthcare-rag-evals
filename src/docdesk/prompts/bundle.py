"""The bundle id: one short id for everything that shapes a model's output (AC-PRM-03)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BundleParts:
    """Every input whose change can change an answer, so a trace can be tied to its exact setup."""

    prompt_name: str
    prompt_version: str
    prompt_hash: str
    model: str
    params: dict[str, Any]
    schema_version: str
    retrieval_config_id: str


def bundle_id(parts: BundleParts) -> str:
    """Hash the parts into 16 hex characters; sorted keys make the order of params irrelevant."""
    canonical = json.dumps(asdict(parts), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
