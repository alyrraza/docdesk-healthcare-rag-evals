"""MedlinePlus fetcher: find the latest file, unpack it, keep English topics as plain text."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx
import pytest

from docdesk.ingestion.seed.common import SeedFetchError, load_manifest
from docdesk.ingestion.seed.medlineplus import (
    download_topics,
    download_zip,
    find_latest_zip_url,
    html_to_text,
    parse_topics,
    read_zip_xml,
    spread,
)

LONG = "Diabetes is a disease in which blood sugar is too high. " * 12


def topic(title: str, topic_id: int, language: str, html: str, also: tuple[str, ...] = ()) -> str:
    """One <health-topic> element, with the summary escaped the way MedlinePlus ships it."""
    escaped = html.replace("<", "&lt;").replace(">", "&gt;")
    nicknames = "".join(f"<also-called>{name}</also-called>" for name in also)
    url = f"https://medlineplus.gov/t{topic_id}.html"
    return (
        f'<health-topic title="{title}" url="{url}" id="{topic_id}" language="{language}">'
        f"{nicknames}<full-summary>{escaped}</full-summary></health-topic>"
    )


XML = (
    '<?xml version="1.0" encoding="UTF-8"?><health-topics total="3">'
    + topic(
        "Diabetes",
        1,
        "English",
        f'<p>{LONG}</p><ul><li>Eat well</li><li>Move <a href="x">daily</a></li></ul>',
        also=("Sugar disease", "DM"),
    )
    + topic("Diabetes ES", 2, "Spanish", f"<p>{LONG}</p>")
    + topic("Tiny", 3, "English", "<p>Too short.</p>")
    + "</health-topics>"
)

PAGE = """
<a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-10-09.zip">old</a>
<a href="https://medlineplus.gov/xml/mplus_topics_compressed_2026-10-13.zip">new</a>
<a href="https://medlineplus.gov/xml/mplus_topics_2026-10-13.xml">plain</a>
"""


def make_zip(xml: str = XML) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mplus_topics_2026-10-13.xml", xml)
    return buffer.getvalue()


def test_seed_html_becomes_plain_text_with_list_dashes_and_no_tags() -> None:
    text = html_to_text('<p>Hello <a href="x">there</a>.</p><ul><li>One</li><li>Two</li></ul>')
    assert text == "Hello there.\n\n- One\n- Two"


def test_seed_html_entities_are_decoded() -> None:
    assert html_to_text("<p>Fish &amp; chips &gt; 5%</p>") == "Fish & chips > 5%"


def test_seed_only_english_topics_with_enough_text_are_kept() -> None:
    topics = parse_topics(XML.encode())
    assert [t.title for t in topics] == ["Diabetes"]


def test_seed_a_topic_keeps_its_nicknames_source_line_and_list() -> None:
    topic = parse_topics(XML.encode())[0]
    assert topic.source_id == "medlineplus-1"
    assert topic.source_url == "https://medlineplus.gov/t1.html"
    assert "Also called: Sugar disease, DM" in topic.text
    assert "- Move daily" in topic.text
    assert "Source: MedlinePlus, National Library of Medicine" in topic.text


def test_seed_spread_picks_evenly_across_the_list() -> None:
    assert spread(list(range(10)), 5) == [0, 2, 4, 6, 8]
    assert spread(list(range(3)), 10) == [0, 1, 2]
    assert spread([], 5) == []


def test_seed_the_newest_compressed_file_is_chosen_from_the_page() -> None:
    assert find_latest_zip_url(PAGE).endswith("mplus_topics_compressed_2026-10-13.zip")


def test_seed_a_page_without_a_download_link_is_an_error() -> None:
    with pytest.raises(SeedFetchError, match="no compressed"):
        find_latest_zip_url("<html></html>")


def test_seed_the_xml_is_read_out_of_the_zip(tmp_path: Path) -> None:
    path = tmp_path / "t.zip"
    path.write_bytes(make_zip())
    assert b"<health-topics" in read_zip_xml(path)


def test_seed_the_zip_is_downloaded_once_and_reused(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=make_zip())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    path = download_zip(client, "https://x.test/a_2026.zip", tmp_path)
    again = download_zip(client, "https://x.test/a_2026.zip", tmp_path)
    assert path == again and path.is_file()
    assert len(calls) == 1


def test_seed_a_failed_download_leaves_no_partial_file(tmp_path: Path) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(SeedFetchError, match="503"):
        download_zip(client, "https://x.test/a_2026.zip", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_seed_download_topics_saves_documents_and_a_rerun_adds_none(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("xml.html"):
            return httpx.Response(200, text=PAGE)
        return httpx.Response(200, content=make_zip())

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://medlineplus.gov"
    )
    out, cache = tmp_path / "out", tmp_path / "cache"
    assert download_topics(client, out, cache, limit=10) == 1
    assert set(load_manifest(out)) == {"medlineplus-1"}
    assert download_topics(client, out, cache, limit=10) == 0
