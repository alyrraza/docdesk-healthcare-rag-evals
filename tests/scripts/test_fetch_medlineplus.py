"""The MedlinePlus download script keeps every download under data/ or .cache/ (AC-ING-01)."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from fetch_medlineplus import main  # noqa: E402

BODY = "&lt;p&gt;" + "Asthma makes it hard to breathe. " * 20 + "&lt;/p&gt;"
XML = (
    '<health-topics><health-topic title="Asthma" url="u" id="9" language="English">'
    f"<full-summary>{BODY}</full-summary></health-topic></health-topics>"
)
PAGE = '<a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-10-13.zip">z</a>'


def mock_client() -> httpx.Client:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("topics.xml", XML)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("xml.html"):
            return httpx.Response(200, text=PAGE)
        return httpx.Response(200, content=buffer.getvalue())

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://medlineplus.gov")


def test_fetch_script_saves_topics_and_keeps_the_zip_in_the_cache(tmp_path: Path) -> None:
    assert main([], project_root=tmp_path, client=mock_client()) == 1
    assert (tmp_path / "data" / "corpus" / "medlineplus" / "manifest.json").is_file()
    assert list((tmp_path / ".cache" / "downloads" / "medlineplus").glob("*.zip"))


@pytest.mark.parametrize("flag", ["--out", "--cache"])
def test_fetch_script_the_script_refuses_folders_outside_data_and_cache(
    tmp_path: Path, flag: str
) -> None:
    with pytest.raises(ValueError, match="data/ or .cache/"):
        main([flag, "docs"], project_root=tmp_path, client=mock_client())
