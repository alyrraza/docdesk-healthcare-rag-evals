"""openFDA drug label fetcher: one label per common drug, kept as plain text sections."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import httpx

from docdesk.ingestion.seed.common import (
    SeedDocument,
    SeedFetchError,
    load_manifest,
    save_document,
)

logger = logging.getLogger(__name__)

LABEL_PATH = "/drug/label.json"
# Sections people actually ask about; the rest of a label is formatting and tables.
SECTIONS = (
    "boxed_warning",
    "indications_and_usage",
    "dosage_and_administration",
    "contraindications",
    "warnings",
    "warnings_and_cautions",
    "adverse_reactions",
    "drug_interactions",
    "description",
)
MAX_SECTION_CHARS = 8000


def clip(text: str) -> str:
    """Collapse whitespace and cut at the last space before the cap, so one section stays small."""
    flat = " ".join(text.split())
    if len(flat) <= MAX_SECTION_CHARS:
        return flat
    return flat[:MAX_SECTION_CHARS].rsplit(" ", 1)[0]


def label_title(record: dict) -> str:
    """Name the document by brand and generic name, which is how users will search."""
    names = record.get("openfda", {})
    generic = (names.get("generic_name") or ["unknown drug"])[0].lower()
    brand = (names.get("brand_name") or [""])[0]
    if brand and brand.lower() != generic:
        return f"{brand} ({generic}) drug label"
    return f"{generic} drug label"


def label_to_document(record: dict) -> SeedDocument | None:
    """Turn an openFDA record into text, or None when it has none of the sections we keep."""
    parts = []
    for key in SECTIONS:
        body = clip(" ".join(record.get(key) or []))
        if body:
            parts.append(f"{key.replace('_', ' ').capitalize()}\n{body}")
    if not parts:
        return None
    title = label_title(record)
    set_id = record["set_id"]
    return SeedDocument(
        source_id=set_id,
        title=title,
        text="\n\n".join([title, *parts]),
        source_url=f"https://api.fda.gov{LABEL_PATH}?search=set_id:{set_id}",
    )


def fetch_label(client: httpx.Client, generic_name: str) -> dict | None:
    """Ask openFDA for one label by generic name; None means openFDA has no such drug."""
    params = {"search": f'openfda.generic_name:"{generic_name}"', "limit": "1"}
    try:
        response = client.get(LABEL_PATH, params=params)
    except httpx.HTTPError as error:
        raise SeedFetchError(f"could not reach openFDA for {generic_name}: {error}") from error
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise SeedFetchError(f"openFDA returned HTTP {response.status_code} for {generic_name}")
    results = response.json().get("results") or []
    return results[0] if results else None


def download_labels(
    client: httpx.Client,
    names: list[str],
    out_dir: Path,
    sleep: Callable[[float], None],
    delay: float,
) -> int:
    """Save one label per name, skipping names already done, and return how many were new."""
    manifest = load_manifest(out_dir)
    done_queries = {entry.get("query") for entry in manifest.values()}
    have = set(manifest)
    saved = 0
    for name in names:
        if name in done_queries:
            continue
        record = fetch_label(client, name)
        sleep(delay)
        document = label_to_document(record) if record else None
        if document is None:
            logger.info("no usable openFDA label for %s", name)
            continue
        if document.source_id in have:
            continue
        save_document(out_dir, replace(document, query=name))
        have.add(document.source_id)
        saved += 1
    return saved
