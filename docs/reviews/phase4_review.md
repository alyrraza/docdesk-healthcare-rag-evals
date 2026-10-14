# Phase 4 independent review (T079 to T103)

Reviewer: a fresh session that did not write the code. Read only, except this file. No provider call was made.
Dev split only. Database reads were read only SELECTs on the dev database. CONFIRMED means verified by exact
reading or by running a small script (kept outside the repo). PLAUSIBLE means argued but not reproduced.

## Summary

- The harness is sound where it matters most: no test item can reach a run by accident, the stored B0 numbers
  re-derive exactly from raw rows, and the cache, budget guard, pacer, client order holds at every runner call site.
- The real risks are for Phase 5: a judge failure counts as a pass, resume and compare do not check what they
  resume or compare, several config keys are never read, and no latency is stored.
- The calibration interval is too optimistic (resamples dropped, repeated items) and the labels are Claude drafts.
- Some committed result files are stale against the code and the docs (B0 dev report, retrieval only reports).
- No secret was found in the full history. The repo is safe to make public from a secrets point of view, with the caveats in question 8.

**Verdict: SAFE AFTER LISTED FIXES** (fix F1 to F6 before the first Phase 5 technique run; the rest can follow).

## Findings

Severity order. No blocker was found.

| id | sev | where | what is wrong | failure scenario | suggested fix | status |
|---|---|---|---|---|---|---|
| F1 | major | `evals/scoring.py:108`, `evals/labeler.py:47`, `evals/report_sections.py:53` | A judge parse failure or judge error gives a None score, the labeler does not fail the item, so `passed` is true. The "strict pass" and the "stage split pass" use different rules. | Both judges fail on an answered item: `label_failure` returns None (I ran it), `passed` is true, the pass rate and `compare` count a pass, while `is_strict_pass` says no. A flaky judge raises the headline pass rate. | Make `passed` None (not scored) when an answered item lacks a judge score, count it in its own row, use one pass definition in both tables. | CONFIRMED |
| F2 | major | `evals/run_store.py:15-62`, `evals/runner.py:113-170` | `open_run` continues the newest unfinished run with the same config id, bundle id and split. It ignores config hash, `--items`, label and git sha, and `run_eval` always stamps the run finished. | A budget stop leaves a full dev run unfinished. A later `run --items gi-001` joins that run, runs one item, and marks the run finished with 30 items missing. Or an edited config with the same id (new hash) adds rows to an old run. `compare` then pairs a partial run. | Store the config hash and the selected item list on the run, continue only on an exact match, mark finished only when every selected item has a row. | CONFIRMED (reading) |
| F3 | major | `evals/config.py:43-52`, `evals/live_pipeline.py:77-90`, `evals/configs/b0.toml:22,46` | `[rerank] enabled`, `[models] temperature` and `max_output_tokens` are hashed into the config but never read. Temperature and max tokens come from the prompt file params. | A Phase 5 E4 config sets `rerank.enabled = true` and gets the same ranking as B0 under a new id. An E8 or E9 config with another temperature changes nothing. The paired comparison reports "no clear difference" for a factor that was never applied. | In T105 make every config key either wired or rejected by the loader (unread keys fail loudly), one test per key. | CONFIRMED |
| F4 | major | `evals/pipeline.py`, `evals/scoring.py:98-110` | No stage latency is stored. `RetrievalResult.timings_ms` and `LLMResult.latency_ms` are dropped. | The Phase 5 hero table needs p95 latency per config and T103 needs a baseline. B0 has none, and a technique run without timings cannot be compared. | Add per stage timings (retrieval, generate, judges) to `PipelineOutput` and `metrics` before the first technique run; mark cached latency, never use it as a latency number. | CONFIRMED |
| F5 | major | `evals/calib_stats.py:47,88`, natural manifest | The kappa bootstrap drops every resample where either side has one class. A constant judge has kappa 0, a valid value. Also 30 outputs are only 24 distinct items (6 items appear twice, from B0 and calib_cap4) but outputs are resampled as independent. | Faithfulness item kappa 0.651 is reported with interval 0.366 to 1.000 over 1257 of 2000 resamples. I simulated the same table: about 24 percent of resamples have a constant side with kappa 0, 13 percent are undefined; counting the zeros gives a lower bound of 0.0. The reported lower bound is not honest. | Count one class resamples as kappa 0 (undefined only when both sides are constant), resample by item id, show the share dropped next to the interval. | CONFIRMED (simulation) |
| F6 | major | `evals/judges/kit.py:13-14`, `evals/preflight.py:29`, `evals/configs/b0.toml` | Only the answer prompt is pinned. Judge prompt file names (`...v2.md`) are hardcoded, their hashes are only written into each row, and the judge model is not checked against the stored run. `compare_runs` does not look at judge model or prompt hashes. | Edit the judge prompt, or change the judge model under a new config, then compare to B0: the faithfulness and correctness differences are mixed with a judge change and the report says nothing. | Pin judge prompt name, version and hash in the config, refuse a run on mismatch, make `compare` refuse or warn when judge hashes differ. | CONFIRMED |
| F7 | major | `evals/results/b0_dev_report.md:51-60`, `evals/results/b0_dev_summary.json`, `scripts/abstain_sweep.py:39` | The committed B0 report still has the per model table "counted from every entry in the cache folder", which DECISIONS and evals.md say was removed as a bug (T098b). Regenerating the report from the same run differs in 2 places (I did it, to a scratch file). `b0_dev_summary.json` (with ledger fields) was written by a scratch script that is not in the repo, and `abstain_sweep.py` reads the run id from it. | A reader trusts per model token numbers the docs call wrong. The abstain analysis depends on a file nobody can regenerate. | Regenerate the report with the current CLI and commit it. Add the script that builds the summary json, or make `abstain_sweep.py` take the run id as an argument. | CONFIRMED |
| F8 | major | `scripts/reingest_corpus.py`, `db/repositories/fingerprint.py` | One global corpus and one fingerprint row. A re-ingest for E1 or E2 deletes the seed chunks and creates new chunk ids. Stored `trace.used_ids` and `retrieved_ids`, the calibration manifest and `calibration_judge --check` (it rebuilds context from chunk ids) then point at ids that no longer exist. Going back to B0 chunking makes yet new ids. | After E1, the B0 rows can no longer be re-judged, re-labeled or audited, and the calibration check fails. | Before the first re-ingest, store chunk text (or content hash and position) in each row trace, or use one database per chunking config. Write down that B0 artifacts are frozen. | PLAUSIBLE |
| F9 | minor | `evals/metrics/citation.py:28`, `evals/scoring.py:102`, `evals/results/b0_retrieval_dev_run1.md` | With no citations (retrieval only) citation recall is 0.0, not None. The committed retrieval only reports show `citation recall 0.00 [0.00, 0.00]`. | A reader sees a measured 0.00 for a metric that does not exist in that mode. Breaks the rule "no value is never 0". | Return None when the mode produced no answer; regenerate the two reports. | CONFIRMED |
| F10 | minor | `tests/` (names) | Tests are named after the wrong AC. All 19 judge tests use AC-EVL-07 (the calibration report). Runner tests `runner_04` to `runner_08` and `live_02` to `live_04` use AC-EVL-03 (failure labels). `preflight_*`, `usage_*` and the CLI report test use AC-EVL-04 (disk cache). Two pyproject tests use AC-EVL-06 (the CI gate). | `scripts/check_ac_coverage.py` (T118) will report AC-EVL-03, 04, 06 and 07 as covered by tests that do not test them. | Rename to honest ids; add PRD criteria for judges, runner and preflight, or name them by task id. | CONFIRMED |
| F11 | minor | `.github/workflows/ci.yml:19,39-40,66,83-84` | `actions/checkout@v4` and `setup-python@v5` are Node 20 actions pinned by tag. `ubuntu-latest` moves to Ubuntu 26 on 2026-10-19. `pgvector/pgvector:pg16` and `redis:7` float. Dependencies are ranges with no lock file. | After the runner image change a green main can turn red without a code change, and the gate can move with a library update. | Move to the Node 24 majors of both actions (check the current major) pinned by commit sha, use `ubuntu-24.04`, pin image digests, add a constraints file. | CONFIRMED |
| F12 | minor | `scripts/ci_gate_compare.py`, `evals/ci/expected.json` | The gate watches 14 items, recall@5 (saturated at 1.0) and MRR, tolerance 0.04, dense B0 only. One item moving from rank 1 to rank 2 changes MRR by 0.036 and passes, as the decision says. It never exercises generation, rerank or hybrid, and has never been seen to fail end to end. | A one position decay on one item per commit passes forever. A later rerank stage that breaks is not seen. "AC-EVL-06 done" covers retrieval of one config. | Keep it, run it once against a corrupted baseline to show it fails, call it a smoke test in the docs, and add a baseline per technique config in Phase 5. | CONFIRMED |
| F13 | minor | `evals/runner.py:140-160`, `generation/answer.py:53` | A provider error on the generator becomes an `error` outcome row, labeled `other`, counted as a failed item, and a rerun skips it because the row exists. | A 5xx burst at item 20 permanently marks that item failed in this run; the pass rate drops for infrastructure reasons and cannot be repaired without a new run. | Store provider errors as not scored with the reason, leave them out of the pass rate, let a rerun retry them. | CONFIRMED (reading) |
| F14 | minor | `scripts/smoke_llm.py:47`, `evals/cli_runtime.py:30,32`, `evals/budget.py:39-51` | `smoke_llm.py` builds the raw client: no cache, no ledger, no pacer. Ledger and cache paths are relative to the working directory, the ledger file has no lock, and a call is counted once although `RetryingClient` can send up to 3 requests. The daily limit 200000 and the Groq pacer limits are hardcoded for every model. | Smoke spend is invisible to the 85 percent guard, a run started from another folder gets a second empty ledger, and an E9 model with other limits is guarded wrongly. | Anchor paths to the project root, route smoke through `build_llm_stack`, put limits per model in the config. | CONFIRMED |
| F15 | minor | `evals/golden/loader.py:150-175` | `load_golden` validates and resolves the whole directory, test items included, on every dev load. `include_drafts` has no caller. | A bad quote in a test item blocks dev work, and reading test items becomes routine. | Make validation of other splits a flag, and remove or test `include_drafts`. | CONFIRMED |
| F16 | minor | `docs/modules/evals.md:79,86,222-223`, `README.md:5`, `evals/configs/b0.toml:34` | Stale statements: "groundedness reported separately" and "citation accuracy" (the code has citation precision and recall against gold evidence); the "progress saved after every item" text describes `RunProgress`, which is dead code (the real record is the DB row); README says "early scaffolding"; b0.toml still calls the threshold a placeholder (known, frozen file). | A reader or interviewer is told features exist that do not. | Edit the docs; delete `RunProgress` or use it. | CONFIRMED |
| F17 | minor | `docs/PLAN.md` T099, T100 | Ticked done although the labels are drafts. The text says so, but the tick and the AC-EVL-07 test names read as complete. Faithfulness kappa rests on 2 flagged outputs of 30. | A later summary says "judge calibrated". | Add "(drafts, review pending)" to the task titles and to the future README results table. | CONFIRMED |
| F18 | minor | `evals/report_data.py:60-90` | AC-EVL-05 wants an interval for every headline metric. Abstention precision and recall, PRD hero metrics, are shown as counts only. Cells with one group or all equal values show a zero width interval (for example faithfulness 1.00 [1.00, 1.00]). | The hero table cannot show abstention precision with an interval; zero width intervals read as certainty. | Add intervals for the abstention rates and mark zero width cells. | CONFIRMED |
| F19 | minor | `.gitignore`, git history | `.gitignore` has no `*.db`, `*.sqlite`, `*.pem`, `*.key`. `INSTALL.md`, `docs/COMMITS.md`, `REFERENCES.md`, `REMEMBER.md`, `SKILLS.md`, `WORKFLOW.md` are in history (commits 47ce10f, a6405cb, 6100363; untracked in 0c00880). | Not secrets, but local notes become public with the history. | Add the patterns; decide whether the old notes in history matter. | CONFIRMED |
| F20 | minor | `pyproject.toml` | `python-dotenv` (used by `tests/conftest.py`, `scripts/bench_vector_index.py`, `scripts/load_synthea.py`), `pydantic` and `starlette` are imported but arrive only through other packages. | A change in pydantic-settings or fastapi extras breaks a clean install. | Declare them; extend `test_pyproject_deps` to scripts. | CONFIRMED |
| F21 | nit | `evals/runner.py:162-168` | `parse_failures` in the run summary is per process; a resumed run prints only the new failures. The report counts from rows and is right. | The CLI says "0 parse failures" after a resume that follows a bad session. | Count from rows. | CONFIRMED |

