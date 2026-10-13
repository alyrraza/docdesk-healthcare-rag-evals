"""Dependencies of POST /query that tests replace: model, encoder, token counter and prompt."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from docdesk.core.config import Settings, get_settings
from docdesk.core.errors import AppError
from docdesk.db.session import get_session
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.llm.providers.groq import GroqClient
from docdesk.llm.retry import RetryingClient
from docdesk.prompts.loader import PromptFile
from docdesk.prompts.registry import NoActivePromptError, get_active


@lru_cache
def build_llm(api_key: str) -> RetryingClient:
    """Build the real client once per key, so connections are reused between requests."""
    return RetryingClient(GroqClient(api_key))


def get_llm(settings: Settings = Depends(get_settings)) -> RetryingClient:
    """Give the route the real model client, or a clear 503 when no key is configured."""
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value():
        raise AppError("llm_not_configured", "No model is configured on this server", 503)
    return build_llm(settings.groq_api_key.get_secret_value())


@lru_cache
def build_encoder(model_dir: str) -> Encoder:
    """Load the ONNX model once; it takes seconds, so it must not happen per request."""
    return Encoder.from_directory(Path(model_dir))


def get_encoder(settings: Settings = Depends(get_settings)) -> Encoder:
    """Give the route the embedding model for the question."""
    return build_encoder(settings.model_dir)


@lru_cache
def build_counter(model_dir: str) -> TokenCounter:
    """Load the tokenizer once, for the context packer."""
    return TokenCounter.from_file(Path(model_dir) / "tokenizer.json")


def get_token_counter(settings: Settings = Depends(get_settings)) -> TokenCounter:
    """Give the route a token counter that matches the stored chunk sizes."""
    return build_counter(settings.model_dir)


def get_answer_prompt(session: Session = Depends(get_session)) -> PromptFile:
    """Give the route the live answer prompt; changing the pointer needs no deploy."""
    try:
        return get_active(session, "answer")
    except NoActivePromptError as error:
        raise AppError("prompt_not_active", "No answer prompt is active", 503) from error
