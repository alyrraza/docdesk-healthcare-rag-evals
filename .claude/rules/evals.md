---
paths:
  - "src/docdesk/evals/**/*.py"
  - "tests/evals/**/*.py"
  - "evals/**/*"
---

# Evaluation rules

- The golden set is hand-verified. Never write or change a gold answer without
  Ali confirming it. A wrong gold answer makes every number meaningless.
- The held-out test split is touched only for final reports and the CI gate
  baseline. Tuning and debugging happen on the dev split.
- Never tune a judge prompt on the calibration set. Keep the three sets separate:
  golden set, judge calibration set, regression cases from production traces.
- Judges output labels (claim supported or not, fact present or not). Scores are
  computed by code from those labels.
- Every LLM call in an eval run is cached on disk by hash of (prompt, model,
  params). Re-running an eval must cost nothing when nothing changed.
- Every headline metric is reported with a bootstrap confidence interval.
  Differences smaller than the interval are written up as "no clear difference".
- Every failed item gets exactly one primary failure label from `docs/FAILURE_MODES.md`.
- Change one factor at a time against the baseline. No full grids.
- Read `docs/modules/evals.md` before editing.
