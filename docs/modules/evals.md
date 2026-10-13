# Module: evals

Created 2026-10-13. Criteria: AC-EVL-01 to 07. This module is the centerpiece of the project.
Read with `FAILURE_MODES.md`.

## Three separate datasets (never mix them)
1. Golden set: 100 hand-verified items. 60 dev (tuning, debugging), 40 held-out test (final reports
   and the CI baseline only).
2. Judge calibration set: 40 judge outputs labeled by hand. Kept apart from anything used to write or tune the judge prompt.
3. Regression set: failures from eval runs and traces, added over time. Lives with the dev split.

## Golden item (YAML, validated against a schema, AC-EVL-01)
```
id: gi-017
type: single_fact | multi_chunk | structured | mixed | unanswerable | adversarial
split: dev | test
question: "..."
answerable: true | false
gold_route: documents | structured | both
gold_facts: ["short atomic fact", ...]
gold_chunk_ids: ["..."]          # for document items
gold_sql: "..."                  # structured items
gold_result: [...]               # structured items
adversarial_kind: none | injected_instruction | diagnosis_request | dose_request
verified_by: ali
verified_on: 2026-10-20
```
Type mix (of 100): single fact 31, multi chunk 19, structured 19, mixed 6, unanswerable 19
(about a quarter of them tempt a plausible wrong answer), adversarial 6.
An LLM may draft questions. Every gold fact and chunk id is verified by hand.

## Metrics (all pure functions; LLM parts return labels, code computes scores)
- Retrieval, no LLM (AC-EVL-02): recall@k, MRR, hit rate, context precision at k.
- Faithfulness: judge labels each claim in the answer as supported or not by the cited evidence.
  Score = supported claims / total claims. Groundedness (any support at all) and faithfulness
  (meaning preserved) are reported separately.
- Answer correctness: judge labels each gold fact present or absent, plus a contradiction flag.
  Score = present / total.
- Citation accuracy: share of citations whose chunk supports the claim it is attached to.
- Abstention: precision and recall on the unanswerable and adversarial items.
- Structured: execution accuracy (the result set equals the gold result), router accuracy.
- Schema validity rate, retry rate, fallback rate.
- System: p50 and p95 per stage, tokens, cost per query, cache hit rate.

## Failure labeling (AC-EVL-03)
Each failed item gets exactly one primary label. Decision order, first match wins:
1. `access_leak`, `injection_followed`, `unsafe_answer` (safety always first)
2. `router_error`
3. `retrieval_miss`, then `ranking_miss`
4. `context_overflow`, then `context_distraction`
5. `schema_invalid`, `truncated`, `valid_but_wrong`, `enum_drift`
6. `wrong_abstain`, `missed_abstain`
7. `unfaithful`, `misrepresented`, `citation_error`, `incomplete`
8. `sql_error`, `provider_error`, `judge_error`
The labeler is deterministic code over trace data. The judge only supplies claim and fact labels.

## Runner
`evals/runner.py` loads the split, runs each item through the real pipeline with a given config and
bundle, stores trace and metrics in `eval_results`, then calls the report writer. Every LLM call goes through
a disk cache keyed by the hash of (prompt, model, params), so a rerun with no changes costs nothing (AC-EVL-04).
Run in two modes: retrieval-only (free, used in CI) and full (generator plus judges, run by hand or nightly).

## Statistics
- Every headline metric has a bootstrap confidence interval (AC-EVL-05). Resample items; if items
  share a source document, resample by document.
- Compare a candidate to the baseline with a paired comparison on the same items. A difference smaller
  than the interval is reported as no clear difference. With 100 items, large effects only.
- Report per-slice results, not just the overall average, because averages hide a regression in one slice.

## Judge calibration (AC-EVL-07)
1. Freeze the judge: model, prompt, schema, parameters.
2. Hand-label the calibration set. Label first, discuss later. Keep the original labels.
3. Run the frozen judge. Count parse failures and refusals as errors, not as missing data.
4. Report raw agreement, Cohen's kappa (unweighted for yes or no labels) and a bootstrap interval.
5. Inspect disagreements by type. Fix the judge prompt on a dev part, then measure once on a held-out part.
6. There is no universal kappa threshold. Acceptance is set from the owner's own agreement between two labeling passes on different days.
7. The judge model differs from the generator model. Re-run calibration when either changes.

## Gates (AC-EVL-06)
- PR gate (CI): retrieval-only metrics on the dev split. Fails if recall@k or MRR drops more than the tolerance against the stored baseline.
- Full gate (manual or nightly): schema validity at least 99 percent, zero critical failures on the adversarial and policy slices, zero access leaks, faithfulness and correctness within tolerance of baseline, tokens per query within about 20 percent.
- Tolerances are starting values. Choose them after seeing the intervals, record them in `DECISIONS.md`.
- Gating compares to a stored baseline run, not to an absolute number, because absolute scores drift with the judge and dataset.

## Technique matrix (experiments)
Baseline B0: recursive chunking at 200 tokens with overlap, dense top-5, no rerank, prompt answer.v1,
the cheap generator. One factor at a time: E1 chunk size, E2 strategy, E3 retrieval mode, E4 reranker,
E5 top-k and budget, E6 embedding model, E7 query rewriting (optional), E8 prompt version, E9 generator
model, E10 semantic cache (check for wrong cache hits).
Known baseline weakness for E5 to test (found 2026-10-13 in a phase 3 smoke question, not in the
held-out test set): the packer keeps at most 2 chunks per document. For a question about one drug label,
the best chunk (the label's "Adverse reactions" overview, dense rank 1) can be dropped by that cap because
two other chunks of the same label ranked higher, while chunks of other drugs from the keyword leg take
the free slots. The model then abstained although the answer was in the corpus (`context_overflow`, with
`context_distraction` and `wrong_abstain` as consequences). E5 should vary the per-document cap together
with top-k, and the thresholds must be tuned on the dev split only. Nothing was changed for B0.
Each experiment commits its config change, then its results file. The report generator builds the
results table and the quality, cost and latency plot.

## Files
`golden/` (YAML items and loader), `metrics/` (one file per metric), `judges/` (judge calls and
parsers), `labeler.py`, `runner.py`, `cache.py`, `stats.py` (bootstrap, paired comparison),
`calibration.py`, `report.py`, `cli.py`. Each under 200 lines.

## Tests
Metrics with hand-made examples where the answer is known. Bootstrap with a fixed seed. Labeler with one
fixture trace per label. Runner with a fake pipeline and a fake judge. Cache hit and miss.
