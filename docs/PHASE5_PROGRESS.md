# Phase 5 lite progress

Started 2026-10-14. Resume rule: read this file first, continue at the first unticked item.
Calibration labels are Claude drafts with Ali review pending.

## Step 1: Phase 4 review fixes (order matters)
- [x] F6 pin judge prompt hashes and judge model into run identity and the runner check
- [x] F2 declared item set on the run, exact match resume, finished only when complete
- [x] F3 wire or reject config keys (temperature, max_output_tokens, rerank.enabled, unknown keys)
- [~] F1 code and tests committed; re-score of the stored B0 run still to do (needs the database) counts as not passed, one pass rule, re-score B0 from cache
- [~] F7 tools committed (report --json-out, verify-report); regeneration of B0 files still to do (needs the database) B0 report and summary through tracked code, freshness check
- [x] F4 code committed; retrieval only latency for B0 still to measure (needs the database) latency with migration, p50 and p95 non cached, retrieval only latency for B0
- [x] F5 cluster bootstrap by item, count single class resamples
- [x] F8 docs only: re-ingest invalidates chunk ids
- [x] F13 generator provider error is not scored and is retried on resume
- [x] F14 anchor ledger and cache paths, smoke through build_llm_stack, per model limits
- [x] F9 citation recall None when no answer, regenerate retrieval only reports
- [x] F18 intervals for abstention precision and recall, mark zero width
- [x] F21 parse failures counted from rows
- [x] F6 extra: compare_runs refuses or warns on split, judge, prompt hash, fingerprint differences
- [x] F19 gitignore patterns
- [x] F17 PLAN titles T099 and T100
- [x] Backlog list in PLAN.md (minor and nit findings, F12 required before deployment)
- [x] CI maintenance: ubuntu-24.04 and action major bumps
- [ ] Targeted tests plus B0 regression after Step 1

## Step 2: Phase 5 lite plan and pre-registration
- [ ] pending

## Step 3: techniques
- [ ] pending

## Step 4: FINAL config
- [ ] pending

## Step 5: test split (once)
- [ ] pending

## Step 6: phase5_summary.md
- [ ] pending

## Step 7: end of session
- [ ] pending

## Stopped items
none yet

## Log
- 2026-10-14: file created, starting Step 1.
- 2026-10-14: Step 1 code committed (commits 'git log c1f2123..HEAD'). Commits are coarse where findings edit the same runner files (one change set for F6, F2, F3, F13, F4, F14, F18, F21, F6 extra). Targeted DB tests for identity, item set, provider error, latency and the runner passed; unit tests pass.
- 2026-10-14: the hosted database stopped resolving (DNS error). Pending DB steps: B0 rescore, report regeneration, B0 regression script, retrieval only latency, migrations are already applied to the dev database (0017).
- Process note: rescore.py and its tests were written together, not test first.