## Question 1: test split leakage

Checked: every use of `load_golden`, `read_items`, `read_file`, `allow_test` and `include_drafts` in `src` and `scripts`, the CLI parser, the stored runs and result items in the database, the CI subset file.
- Paths that can run the test split: only `run_eval` with `split="test"` and `allow_test=True`, reached by `cli run --split test --allow-test`. `SplitLockedError` is raised in `run_eval` (`runner.py:116`), in the CLI (`cli.py:100`) and in `load_golden` (`loader.py`), before any row is written. `--items` cannot unlock it (`select_items` works on the already loaded split).
- Scripts: `b0_rows.py:35` hardcodes `"dev"`, so `b0_run`, `ci_gate`, `abstain_sweep` and `abstain_tradeoff` are dev only. `b0_summary` and `b0_render` are pure functions. `calibration_sheet.py:66` refuses a non dev run. `calibration_report`, `calibration_sheet` and `calibration_synthetic` use `read_items` on the whole golden folder (questions and key points of all splits are read into memory) but look items up by the ids of dev runs, so no test item is used. `golden_check` and `golden_review` read single batch files for review, by design.
- Verified filter: `load_golden` filters `item.verified`; `include_drafts` has no caller (F15).
- Database: all 4 runs are `dev`; the 45 distinct item ids across all rows are all dev ids; no test id is stored. The CI subset has 14 items, all `split: dev`.
- Result: no leak found. Remaining gap: a test run is stored in the same tables and the report does not mark it, and nothing stops it from being repeated (the plan says once).

