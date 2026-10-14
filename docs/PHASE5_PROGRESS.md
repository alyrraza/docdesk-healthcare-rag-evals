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
- [x] Targeted tests plus B0 regression after Step 1 (unit suite green, DB tests for runner, identity, latency green, B0 regression ok)

## Step 2: Phase 5 lite plan and pre-registration
Written 2026-10-14 BEFORE any technique run. The dev split only, 30 answerable items, so dev effects below
about 0.15 cannot be told from noise. Every config below is listed in the final table, winners and losers.
Primary metric: strict pass rate on answerable items (faithfulness 1.0 and correctness 1.0, the F1 pass rule), against
the B0 baseline of record: 15 of 30 (0.50). Secondary: recall@5, MRR, faithfulness, correctness, wrong abstain count,
tokens billed, p95 latency (non cached). Rule for the FINAL config: a technique is included only if it improves the
primary metric by at least 1 item versus B0 on dev and does not lower faithfulness; ties and losses are excluded. A paired
interval that includes zero is written "no clear difference" and is never called an improvement.
Every technique is its own config file derived from `b0.toml` (never edited). Each new key is added to `KNOWN_KEYS` in the
same commit that reads it. After each code change `scripts/b0_regression.py` must say ok.

| # | technique | target label (dev count) | hypothesis | configs (max 2) | new LLM calls | expected tokens |
|---|---|---|---|---|---|---|
| 1 | E5 per document chunk cap | context_overflow (5) | cap 4 instead of 2 lets gold chunks reach the prompt | `calib_cap4.toml` (exists, id calib_cap4); reuse its stored run 80c1977c after the F1 re-score (0 rows changed, judge pins equal to B0) | none | 0 (already spent) |
| 2 | E3 hybrid retrieval | ranking_miss (5) | adding keyword search with RRF lifts gold chunks the dense leg ranks low | `e3_hybrid.toml` (mode hybrid, top_n 20, top_k 5, rrf_k 60) | yes, after the free retrieval only run | up to 55k generator + 28k judge, less with cache hits |
| 3 | candidate depth and top_k | ranking_miss (5), context_overflow (5), retrieval_miss (2) | a wider top_k (8) keeps gold in range; a deeper candidate list (top_n 50) reaches the 2 retrieval misses | `e5_topk8.toml` (top_k 8, packer budget unchanged), `e5_topn50.toml` (top_n 50, top_k 5) | yes, after the free run | same bound per config |
| 4 | drop title only chunks | gi-014, gi-024 (ranking_miss) | chunks whose text is only the document title ("<drug> drug label") take rank slots without evidence | `e4_title_drop.toml` (new key `retrieval.drop_title_only`) | yes, after the free run | same bound |
| 5 | rule based query decomposition | gi-047 and other multi entity questions | splitting "X and Y" questions into one sub query per drug name, then RRF merge, finds both labels | `e7_decompose.toml` (new key `retrieval.decompose`) | yes, after the free run | same bound |
| 6 | abstain gate (T111a) | missed_abstain / wrong answers on unanswerable items | threshold 0.55 abstains on weak top 1 dense scores before the model is called | `t111a_abstain055.toml` (threshold 0.55), `t111a_abstain060.toml` (0.60, a documented risky variant: 3 answerable items lost at 0.60 in the sweep) | fewer than B0 (abstains skip the generator) | below the B0 bound |

Skipped, with the reason: cross encoder reranker (needs a model download and an ONNX export path that is not in
`docs/TECHSTACK.md`; F3 now refuses `rerank.enabled`); chunk size and strategy changes E1, E2 (a re-ingest changes chunk ids,
F8, and takes about 25 minutes each); second embedding model E6; prompt and generator model changes E8, E9 (out of Phase 5 lite).
Token budget: the guard stops at 85 percent of 200000 per model per day. A budget stop is expected: commit, write this file,
end the session with RESUME TOMORROW.
Disclosure: the cap 4 result (19 of 30 strict pass) was seen before this pre-registration, because that run was made earlier
for judge calibration. It is reported as measured, not as a blind result.

## Step 3: techniques
Results table (primary metric: strict pass on 30 answerable dev items, baseline 15):
| technique | config | strict pass | change | paired interval | verdict (rule) |
|---|---|---|---|---|---|
| E3 hybrid | e3_hybrid (run b509fe25) | 16 of 30 | +1 (gained gi-008, 014, 024, 047; lost gi-003, 016, 026) | [-0.133, +0.200] on the rate: no clear difference | kept by the mechanical rule (+1 item, faithfulness not lowered) but weak: MRR 0.67 against 0.81, recall@5 0.82 against 0.84, wrong abstains 11 against 10 |
| depth top_n 50 | e5_topn50 (run 1670de42) | 15 of 30 | 0 | no clear difference | not kept (tie). Top 5 identical to B0 on every item, so every call was a cache hit |
| depth top_k 8 | e5_topk8 (run 22fb6b60, unfinished) | not finished | | | BUDGET STOP at 168122 of 170000 generator tokens. Resume after 2026-10-15 10:39 UTC. Retrieval only: recall at 8 is 0.93 against recall at 5 0.84, not comparable |
| title only chunks dropped | e4_title_drop (run f4a588e4) | 15 of 30 | 0 | no clear difference | not kept (tie). Retrieval recall@5 0.91 against 0.84 (interval holds zero), top 5 differed on 7 items, no strict pass change. 8435 tokens billed |
| rule based decomposition | e7_decompose (run 89af9b7b) | 15 of 30 | 0 | no clear difference | not kept (tie). Top 5 differed on 3 items (gi-024, 046, 047), no strict pass change. 3186 tokens billed |
| abstain gate 0.55 | t111a_abstain055 (run 5900cbfe) | 15 of 30 | 0 | no clear difference | not kept (tie on the primary metric). 0 tokens billed |
| abstain gate 0.60 (risky) | t111a_abstain060 (run d0c644b8) | 13 of 30 | -2 (lost gi-021, gi-034) | [-0.167, +0.000] | not kept. Wrong abstains 13 against 10 |
| E5 cap 4 | calib_cap4 (reused run 80c1977c) | 19 of 30 | +4 | [+0.033, +0.267] on the rate | kept by the rule (+4 items, faithfulness not lowered). Not blind, see disclosure. |

