"""openFDA fetcher: record to text conversion and polite, resumable downloading."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from docdesk.ingestion.seed.common import SeedFetchError, load_manifest
from docdesk.ingestion.seed.openfda import (
    MAX_SECTION_CHARS,
    download_labels,
    fetch_label,
    label_to_document,
)


def record(set_id: str = "set-1", **sections: list[str]) -> dict:
    base = {
        "set_id": set_id,
        "openfda": {"brand_name": ["Bayer"], "generic_name": ["ASPIRIN"]},
        "indications_and_usage": ["Indicated for pain and fever."],
        "warnings": ["Reye's syndrome   in children.\n\nStomach bleeding."],
    }
    return {**base, **sections}


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.test")


def test_seed_a_label_becomes_titled_text_with_section_headings() -> None:
    document = label_to_document(record())
    assert document.source_id == "set-1"
    assert document.title == "Bayer (aspirin) drug label"
    assert "Indications and usage" in document.text
    assert "Indicated for pain and fever." in document.text
    assert "Reye's syndrome in children." in document.text


def test_seed_sections_the_label_lacks_are_left_out() -> None:
    text = label_to_document(record()).text
    assert "Contraindications" not in text


def test_seed_a_very_long_section_is_cut_to_the_cap() -> None:
    long = record(warnings=["word " * 10000])
    text = label_to_document(long).text
    assert len(text) < 2 * MAX_SECTION_CHARS + 500


def test_seed_a_label_with_no_usable_section_is_skipped() -> None:
    assert label_to_document({"set_id": "x", "openfda": {"generic_name": ["A"]}}) is None


def test_seed_the_title_falls_back_to_the_generic_name() -> None:
    bare = record()
    bare["openfda"] = {"generic_name": ["METFORMIN"]}
    assert label_to_document(bare).title == "metformin drug label"


def test_seed_fetch_label_asks_for_one_label_by_generic_name() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"results": [record()]})

    assert fetch_label(client_for(handler), "aspirin")["set_id"] == "set-1"
    assert 'openfda.generic_name:"aspirin"' in seen[0].params["search"]
    assert seen[0].params["limit"] == "1"


def test_seed_a_drug_openfda_does_not_know_is_none_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})

    assert fetch_label(client_for(handler), "nothingium") is None


def test_seed_a_server_error_stops_with_a_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(SeedFetchError, match="500"):
        fetch_label(client_for(handler), "aspirin")


def make_handler(calls: list[str], missing: set[str] = frozenset()):
    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.params["search"].split('"')[1]
        calls.append(name)
        if name in missing:
            return httpx.Response(404, json={})
        return httpx.Response(200, json={"results": [record(set_id=f"set-{name}")]})

    return handler


def test_seed_download_saves_each_label_and_waits_between_requests(tmp_path: Path) -> None:
    calls: list[str] = []
    pauses: list[float] = []
    saved = download_labels(
        client_for(make_handler(calls)), ["aspirin", "metformin"], tmp_path, pauses.append, 0.5
    )
    assert saved == 2
    assert set(load_manifest(tmp_path)) == {"set-aspirin", "set-metformin"}
    assert pauses == [0.5, 0.5]


def test_seed_a_second_run_does_not_fetch_labels_it_already_has(tmp_path: Path) -> None:
    first: list[str] = []
    download_labels(client_for(make_handler(first)), ["aspirin"], tmp_path, lambda _: None, 0)
    second: list[str] = []
    saved = download_labels(
        client_for(make_handler(second)), ["aspirin", "metformin"], tmp_path, lambda _: None, 0
    )
    assert second == ["metformin"]
    assert saved == 1


def test_seed_two_names_that_return_the_same_label_save_it_once(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [record(set_id="same")]})

    saved = download_labels(client_for(handler), ["a", "b"], tmp_path, lambda _: None, 0)
    assert saved == 1


def test_seed_unknown_drugs_are_skipped_and_the_rest_still_download(tmp_path: Path) -> None:
    saved = download_labels(
        client_for(make_handler([], missing={"nothingium"})),
        ["aspirin", "nothingium"],
        tmp_path,
        lambda _: None,
        0,
    )
    assert saved == 1