## Question 2: metric correctness

Re-derived with my own code (not `docdesk.evals`) from `eval_results.trace.retrieved_ids`, the golden YAML and the `chunks` table:
- Gold chunks for the 30 answerable dev items (whole quote inside a chunk after whitespace folding, plus `alt_sources`): zero differences against stored `recall` and `mrr` for all 30 items.
- recall@5 0.8389 (report 0.84), MRR 0.8056 (0.81), hit@5 0.90, 7 items with recall below 1 (gi-008, 014, 024, 047, 049, 051, 053), which equals retrieval_miss 2 plus ranking_miss 5.
- Strict pass: 15 of 30 (both scores 1.0, none contradicted). Overall passed 27 of 44 = 0.614. The stage split 7 / 5 / 3 / 15 adds to 30 and matches the label counts in the database (context_overflow 5, ranking_miss 5, retrieval_miss 2, context_distraction 1, incorrect 1, unfaithful 1, missed_refusal 2).
- Retrieval only runs 05a8adf1 and 9fc1fbda are identical to each other and to the full run on recall and MRR for every item (retrieval is deterministic).
- Bootstrap: re-implemented (group sums and counts, 2000 draws, seed 0, `default_rng`): recall CI 0.722 to 0.950, report 0.72 to 0.94 (same method, rounding at the edge). The resampling unit is the first evidence source; in this dev set all 30 answerable items have a distinct source, so grouping changes nothing. Undefined values are dropped before resampling (never 0) and n is shown. An empty set gives no interval. Edge: one group or equal values give zero width (F18).
- Resolver rule (`golden/evidence.py:68`): overlap at least half the quote and above zero; the whole quote implies overlap equal to quote length. Matches the docs. An identical chunk text that repeats could be located at an earlier position (`locate_chunks` searches forward from the previous start); not seen in the data.
- Cohen's kappa: formula correct; single class is reported as undefined and labeled; the bootstrap handling is wrong (F5).
- Docs versus code: retrieval metrics, outcome cells, labeler order and condition table match. Mismatches: groundedness and citation accuracy (F16), citation recall in retrieval only mode (F9). Abstention precision excludes abstains on refuse items, as its docstring says.

