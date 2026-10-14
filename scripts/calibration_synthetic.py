"""Build the synthetic calibration outputs from the natural calibration manifest (T099).

Usage:
    python scripts/calibration_synthetic.py [--seed N]
        writes evals/calibration/manifest_synthetic.yaml, never over an existing file
    python scripts/calibration_synthetic.py --sheet
        writes docs/calibration/sheet_synthetic.md (git ignored) from that manifest, same format
        as the natural sheet and blind: it never shows the perturbation type or a judge field

Dev runs only. The natural manifest and the natural sheet are only read. Deterministic: the same
seed, runs and corpus give the same set. The perturbation type is written to the manifest only.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select

from calibration_sheet import Source, db_chunks, db_runs
from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.db.session import default_session_factory
from docdesk.evals.calib_sample import SEED, Output, answer_hash, pool_from_runs
from docdesk.evals.calib_sheet import SheetEntry, render_sheet
from docdesk.evals.calib_synth import (
    Candidate,
    Parent,
    build_synthetic,
    drug_of,
    manifest_synthetic,
)
from docdesk.evals.golden.loader import read_items

ROOT = Path(__file__).resolve().parents[1]
NATURAL = Path("evals") / "calibration" / "manifest.yaml"
SYNTHETIC = Path("evals") / "calibration" / "manifest_synthetic.yaml"
SHEET = Path("docs") / "calibration" / "sheet_synthetic.md"


@dataclass(frozen=True)
class SynthSource(Source):
    """The natural sources plus the drug label chunks a sentence may be taken from."""

    candidates: Callable[[], list[Candidate]]


def db_candidates() -> list[Candidate]:
    """Chunks of ready openFDA drug labels, with the document key and the drug name."""
    query = select(ChunkRow.id, DocumentRow.source, DocumentRow.title, ChunkRow.text).join(
        DocumentRow, DocumentRow.id == ChunkRow.document_id
    ).where(DocumentRow.source.like("seed:openfda:%"), DocumentRow.title.like("% drug label"),
            DocumentRow.status == "ready")
    with default_session_factory()() as session:
        return [Candidate(str(r.id), r.source, drug_of(r.title), r.text)
                for r in session.execute(query)]


def natural_parents(manifest: dict, source: SynthSource, root: Path) -> list[Parent]:
    """Match each natural manifest entry to its stored output; a changed answer stops the build."""
    pool = {(o.run_id, o.item_id, o.answer_hash): o
            for o in pool_from_runs(source.runs(manifest["runs"]))}
    questions = {item.id: item.question for _, item in read_items(root / "evals" / "golden")[0]}
    parents = []
    for entry in manifest["outputs"]:
        output: Output | None = pool.get((entry["run_id"], entry["item_id"], entry["answer_hash"]))
        if output is None:
            raise SystemExit(f"{entry['item_id']} of run {entry['run_id']}: no stored output "
                             "matches the manifest hash, the run changed since sampling")
        titles = {drug_of(c.title) for c in source.chunks(list(output.used_ids))}
        parents.append(Parent(output, questions[output.item_id], entry["key_points"],
                              frozenset(titles)))
    return parents


def write_manifest(seed: int, root: Path, source: SynthSource, today: date) -> int:
    """Build the synthetic set and write its manifest; an existing manifest is kept."""
    target = root / SYNTHETIC
    if target.exists():
        raise SystemExit(f"{target} already exists; it is never overwritten")
    natural = yaml.safe_load((root / NATURAL).read_text(encoding="utf-8"))
    items = build_synthetic(natural_parents(natural, source, root), source.candidates(), seed=seed)
    manifest = manifest_synthetic(items, seed=seed, created=today)
    manifest["natural_manifest_seed"] = natural["seed"]
    target.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    counts = manifest["counts"]
    print(f"built {len(items)} synthetic outputs: {counts['insertion']} insertion, "
          f"{counts['omission']} omission")
    print(f"wrote {target}")
    return 0


def sheet_entries(manifest: dict, source: SynthSource, root: Path) -> list[SheetEntry]:
    """Show each synthetic answer with its parent's question, packed context and key points."""
    runs = sorted({o["parent_run_id"] for o in manifest["outputs"]})
    # One run at a time: pooling runs together drops a repeated answer from the later run, and
    # the parent is named by its own run.
    pool = {(o.run_id, o.item_id, o.answer_hash): o
            for run in source.runs(runs) for o in pool_from_runs([run])}
    items = {item.id: item for _, item in read_items(root / "evals" / "golden")[0]}
    entries = []
    for out in manifest["outputs"]:
        parent = pool.get((out["parent_run_id"], out["parent_item_id"], out["parent_answer_hash"]))
        if parent is None or answer_hash(out["answer"]) != out["answer_hash"]:
            raise SystemExit(f"{out['parent_item_id']}: the parent output or the manifest text "
                             "changed since the manifest was built")
        item = items[parent.item_id]
        shown = Output(parent.run_id, parent.item_id, parent.category, out["answer"],
                       parent.used_ids)
        points = list(item.gold_facts) if item.answerable else []
        entries.append(SheetEntry(out["n"], shown, item.question,
                                  source.chunks(list(parent.used_ids)), points))
    return entries


def write_sheet(root: Path, source: SynthSource) -> int:
    """Write the blind sheet in manifest order, which is already the seeded shuffle."""
    target, manifest_path = root / SHEET, root / SYNTHETIC
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} not found, build the manifest first")
    if target.exists():
        raise SystemExit(f"{target} already exists; it is never overwritten")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    entries = sheet_entries(manifest, source, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_sheet(entries), encoding="utf-8")
    print(f"wrote {target} ({len(entries)} outputs)")
    return 0


def main(
    argv: list[str] | None = None,
    project_root: Path = ROOT,
    source: SynthSource | None = None,
    today: date | None = None,
) -> int:
    """Read the arguments and write the synthetic manifest."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--sheet", action="store_true", help="write the blind sheet")
    args = parser.parse_args(argv)
    real = source or SynthSource(db_runs, db_chunks, db_candidates)
    if args.sheet:
        return write_sheet(project_root, real)
    return write_manifest(args.seed, project_root, real, today or date.today())


if __name__ == "__main__":
    raise SystemExit(main())
