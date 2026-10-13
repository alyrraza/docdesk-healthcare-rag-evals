"""Download one openFDA drug label per common drug into data/corpus/openfda (resumable).

Usage: python scripts/fetch_openfda.py [--limit N] [--out data/corpus/openfda]
No API key is needed; the script waits between requests to stay under openFDA's rate limit.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import httpx

from docdesk.ingestion.seed.common import ensure_download_dir
from docdesk.ingestion.seed.drug_names import COMMON_DRUGS
from docdesk.ingestion.seed.openfda import download_labels

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://api.fda.gov"
DELAY_SECONDS = 0.5


def main(
    argv: list[str] | None = None,
    project_root: Path = ROOT,
    client: httpx.Client | None = None,
    sleep=time.sleep,
) -> int:
    """Parse arguments, check the folder is allowed, then download; returns the new label count."""
    parser = argparse.ArgumentParser(description="Download openFDA drug labels.")
    parser.add_argument("--out", default="data/corpus/openfda")
    parser.add_argument("--limit", type=int, default=len(COMMON_DRUGS))
    args = parser.parse_args(argv)
    out_dir = ensure_download_dir(project_root / args.out, project_root)
    http = client or httpx.Client(base_url=BASE_URL, timeout=60)
    saved = download_labels(http, list(COMMON_DRUGS[: args.limit]), out_dir, sleep, DELAY_SECONDS)
    print(f"saved {saved} new labels in {out_dir}")
    return saved


if __name__ == "__main__":
    main()