## Question 3: judge isolation

Checked `judges/call.py`, `faithfulness.py`, `correctness.py`, `scoring.run_judges`, both prompt files, `parser.py`.
- Faithfulness judge variables: question, answer (without disclaimer), evidence = the packed chunks the generator was given. No gold evidence, no gold facts, no key points.
- Correctness judge variables: question, answer, numbered `gold_facts` as key points. No retrieved context, no gold evidence quotes. Only for `behavior == answer` items.
- Code decided outcomes never call a judge: not answered or empty answer returns `skipped` or `decided_by_code` before `call_judge`. An `error` outcome is not judged.
- Parse failures: counted by `JudgeParser`, score None, status `parse_failed`; label sets that do not match are rejected and counted. Never scored as 0. But a missing score counts as a pass in `passed` (F1).
- Prompt files and hashes: hashes are stored in each row and in the calibration report, but only the answer prompt is pinned (F6). Both judge prompts still say `status: draft`.
- Not verified: that the rebuilt judge evidence equals the generator prompt text (the calibration `--check` proves it against the earlier judge call, not the generator call).

## Question 4: LLM layering

- Runner: `stack.py` builds cache, budget guard, pacer, client; one stack per config id (`cli_runtime.py`) is shared by the generator and both judges; tests `stack_01` to `stack_04` pin the order.
- Scripts: `calibration_judge.py --run` uses `llm_stack_for(config)` (correct); `--check` uses `CachedClient(CacheOnly())` and cannot spend. `smoke_llm.py` uses the raw client (F14). The live API uses `RetryingClient(GroqClient)` without cache, by design.
- Retry sits inside the client, below the pacer and the ledger (F14).
- Cache key (`cache.py:21`): hash of system text (the prompt), model, temperature, max_output_tokens, json_mode and user input. Complete for what `LLMRequest` carries. Not in the key: provider and base url. Failed calls are not cached; truncated (`finish_reason` length) and unparsable replies are cached and replay forever (nit).
- Cross run leakage: a hit returns `cache_hit=True` with the original tokens; per run usage counts them as saved, not billed; per run totals come from the run's own rows. No leak into another run's accounting. The exception is the stale committed B0 report (F7).

