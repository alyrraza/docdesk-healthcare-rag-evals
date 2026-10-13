"""MedlinePlus health topics: download the official compressed file once, keep English topics."""

from __future__ import annotations

import io
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

import httpx

from docdesk.ingestion.seed.common import (
    SeedDocument,
    SeedFetchError,
    load_manifest,
    save_document,
)

PAGE_PATH = "/xml.html"
ZIP_LINK = re.compile(
    r"https://medlineplus\.gov/xml/mplus_topics_compressed_(\d{4}-\d{2}-\d{2})\.zip"
)
MIN_BODY_CHARS = 400
BLOCK_TAGS = {"p", "ul", "ol", "h1", "h2", "h3", "h4", "br"}
SOURCE_LINE = "Source: MedlinePlus, National Library of Medicine"


class TextExtractor(HTMLParser):
    """Collects the visible text of a summary and marks paragraph and list item breaks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pieces: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Put a break before blocks and a dash before each list item."""
        if tag == "li":
            self.pieces.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.pieces.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        """Put a break after blocks so the next text starts on a new line."""
        if tag in BLOCK_TAGS:
            self.pieces.append("\n\n")

    def handle_data(self, data: str) -> None:
        """Keep text with its whitespace squeezed; line breaks come only from the tags."""
        self.pieces.append(" ".join(data.split()) + (" " if data[-1:].isspace() else ""))


def html_to_text(html: str) -> str:
    """Strip tags from a summary, keeping paragraphs and list items readable."""
    parser = TextExtractor()
    parser.feed(html)
    lines = (line.strip() for line in "".join(parser.pieces).split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_topics(xml_bytes: bytes) -> list[SeedDocument]:
    """Read English topics that have a real summary and turn each into a seed document."""
    documents = []
    for _, element in ElementTree.iterparse(io.BytesIO(xml_bytes)):
        if element.tag != "health-topic":
            continue
        if element.get("language") == "English":
            document = topic_to_document(element)
            if document is not None:
                documents.append(document)
        element.clear()
    return documents


def topic_to_document(element: ElementTree.Element) -> SeedDocument | None:
    """Build one document from a health-topic element, or None when its summary is too short."""
    body = html_to_text(element.findtext("full-summary") or "")
    if len(body) < MIN_BODY_CHARS:
        return None
    title, url = element.get("title", ""), element.get("url", "")
    nicknames = [node.text for node in element.findall("also-called") if node.text]
    parts = [title, body]
    if nicknames:
        parts.append("Also called: " + ", ".join(nicknames))
    parts.append(f"{SOURCE_LINE} ({url})")
    return SeedDocument(
        source_id=f"medlineplus-{element.get('id')}",
        title=title,
        text="\n\n".join(parts),
        source_url=url,
    )


def spread(items: list, limit: int) -> list:
    """Pick `limit` items evenly across the list, so a small sample still covers A to Z."""
    if len(items) <= limit:
        return list(items)
    step = len(items) / limit
    return [items[int(index * step)] for index in range(limit)]


def find_latest_zip_url(page_html: str) -> str:
    """Find the newest compressed topics file on the MedlinePlus download page."""
    dates = {match.group(1): match.group(0) for match in ZIP_LINK.finditer(page_html)}
    if not dates:
        raise SeedFetchError("no compressed topics file link found on the MedlinePlus page")
    return dates[max(dates)]


def download_zip(client: httpx.Client, url: str, directory: Path) -> Path:
    """Download the zip once; an existing file is reused and a failed download leaves nothing."""
    destination = directory / url.rsplit("/", 1)[-1]
    if destination.is_file():
        return destination
    directory.mkdir(parents=True, exist_ok=True)
    try:
        response = client.get(url)
    except httpx.HTTPError as error:
        raise SeedFetchError(f"could not download {url}: {error}") from error
    if response.status_code != 200:
        raise SeedFetchError(f"MedlinePlus returned HTTP {response.status_code} for {url}")
    partial = destination.with_suffix(".part")
    partial.write_bytes(response.content)
    partial.replace(destination)
    return destination


def read_zip_xml(path: Path) -> bytes:
    """Read the topics XML out of the downloaded zip without unpacking it to disk."""
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".xml")]
        if not names:
            raise SeedFetchError(f"no XML file inside {path.name}")
        return archive.read(names[0])


def download_topics(client: httpx.Client, out_dir: Path, cache_dir: Path, limit: int) -> int:
    """Save up to `limit` evenly spread topics as text files and return how many were new."""
    page = client.get(PAGE_PATH)
    if page.status_code != 200:
        raise SeedFetchError(f"MedlinePlus download page returned HTTP {page.status_code}")
    zip_path = download_zip(client, find_latest_zip_url(page.text), cache_dir)
    topics = sorted(parse_topics(read_zip_xml(zip_path)), key=lambda doc: doc.title)
    have = set(load_manifest(out_dir))
    new = [doc for doc in spread(topics, limit) if doc.source_id not in have]
    for document in new:
        save_document(out_dir, document)
    return len(new)
