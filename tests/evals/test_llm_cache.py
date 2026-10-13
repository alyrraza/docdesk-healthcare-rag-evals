"""The disk cache answers a repeated call from a file, with the original tokens and latency."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from docdesk.evals.cache import CachedClient, cache_key
from docdesk.llm.client import LLMRequest
from fakes.llm import FakeLLMClient

REQ = LLMRequest(system="be brief", user="what is aspirin", model="m")


def test_ac_evl_04_the_second_identical_call_is_served_from_disk(tmp_path: Path) -> None:
    inner = FakeLLMClient(["first answer"])
    client = CachedClient(inner, tmp_path)
    first = client.complete(REQ)
    second = client.complete(REQ)
    assert len(inner.requests) == 1
    assert (first.cache_hit, second.cache_hit) == (False, True)
    assert second.text == "first answer"


def test_ac_evl_04_a_cache_hit_keeps_the_original_tokens_latency_and_cost(tmp_path: Path) -> None:
    client = CachedClient(FakeLLMClient(["one two three"]), tmp_path)
    first = client.complete(REQ)
    second = client.complete(REQ)
    assert replace(second, cache_hit=False) == first


def test_ac_evl_04_the_cache_survives_a_new_client_object(tmp_path: Path) -> None:
    CachedClient(FakeLLMClient(["kept"]), tmp_path).complete(REQ)
    later = FakeLLMClient([])
    assert CachedClient(later, tmp_path).complete(REQ).text == "kept"
    assert later.requests == []


def test_ac_evl_04_every_part_of_the_input_changes_the_key() -> None:
    base = cache_key(REQ)
    changes = [
        replace(REQ, system="be long"),
        replace(REQ, user="what is ibuprofen"),
        replace(REQ, model="other"),
        replace(REQ, temperature=0.5),
        replace(REQ, max_output_tokens=10),
        replace(REQ, json_mode=False),
    ]
    keys = {cache_key(changed) for changed in changes}
    assert base not in keys
    assert len(keys) == len(changes)


def test_ac_evl_04_a_different_request_is_a_miss(tmp_path: Path) -> None:
    inner = FakeLLMClient(["a", "b"])
    client = CachedClient(inner, tmp_path)
    client.complete(REQ)
    client.complete(replace(REQ, user="another question"))
    assert len(inner.requests) == 2


def test_ac_evl_04_a_failed_call_is_not_cached(tmp_path: Path) -> None:
    inner = FakeLLMClient([RuntimeError("boom"), "recovered"])
    client = CachedClient(inner, tmp_path)
    try:
        client.complete(REQ)
    except RuntimeError:
        pass
    assert client.complete(REQ).text == "recovered"


def test_ac_evl_04_a_corrupt_entry_is_a_miss_and_is_replaced(tmp_path: Path) -> None:
    (tmp_path / f"{cache_key(REQ)}.json").write_text("{not json", encoding="utf-8")
    client = CachedClient(FakeLLMClient(["fresh"]), tmp_path)
    assert client.complete(REQ).text == "fresh"
    assert client.complete(REQ).cache_hit is True


def test_ac_evl_04_bypass_always_calls_the_model_and_leaves_the_cache_alone(
    tmp_path: Path,
) -> None:
    CachedClient(FakeLLMClient(["cached"]), tmp_path).complete(REQ)
    inner = FakeLLMClient(["live"])
    result = CachedClient(inner, tmp_path, bypass=True).complete(REQ)
    assert (result.text, result.cache_hit) == ("live", False)
    assert CachedClient(FakeLLMClient([]), tmp_path).complete(REQ).text == "cached"