## Question 5: runner

- Preflight refuses a stale or missing fingerprint and a different answer prompt hash before any write (`preflight.py`). The fingerprint is a stored label written by the re-ingest script. Today it equals the real chunk columns (recursive-v1, max 200 tokens, model@revision, 298 shared documents). It does not cover judge prompts (F6) or the document set.
- Resume: the primary key (run_id, item_id) prevents duplicate rows; skipping is by existing row. Problems: F2 and F13. A BudgetStop inside an item writes nothing for that item and its generator calls are cached, so the rerun is cheap.
- not_run items (fixtures, non document routes) are rows with status `not_run`, excluded from every n, interval and failure count (`build_report` filters on `status == ok`); gi-079 is listed apart in the report.
- Token accounting: per call `usage` entries are written for new runs. B0 predates them (NULL) and a regenerated report says "not available".
- Judge or generator failure midway: judge `LLMError` is recorded as a status and the item continues (F1); generator `LLMError` becomes an `error` outcome (F13); any other exception stops the run with nothing half written for that item.

## Question 6: honesty of docs and results

Compared evals.md, DECISIONS.md, PLAN.md and `evals/results/*`.
- Calibration: the report, `labels*.yaml`, DECISIONS and PLAN T099 all say Claude drafts and review pending. I found no place that calls them hand labels. Gaps: the evals.md procedure text says "hand-label", PLAN ticks T099 and T100 without the caveat in the title, and the sample is 24 independent items (F5, F17). Key point agreement is 1.000 on natural outputs, which is too good to inform: the judge and the drafter are both LLMs, and the drafter worked in a session that had seen the B0 results.
- "Pass rate" wording: the B0 report separates the strict answerable rate (15 of 30) from the overall rate (27 of 44, which includes 11 correct abstains) and says so. F1 changes what "pass" means when a judge fails.
- B0 threshold: DECISIONS and the tradeoff report agree with my recomputation from `abstain_threshold_tradeoff.json` (rows at 0.50, 0.55, 0.60, 0.65, 0.70 and the 0.63 statement), and its 44 outcomes equal the database. The top-1 scores come from a retrieval re-run that I did not repeat.
- CI gate claim: DECISIONS states what it catches and misses; my reading agrees (F12). The T101 plan line "the workflow has not run on GitHub yet" is stale (the user reports it is green).
- Stale: F7, F9, F16. PRD "set non functional targets at the end of Phase 4" is open (T103) and needs F4 first.

