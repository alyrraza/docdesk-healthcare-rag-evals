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
bundle, stores trace and metrics in `eval_results`, then calls the report writer.
Run in two modes: retrieval-only (free, used in CI) and full (generator plus judges, run by hand or nightly).

Rules for a full run (added 2026-10-13, tasks T079a to T079e):
- **Pacer** (`llm/pacer.py`): limits tokens per minute and requests per minute per model. When a limit
  is reached the call waits; it never fails and never becomes a `system_error` row. In process only.
- **Cache** (`evals/cache.py`, AC-EVL-04): key is the hash of prompt hash, model id, sampling params and
  the full input. Entries live under `.cache/` (git-ignored). Each entry keeps the original tokens in and
  out and the original latency, and a result carries a `cache_hit` flag. Cost reports use the stored
  tokens. Latency experiments bypass the cache or read the recorded stage timings, so a cache hit never
  produces a fake latency number.
- **Resumable runner**: progress is saved after every item (item id, config id, bundle id), so a stopped
  run continues where it stopped and never repeats a finished item.
- **Daily budget guard** (`evals/budget.py`): keeps a ledger of tokens used per model. It stops the run
  cleanly before the daily limit (at 85 percent of the limit, which leaves room for retries and for
  the other tools that share the key) and prints how to continue. Cache hits cost nothing.
- **Judge output**: JSON mode where the provider supports it. The parser also strips one fenced json
  block, because a judge can wrap its answer even when told not to. Every parse failure is counted and
  shown in the report as `judge_error`; none is hidden or silently retried into a pass.

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
B0 is pinned in one file, `evals/configs/b0.toml` (T079e), with a content hash. It holds everything that
shapes a result: retriever (dense), k (5), chunk strategy and size (recursive, 200 tokens), per-document
cap, rerank off, prompt name and version, generator model id, judge model id, abstain threshold, token
budget slots. Once the first B0 result is stored the file is frozen. A change means a new baseline with
a new id (b1, b2), never an edit. Every result stores the config id and its hash.

The live API default is different on purpose: `POST /query` uses hybrid retrieval (dense plus keyword,
RRF, n=20, k=5). B0 is dense top-5, so E3 can measure what hybrid adds. Numbers measured on B0 do not
describe the live API until the hybrid config has its own eval run.

Each experiment commits its config change, then its results file. The report generator builds the
results table and the quality, cost and latency plot.

## Eval budget and pacing (measured and recomputed 2026-10-13)
Limits on the free Groq key, per model: 8,000 tokens per minute, 30 requests per minute, 1,000 requests
and 200,000 tokens per day. OpenRouter free models: 20 requests per minute, 50 requests per day (under
10 credits bought), counted per UTC day.

**Per item tokens.** Generator: 1,470 measured (mean of 10 real queries: 1,203 in, 267 out), plus 10
percent for retries and repairs, so 1,600 used below. Faithfulness judge: 1,150 estimated (measured
615 on a one claim example, scaled to about 2 cited chunks and 4 claims). Correctness judge: 420
estimated (measured 291 on a one fact example). Re-measure when T090 and T091 exist. About 70 percent
of items are answerable and get both judges (42 of 60, 28 of 40); unanswerable items need no judge.

**One run.**
| Run | Generator tokens | Judge tokens | Minutes at 8,000 tokens per minute |
|---|---|---|---|
| Dev, 60 items | 60 x 1,600 = 96,000 | 42 x 1,150 + 42 x 420 = 48,300 + 17,640 = 65,940 | generator 96,000 / 8,000 = 12.0; judges 65,940 / 8,000 = 8.2; about 15 with retries, both models run in parallel |
| Test, 40 items | 40 x 1,600 = 64,000 | 28 x 1,150 + 28 x 420 = 32,200 + 11,760 = 43,960 | generator 8.0; judges 5.5; about 10 |

**Full matrix as a funnel.** E1 to E6 and E10 are scored with retrieval-only metrics (recall@k, MRR, hit
rate, gold ids in `dropped_ids`) and cost no LLM tokens. E7 costs about 100 tokens per query and is
optional. E8 (prompt version) and E9 (generator model) cannot be retrieval-only. LLM runs:
- 7 dev runs on gpt-oss-120b: B0 (1), the best three retrieval configs (3), two extra prompt versions
  for E8 (2), the final config (1).
- 1 dev run for E9 on an alternative generator. It uses that model's own daily budget, but its answers
  are still judged by the judge model.
- 2 test runs on gpt-oss-120b: B0 and the final config, each run once.

**Totals.**
- gpt-oss-120b: 7 x 96,000 + 2 x 64,000 = 672,000 + 128,000 = 800,000 tokens. (An earlier estimate of
  700,000 counted six dev runs by mistake; 800,000 is right.)
- Judge model: 8 x 65,940 + 2 x 43,960 = 527,520 + 87,920 = 615,440 tokens. The 40 item judge
  calibration adds 40 x (1,150 + 420) = 62,800, so about 678,000.
- OpenRouter cross check: 40 faithfulness plus 40 correctness calls is 80 requests at 50 per day, so
  2 UTC days, in parallel with the Groq days.

**Days.** At 100 percent of the daily limit the generator needs 800,000 / 200,000 = 4.0 days, so 4 days
is only right with no margin. The guard stops at 85 percent (170,000 tokens a day): generator 800,000 /
170,000 = 4.7, so 5 days; judges 678,000 / 170,000 = 4.0, so 4 days (they run in parallel with the
generator days). Two dev runs do not fit in one day under the guard (2 x 96,000 = 192,000 > 170,000);
one dev run plus one test run does (160,000). Plan with 5 LLM days, plus 1 buffer day for a failed or
rate limited day, plus the retrieval-only funnel that runs before them: about 7 calendar days in total.

**Reset time.** Groq's rate limit page does not say when the daily limits reset. The reset header seen
on a first call of the day was 1 minute 26.4 seconds for a 1,000 request limit, which equals 86,400
seconds / 1,000 requests, so the limit looks like a bucket that refills continuously over 24 hours, not
a reset at a fixed clock time. This is an inference, not documented. The guard therefore counts tokens
in a rolling 24 hour window and treats "next day" as 24 hours after the spend, and the first real
429 for the daily limit should be read for its wait time and noted here. OpenRouter says the daily
counter is per UTC day.

## Files
`golden/` (YAML items and loader), `metrics/` (one file per metric), `judges/` (judge calls and
parsers), `labeler.py`, `runner.py`, `cache.py`, `stats.py` (bootstrap, paired comparison),
`calibration.py`, `report.py`, `cli.py`. Each under 200 lines.

## Tests
Metrics with hand-made examples where the answer is known. Bootstrap with a fixed seed. Labeler with one
fixture trace per label. Runner with a fake pipeline and a fake judge. Cache hit and miss.
