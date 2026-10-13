"""Download MedlinePlus health topics into data/corpus/medlineplus (resumable).

Usage: python scripts/fetch_medlineplus.py [--limit N] [--out data/corpus/medlineplus]
Downloads the official compressed topics file (about 5 MB) into .cache/downloads once.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from docdesk.ingestion.seed.common import ensure_download_dir
from docdesk.ingestion.seed.medlineplus import download_topics

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://medlineplus.gov"


def main(
    argv: list[str] | None = None,
    project_root: Path = ROOT,
    client: httpx.Client | None = None,
) -> int:
    """Parse arguments, check both folders are allowed, then download; returns new topic count."""
    parser = argparse.ArgumentParser(description="Download MedlinePlus health topics.")
    parser.add_argument("--out", default="data/corpus/medlineplus")
    parser.add_argument("--cache", default=".cache/downloads/medlineplus")
    parser.add_argument("--limit", type=int, default=150)
    args = parser.parse_args(argv)
    out_dir = ensure_download_dir(project_root / args.out, project_root)
    cache_dir = ensure_download_dir(project_root / args.cache, project_root)
    http = client or httpx.Client(base_url=BASE_URL, timeout=120, follow_redirects=True)
    saved = download_topics(http, out_dir, cache_dir, args.limit)
    print(f"saved {saved} new topics in {out_dir}")
    return saved


if __name__ == "__main__":
    main()
