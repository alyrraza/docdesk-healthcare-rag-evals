"""Write the judge calibration report and summary from the stored files (T100, AC-EVL-07).

Usage:
    python scripts/calibration_report.py
        reads manifest.yaml, labels.yaml, manifest_synthetic.yaml, labels_synthetic.yaml,
        judge_results_synthetic.yaml and the stored judge labels of the natural runs, and writes
        evals/results/judge_calibration.md and evals/results/judge_calibration_summary.json

Both files are generated: rerun the script, never edit them. It spends no tokens. Natural and
synthetic outputs are computed apart and never pooled. The report gives no pass or fail verdict.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from calibration_sheet import (
    LABELS,
    LABELS_SYNTHETIC,
    MANIFEST,
    MANIFEST_SYNTHETIC,
    Source,
    db_chunks,
    db_runs,
)
from docdesk.evals.calib_join import JoinError, join_natural, join_synthetic
from docdesk.evals.calib_report import plain_tree, render_markdown
from docdesk.evals.calibration import (
    NATURAL_BORDERLINE,
    SYNTHETIC_BORDERLINE,
    build_summary,
    provenance_from,
)
from docdesk.evals.golden.loader import read_items
from docdesk.evals.stats import DEFAULT_RESAMPLES, DEFAULT_SEED

ROOT = Path(__file__).resolve().parents[1]
JUDGE_RESULTS = Path("evals") / "calibration" / "judge_results_synthetic.yaml"
MARKDOWN_OUT = Path("evals") / "results" / "judge_calibration.md"
JSON_OUT = Path("evals") / "results" / "judge_calibration_summary.json"


def load(root: Path, relative: Path) -> dict[str, Any]:
    """One yaml file of the calibration folder."""
    return yaml.safe_load((root / relative).read_text(encoding="utf-8"))


def build(root: Path, source: Source, resamples: int, seed: int) -> dict[str, Any]:
    """Join both sets to their judge labels and compute the summary; a gap stops with its reason."""
    manifest, labels = load(root, MANIFEST), load(root, LABELS)
    synthetic_manifest = load(root, MANIFEST_SYNTHETIC)
    synthetic_labels, results = load(root, LABELS_SYNTHETIC), load(root, JUDGE_RESULTS)
    facts = {item.id: list(item.gold_facts) for _, item in read_items(root / "evals" / "golden")[0]}
    rows = dict(source.runs(manifest["runs"]))
    try:
        natural = join_natural(manifest, labels, rows, facts, NATURAL_BORDERLINE)
        synthetic = join_synthetic(synthetic_manifest, synthetic_labels, results, facts,
                                   SYNTHETIC_BORDERLINE)
    except JoinError as error:
        raise SystemExit(f"cannot join the judge labels: {error}") from error
    judge = {"model": results["judge_model"], "prompts": results["prompts"]}
    return build_summary(natural, synthetic, provenance_from(labels),
                         provenance_from(synthetic_labels), judge, resamples=resamples, seed=seed)


def main(
    argv: list[str] | None = None,
    project_root: Path = ROOT,
    source: Source | None = None,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> int:
    """Generate both files; they are rewritten each time because they hold no hand edits."""
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    summary = plain_tree(build(project_root, source or Source(db_runs, db_chunks),
                               resamples, seed))
    (project_root / MARKDOWN_OUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / MARKDOWN_OUT).write_text(render_markdown(summary), encoding="utf-8")
    (project_root / JSON_OUT).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {project_root / MARKDOWN_OUT} and {project_root / JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