## Question 7: spec traceability (AC-EVL-01 to 07)

- AC-EVL-01 (schema, `verified_by`, `verified_on`): 140 tests, including batch tests over the real files. Covered.
- AC-EVL-02 (retrieval metrics without LLM): hand example metric tests; `runner_09` and `live_01` for no model call. Covered. Citation recall for retrieval only is wrong (F9).
- AC-EVL-03 (one primary label per failed item): `label_01` to `label_14`, `order_01`, `order_02`. Covered. No test enumerates every (behavior, outcome) pair, but the function returns one string by construction. Misnamed: `runner_04` to `runner_08`, `live_02` to `live_04` (F10).
- AC-EVL-04 (cache by hash of prompt, model, parameters): the cache tests are real. Misnamed: `preflight_*`, `usage_*`, the CLI report test (F10).
- AC-EVL-05 (interval for every headline metric): `stats` and `report_*` tests. Abstention rates have no interval (F18).
- AC-EVL-06 (CI fails on regression): decision tests in `ci_gate_compare` and workflow file tests exist. No test runs `ci_gate.py`; no failing end to end run has been seen. Two pyproject tests carry this id wrongly.
- AC-EVL-07 (calibration report: agreement, kappa, interval): real tests in `test_calib_*`. The 19 judge tests also carry this id and test judge behavior instead.
- ACs with no test: none in EVL. Missing PRD criteria for the judges, the runner and the preflight.

## Question 8: secrets and history

