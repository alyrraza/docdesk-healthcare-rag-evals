"""The openFDA download script refuses folders outside data/ and .cache/ (AC-ING-01)."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from fetch_openfda import main  # noqa: E402


def mock_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        record = {"set_id": "s1", "indications_and_usage": ["For pain."], "openfda": {}}
        return httpx.Response(200, json={"results": [record]})

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.test")


def test_fetch_script_the_script_downloads_into_a_data_folder(tmp_path: Path) -> None:
    saved = main(
        ["--limit", "1"], project_root=tmp_path, client=mock_client(), sleep=lambda _: None
    )
    assert saved == 1
    assert (tmp_path / "data" / "corpus" / "openfda" / "manifest.json").is_file()


def test_fetch_script_the_script_refuses_a_folder_outside_data_and_cache(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="data/ or .cache/"):
        main(["--out", "docs"], project_root=tmp_path, client=mock_client(), sleep=lambda _: None)