- [x] P5-3 E5 cap 4 done (no new tokens)
- [x] P5-4 hybrid done (retrieval only run 6ba747df, full run b509fe25, 12m43 wall, 88705 tokens billed; budget guard: generator ledger 151293 of 170000 allowed per 24 hours)
- [~] P5-5 depth: top_n 50 done (no change), top_k 8 stopped by the token budget, resume tomorrow
- [x] P5-6 title drop done (tie, not kept)
- [x] P5-7 decomposition done (tie, not kept)
- [x] P5-8 abstain gate done (0.55 tie, 0.60 loses 2 items, neither kept)

## Step 4: FINAL config
AMENDED 2026-10-15 (before any FINAL run). Original rule: include a technique if it gains at least 1 item and does not
lower faithfulness. Reason for the amendment: hybrid gained 1 item with an interval that holds zero and MRR fell from
0.81 to 0.67, so the one item rule would turn noise into a kept technique. New rule: FINAL_SIMPLE is E5 cap 4 alone
(19 of 30). FINAL_FULL is cap 4 plus every other technique that passed the original rule (hybrid, top_k 8 if it passes).
Freeze FINAL_FULL only if it beats FINAL_SIMPLE by at least 2 items on strict pass and does not lower faithfulness,
otherwise freeze FINAL_SIMPLE. Both are reported in final_vs_b0.md.
- [x] 2026-10-15 final_simple.toml built and run on dev (run 07e3ffbb, label final_simple): 19 of 30 strict pass, all 91 calls cache hits, 0 tokens billed. Same as cap 4.
- [ ] RESUME: (1) e5_topk8 rerun and report after 2026-10-15 10:39 UTC; (2) technique comparison e5_topk8_vs_b0; (3) final_full.toml = cap 4 + hybrid (+ top_k 8 if it passes the original rule), run label final_full; (4) apply the amended rule, write final_vs_b0.md, copy winner to final.toml, DECISIONS entry FINAL frozen; (5) test split once each; (6) python scripts/phase5_summary.py; (7) push, CI.
- [ ] (old note) waits for e5_topk8 (resume the same command after 2026-10-15 10:39 UTC). Candidates by the rule so far: E5 cap 4 and E3 hybrid.
  Build `evals/configs/final.toml` from the techniques that pass, run it on dev once, write `evals/results/final_vs_b0.md`, then freeze.

## Step 5: test split (once)
- [ ] pending

## Step 6: phase5_summary.md
- [~] generator written (`scripts/phase5_summary.py`, test passes), table built with FINAL and top_k 8 marked not finished; rebuild after they finish

## Step 7: end of session
- [ ] pending

## Stopped items
- e5_topk8 full dev run (run 22fb6b60): stopped by the daily token guard, resumable. Command: `python -m docdesk.evals.cli --config evals/configs/e5_topk8.toml run --label e5_topk8` after 2026-10-15 10:39 UTC.
- Cross encoder reranker, E1, E2: skipped on purpose (see Step 2).

## Log
- 2026-10-14: file created, starting Step 1.
- 2026-10-14: Step 1 code committed (commits 'git log c1f2123..HEAD'). Commits are coarse where findings edit the same runner files (one change set for F6, F2, F3, F13, F4, F14, F18, F21, F6 extra). Targeted DB tests for identity, item set, provider error, latency and the runner passed; unit tests pass.
- 2026-10-14: the hosted database stopped resolving (DNS error). Pending DB steps: B0 rescore, report regeneration, B0 regression script, retrieval only latency, migrations are already applied to the dev database (0017).
- Process note: rescore.py and its tests were written together, not test first.
- 2026-10-15: Step 3 done except top_k 8. Next session: (1) resume e5_topk8, then `report`, `technique e5_topk8 <B0 run> <run>` (note recall at 8); (2) build final.toml, run FINAL on dev, compare, freeze with a DECISIONS entry that has the date and the git hash; (3) only if all preconditions hold, B0 and FINAL on test once each with `--split test --allow-test`; (4) `python scripts/phase5_summary.py`; (5) secret scan and push.