Scanned all 405 commits on all refs (`git log --all -p`, added lines) for: `gsk_` + 20 or more, `sk-` + 20 or more, `AKIA` + 16, `npg_` + 8 or more, URL passwords, and assignments to names containing KEY, SECRET, TOKEN or PASSWORD with 32 or more value characters. Matched text was never printed.
- Hits: 5, all in test fixtures in commits 42979048a3 (`tests/api/test_query.py`), e0720da2dd (`tests/core/test_config_placeholders.py`) and b8d87f831d (`tests/core/test_config_llm.py`). They use fake hosts (`db.internal`, `example.com`) and made up values.
- Cross check: I searched the whole history for the actual values of the secrets in the local `.env` (database url and password parts, JWT secret, admin password, Groq key, OpenRouter key). None is present. The Redis url value matches commit e097173 and is a local default, not a secret.
- `.gitignore` covers `.env`, `.env.*`, `.cache/` (ledger and LLM cache), `data/`, `evals/cache/`, `PROJECT_NOTES.md`, `docs/golden_review/`, `docs/calibration/`, REMEMBER, SKILLS, WORKFLOW, COMMITS, REFERENCES and INSTALL. Not covered: `*.db`, `*.sqlite`, `*.pem`, `*.key` (F19). No tracked file is in the ignored sets now.
- Old local notes (INSTALL, COMMITS, REFERENCES, REMEMBER, SKILLS, WORKFLOW) are in history before commit 0c00880.
- **From a secrets point of view the repo is safe to make public.**
- Not covered by my scan: binary blobs, secrets split over lines or encoded, key formats with other prefixes (the OpenRouter, Groq and Neon values were checked only by exact value against the local `.env`), unreachable objects (`git fsck` lists dangling trees, which are not pushed), and anything outside the repo (GitHub secrets, issue text, logs, the Neon console). If any of these credentials was ever pasted somewhere public, rotate it.

## Question 9: CI and tooling

- Workflow logic: two jobs, each with its own pgvector service; `permissions: contents: read`; no `secrets.` use; throwaway secrets masked; the model is fetched at a pinned revision with sha256 per file; the gate exits 1 on any problem and refuses a baseline of another config id or hash. `check_gate` compares drops only. Fine.
- Warnings: the Node 20 actions and the Ubuntu 26 change are real (F11). Also no pip cache, floating service images, ranges with no lock file. Fork pull requests get no secrets, which is fine here.
- Undeclared dependencies: found by importing every module under `src`, `scripts` and `tests` (list in F20). The existing test checks only `src`.

## Question 10: duplication and drift

- `scripts/b0_rows.py` repeats the retrieval call of `LivePipeline.run` (wide retrieve with `top_k = top_n`, random user id). When T109 adds rerank or E7 adds query rewriting to the pipeline, the CI gate and `b0_run` will not follow.
- `b0_summary.label_of` calls labeler functions with a fake outcome: a second path to `retrieval_miss` and `ranking_miss` next to `score_item`.
- Two pass definitions (F1). `RunProgress` is dead code beside DB based resume (F16).
- Scratch logic behind committed numbers: the B0 summary json (F7) and, per DECISIONS, the 3 item smoke run and the first report extras (later moved into code). The abstain analysis and the calibration results are rebuilt by repo scripts (`abstain_sweep.py`, `calibration_report.py`).

## Question 11: risks for Phase 5

- F2, F3, F6 and F8 are the main ones.
- Power: dev has 45 items, 30 answerable, so intervals are about plus or minus 0.15 to 0.2. Effects below roughly 0.15 cannot be told from noise. The test split has 30 verified items, and the structured and mixed items do not exist yet.
- Paired comparison pairs on item id using only items with a value in both runs, so a technique that abstains more changes which items have faithfulness; `compare` also does not check split, judge identity or chunking (F6, F8).
- The same 30 answerable dev items are reused for every technique, so choosing the best of many configs on dev overfits; list every config tried in the results table.
- `GROQ_DAILY_TOKENS` and the pacer limits apply to any model, and only a Groq client is built; E9 on another provider needs new wiring (F14).
- Not computed anywhere: schema validity rate, retry rate, fallback rate and tokens per query gates from the full gate in evals.md.

## What I could not check

- Whether the GitHub workflow passes on a clean runner: no Actions access. The task statement says 1113 tests are green; I did not run the local suite.
- The top-1 dense scores behind the abstain table (needs the embedding model and a re-run); the committed json is consistent with the stored outcomes.
- Whether the judge prompts were tuned on calibration items, and whether the drafter saw judge output: no transcript of the planning chat.
- Correctness of the 75 verified golden items themselves (gold facts and quotes were validated by code only; the human review cannot be audited).
- Live provider behavior (rate limits, reset times, real token counts): no provider call allowed.
- Test split item content: deliberately not read beyond the loader paths.
