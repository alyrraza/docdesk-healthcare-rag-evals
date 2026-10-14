"""Build the blind judge calibration sheet from eval runs, or apply the owner's filled sheet.

Usage:
    python scripts/calibration_sheet.py --run RUN_ID --run RUN_ID [--size 40] [--seed N]
        writes evals/calibration/manifest.yaml and docs/calibration/sheet.md (git ignored)
        the first --run wins when two runs gave the same answer text for an item
    python scripts/calibration_sheet.py --apply docs/calibration/sheet.md [--by ali]
        checks the filled sheet is complete and writes evals/calibration/labels.yaml
    python scripts/calibration_sheet.py --apply docs/calibration/sheet_synthetic.md --synthetic
        the same check against manifest_synthetic.yaml, writes labels_synthetic.yaml

Dev runs only. The sheet shows the question, the answer, the packed context and the key points,
and never a judge label, score or pass flag. T100 compares the judge's labels with labels.yaml.
"""

from __future__ import annotations

import argparse
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.db.session import default_session_factory
from docdesk.evals.calib_labels import LabelError, apply_sheet, parse_sheet
from docdesk.evals.calib_sample import (
    SAMPLE_SIZE,
    SEED,
    Output,
    counts_by_category,
    pool_from_runs,
    sample_outputs,
)
from docdesk.evals.calib_sheet import ChunkView, SheetEntry, manifest_of, render_sheet
from docdesk.evals.golden.loader import read_items
from docdesk.evals.report_data import ResultRecord, load_run_data

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("evals") / "calibration" / "manifest.yaml"
LABELS = Path("evals") / "calibration" / "labels.yaml"
MANIFEST_SYNTHETIC = Path("evals") / "calibration" / "manifest_synthetic.yaml"
LABELS_SYNTHETIC = Path("evals") / "calibration" / "labels_synthetic.yaml"
SHEET = Path("docs") / "calibration" / "sheet.md"


@dataclass(frozen=True)
class Source:
    """Where the data comes from: stored runs and chunk texts. Tests pass fakes."""

    runs: Callable[[list[str]], list[tuple[str, list[ResultRecord]]]]
    chunks: Callable[[list[str]], list[ChunkView]]


def db_runs(run_ids: list[str]) -> list[tuple[str, list[ResultRecord]]]:
    """Read the stored rows of dev runs; a run of another split is refused."""
    found = []
    with default_session_factory()() as session:
        for run_id in run_ids:
            data = load_run_data(session, uuid.UUID(run_id))
            if data.split != "dev":
                raise SystemExit(f"run {run_id} is the {data.split} split, calibration uses dev")
            found.append((run_id, data.records))
    return found


def db_chunks(chunk_ids: list[str]) -> list[ChunkView]:
    """Title and text of the packed chunks in the order given; a missing chunk is an error."""
    with default_session_factory()() as session:
        query = select(ChunkRow.id, DocumentRow.title, ChunkRow.text).join(
            DocumentRow, DocumentRow.id == ChunkRow.document_id
        ).where(ChunkRow.id.in_([uuid.UUID(c) for c in chunk_ids]))
        found = {str(row.id): ChunkView(row.title, row.text) for row in session.execute(query)}
    missing = [c for c in chunk_ids if c not in found]
    if missing:
        raise SystemExit(f"chunks no longer in the database (re-ingested?): {', '.join(missing)}")
    return [found[c] for c in chunk_ids]


def entries_for(sample: list[Output], source: Source, root: Path) -> list[SheetEntry]:
    """Attach the question, key points and packed context to each sampled output."""
    items = {item.id: item for _, item in read_items(root / "evals" / "golden")[0]}
    entries = []
    for number, output in enumerate(sample, start=1):
        item = items.get(output.item_id)
        if item is None:
            raise SystemExit(f"{output.item_id} is not in the golden files")
        points = list(item.gold_facts) if item.answerable else []
        entries.append(SheetEntry(number, output, item.question,
                                  source.chunks(list(output.used_ids)), points))
    return entries


