"""Write a markdown review sheet for a golden batch, or apply the owner's decisions to it.

Usage:
    python scripts/golden_review.py evals/golden/batch1.yaml      write docs/golden_review/batch1.md
    python scripts/golden_review.py FILE --only gi-003,gi-005 --name batch1_changed
                                        a sheet for chosen items only, under another name
    python scripts/golden_review.py FILE --probe
                                        also show the top 3 dense and keyword chunks (B0) of each
                                        item without an answer; needs the database and the model
    python scripts/golden_review.py --apply docs/golden_review/batch1.md [--by ali]

In the sheet the owner writes OK, FIX: <note> or DROP after each item. Apply sets verified
true only for OK items; FIX and DROP items are listed and left in the file for you to act on.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from pathlib import Path

from docdesk.core.config import get_settings
from docdesk.db.repositories.fingerprint import FingerprintRepository, differences
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.evals.config import load_eval_config
from docdesk.evals.golden.loader import GoldenValidationError, count_found, read_file
from docdesk.evals.golden.probe import Probe, probe_question
from docdesk.evals.golden.review import SheetError, apply_decisions, parse_sheet, render_sheet
from docdesk.evals.golden.schema import GoldenItem

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ("openfda", "medlineplus")
B0_CONFIG = ROOT / "evals" / "configs" / "b0.toml"
ProbeBuilder = Callable[[list[GoldenItem]], dict[str, Probe]]


def load_titles(corpus_root: Path) -> dict[str, str]:
    """Map each seed source key to its document title, read from the download manifests."""
    titles: dict[str, str] = {}
    for corpus in CORPORA:
        manifest = corpus_root / corpus / "manifest.json"
        if manifest.is_file():
            for source_id, entry in json.loads(manifest.read_text(encoding="utf-8")).items():
                titles[f"seed:{corpus}:{source_id}"] = entry["title"]
    return titles


def pick_items(mine: list[GoldenItem], only: str | None) -> list[GoldenItem]:
    """Keep the requested ids, in the order asked; an id that is not in the file is an error."""
    if only is None:
        return mine
    wanted = [item_id.strip() for item_id in only.split(",") if item_id.strip()]
    by_id = {item.id: item for item in mine}
    missing = [item_id for item_id in wanted if item_id not in by_id]
    if missing:
        raise SystemExit(f"--only names items that are not in the batch file: {', '.join(missing)}")
    return [by_id[item_id] for item_id in wanted]


def build_probes(items: list[GoldenItem]) -> dict[str, Probe]:
    """Run each question through B0 dense and keyword search on the live corpus."""
    settings = get_settings()
    config = load_eval_config(B0_CONFIG)
    encoder = Encoder.from_directory(Path(settings.model_dir))
    with make_session_factory(make_engine(settings.database_url))() as session:
        stored = FingerprintRepository(session).read()
        if stored is None or differences(stored, config.corpus_fingerprint()):
            raise SystemExit("The corpus does not match b0: run scripts/reingest_corpus.py first")
        admin = UserRepository(session).get_by_email(settings.admin_email or "")
        if admin is None:
            raise SystemExit("Admin user not found: run scripts/seed_admin.py --database main")
        return {
            item.id: probe_question(session, encoder, item.question, admin.id) for item in items
        }


def write_sheet(
    batch_file: Path,
    project_root: Path,
    only: str | None = None,
    name: str | None = None,
    probe: ProbeBuilder | None = None,
) -> int:
    """Validate this batch file's schema, then write its review sheet under docs/golden_review/."""
    found, problems = read_file(batch_file)
    if problems or not found:
        raise SystemExit("\n".join(problems) or f"no items found in {batch_file}")
    mine = pick_items(found, only)
    titles = load_titles(project_root / "data" / "corpus")
    probes = probe([item for item in mine if not item.answerable]) if probe else None
    target = project_root / "docs" / "golden_review" / f"{name or batch_file.stem}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shown = batch_file.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        shown = str(batch_file)
    target.write_text(render_sheet(mine, titles, shown, probes), encoding="utf-8")
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


def main(
    argv: list[str] | None = None, project_root: Path = ROOT, probe: ProbeBuilder = build_probes
) -> int:
    """Pick the mode from the arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, help="a batch YAML file, or a sheet with --apply")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--probe", action="store_true", help="add B0 top 3 chunks per question")
    parser.add_argument("--by", default="ali", help="name stored as verified_by")
    parser.add_argument("--only", help="comma separated item ids for a partial sheet")
    parser.add_argument("--name", help="sheet file name without .md, default is the batch name")
    args = parser.parse_args(argv)
    try:
        if args.apply:
            return apply_sheet(args.file, args.by, project_root)
        return write_sheet(
            args.file, project_root, args.only, args.name, probe if args.probe else None
        )
    except (SheetError, GoldenValidationError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    raise SystemExit(main())
