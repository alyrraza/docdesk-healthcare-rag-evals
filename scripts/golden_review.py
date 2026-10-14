"""Write a markdown review sheet for a golden batch, or apply the owner's decisions to it.

Usage:
    python scripts/golden_review.py evals/golden/batch1.yaml      write docs/golden_review/batch1.md
    python scripts/golden_review.py --apply docs/golden_review/batch1.md [--by ali]

In the sheet the owner writes OK, FIX: <note> or DROP after each item. Apply sets verified
true only for OK items; FIX and DROP items are listed and left in the file for you to act on.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from docdesk.evals.golden.loader import GoldenValidationError, count_found, read_file
from docdesk.evals.golden.review import SheetError, apply_decisions, parse_sheet, render_sheet

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ("openfda", "medlineplus")


def load_titles(corpus_root: Path) -> dict[str, str]:
    """Map each seed source key to its document title, read from the download manifests."""
    titles: dict[str, str] = {}
    for corpus in CORPORA:
        manifest = corpus_root / corpus / "manifest.json"
        if manifest.is_file():
            for source_id, entry in json.loads(manifest.read_text(encoding="utf-8")).items():
                titles[f"seed:{corpus}:{source_id}"] = entry["title"]
    return titles


def write_sheet(batch_file: Path, project_root: Path) -> int:
    """Validate this batch file's schema, then write its review sheet under docs/golden_review/."""
    mine, problems = read_file(batch_file)
    if problems or not mine:
        raise SystemExit("\n".join(problems) or f"no items found in {batch_file}")
    titles = load_titles(project_root / "data" / "corpus")
    target = project_root / "docs" / "golden_review" / f"{batch_file.stem}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shown = batch_file.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        shown = str(batch_file)
    target.write_text(render_sheet(mine, titles, shown), encoding="utf-8")
    print(f"wrote {target} ({len(mine)} items)")
    return 0


def apply_sheet(sheet_file: Path, by: str, project_root: Path) -> int:
    """Read the filled in sheet, update the batch file, and say what still needs work."""
    sheet = parse_sheet(sheet_file.read_text(encoding="utf-8"))
    batch = Path(sheet.batch_file)
    sheet = replace(sheet, batch_file=str(batch if batch.is_absolute() else project_root / batch))
    result = apply_decisions(sheet, by, date.today())
    print(f"verified: {', '.join(result.verified) or 'none'}")
    for item_id, note in result.fix:
        print(f"FIX {item_id}: {note}")
    for item_id in result.dropped:
        print(f"DROP {item_id}: still in the file, unverified; remove it or replace it")
    if result.undecided:
        print(f"undecided: {', '.join(result.undecided)}")
    items, problems = read_file(Path(sheet.batch_file))
    if problems:
        raise GoldenValidationError(problems)
    print(count_found(items).summary())
    return 0


def main(argv: list[str] | None = None, project_root: Path = ROOT) -> int:
    """Pick the mode from the arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, help="a batch YAML file, or a sheet with --apply")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--by", default="ali", help="name stored as verified_by")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            return apply_sheet(args.file, args.by, project_root)
        return write_sheet(args.file, project_root)
    except (SheetError, GoldenValidationError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    raise SystemExit(main())