def write_sheet(args: argparse.Namespace, root: Path, source: Source, today: date) -> int:
    """Pool the runs, sample, and write the manifest and the sheet; never overwrite a sheet."""
    sheet_path, manifest_path = root / SHEET, root / MANIFEST
    if (sheet_path.exists() or manifest_path.exists()) and not args.force:
        raise SystemExit(f"{sheet_path} or {manifest_path} already exists; --force replaces both")
    pool = pool_from_runs(source.runs(args.run))
    sample = sample_outputs(pool, args.size, args.seed)
    entries = entries_for(sample.outputs, source, root)
    manifest = manifest_of(entries, seed=args.seed, pool_size=len(pool),
                           shortfall=sample.shortfall, created=today)
    manifest["runs"] = list(args.run)
    for path in (sheet_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    sheet_path.write_text(render_sheet(entries), encoding="utf-8")
    by_category = counts_by_category(sample.outputs)
    print(f"pool {len(pool)}, sample {len(entries)}, by category {by_category}")
    if sample.shortfall:
        print(f"WARNING: the pool is {sample.shortfall} outputs short of {args.size}")
    print(f"wrote {sheet_path} and {manifest_path}")
    return 0


def natural_view(synthetic_manifest: dict) -> dict:
    """Why: the synthetic manifest names the parent run and item, apply_sheet reads run and item."""
    outputs = [{**entry, "run_id": entry["parent_run_id"], "item_id": entry["parent_item_id"]}
               for entry in synthetic_manifest["outputs"]]
    return {**synthetic_manifest, "outputs": outputs}


def apply_filled(
    sheet_file: Path, by: str, root: Path, today: date, synthetic: bool = False
) -> int:
    """Validate the filled sheet against its manifest and write the labels; keep old labels."""
    labels_path = root / (LABELS_SYNTHETIC if synthetic else LABELS)
    if labels_path.exists():
        raise SystemExit(f"{labels_path} already exists; the original labels are never overwritten")
    manifest = yaml.safe_load(
        (root / (MANIFEST_SYNTHETIC if synthetic else MANIFEST)).read_text(encoding="utf-8"))
    if synthetic:
        manifest = natural_view(manifest)
    try:
        labels = apply_sheet(parse_sheet(sheet_file.read_text(encoding="utf-8")),
                             manifest, by=by, today=today)
    except LabelError as error:
        raise SystemExit(str(error)) from error
    if synthetic:
        ids = {entry["n"]: entry["synthetic_id"] for entry in manifest["outputs"]}
        labels["labels"] = [{"synthetic_id": ids[x["n"]], **x} for x in labels["labels"]]
    labels_path.write_text(yaml.safe_dump(labels, sort_keys=False), encoding="utf-8")
    print(f"wrote {labels_path} ({len(labels['labels'])} outputs, labeled by {by})")
    return 0


def main(
    argv: list[str] | None = None,
    project_root: Path = ROOT,
    source: Source | None = None,
    today: date | None = None,
) -> int:
    """Pick the mode from the arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="append", default=[], help="a dev run id, repeatable")
    parser.add_argument("--size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--force", action="store_true", help="replace an existing sheet")
    parser.add_argument("--apply", type=Path, help="the filled in sheet")
    parser.add_argument("--by", default="ali", help="name stored as labeled_by")
    parser.add_argument("--synthetic", action="store_true", help="apply the synthetic sheet")
    args = parser.parse_args(argv)
    day = today or date.today()
    if args.apply:
        return apply_filled(args.apply, args.by, project_root, day, args.synthetic)
    if not args.run:
        raise SystemExit("give at least one --run RUN_ID, or --apply SHEET")
    return write_sheet(args, project_root, source or Source(db_runs, db_chunks), day)


if __name__ == "__main__":
    raise SystemExit(main())
