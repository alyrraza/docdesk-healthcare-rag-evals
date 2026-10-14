"""LLM settings: model ids live in config, keys stay secret, generator and judge differ."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docdesk.core.config import Settings

BASE = {
    "database_url": "postgresql://owner:Vq8x2LmP4rTz@db.internal:5432/docdesk",
    "redis_url": "redis://localhost:6379/0",
    "jwt_secret": "f3a9c1d27b8e4a60915d2c7e8b4f1a36d0e9c5b7a2f84163",
}


def build(**overrides: str) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})


def test_ac_gen_01_the_default_models_are_two_different_families() -> None:
    settings = build()
    assert settings.generator_model == "openai/gpt-oss-120b"
    assert settings.judge_model == "qwen/qwen3.8-27b"
    assert settings.generator_model != settings.judge_model


def test_ac_gen_01_startup_fails_when_generator_and_judge_are_the_same_model() -> None:
    with pytest.raises(ValidationError, match="different models"):
        build(generator_model="openai/gpt-oss-120b", judge_model="openai/gpt-oss-120b")


@pytest.mark.parametrize("bad", ["openrouter/free", "google/gemma-4-31b-it", "some/model"])
def test_ac_gen_01_the_crosscheck_judge_must_be_a_free_model_and_never_the_router(
    bad: str,
) -> None:
    with pytest.raises(ValidationError, match=":free"):
        build(crosscheck_judge_model=bad)


def test_ac_gen_01_the_api_keys_are_optional_and_never_appear_in_repr() -> None:
    assert build().groq_api_key is None
    settings = build(groq_api_key="gsk_super_secret_value")
    assert "gsk_super_secret_value" not in repr(settings)
    assert settings.groq_api_key is not None
    assert settings.groq_api_key.get_secret_value() == "gsk_super_secret_value"


def test_ac_evl_pool_14_the_second_groq_key_is_an_optional_secret() -> None:
    assert build().groq_api_key_2 is None
    settings = build(groq_api_key_2="abc-second")
    assert settings.groq_api_key_2 is not None
    assert "abc-second" not in repr(settings)
    assert build(groq_api_key="one", groq_api_key_2="two").groq_api_keys == ["one", "two"]
