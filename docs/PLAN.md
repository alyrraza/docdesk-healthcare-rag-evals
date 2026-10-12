# Plan

Created 2026-10-13. Ordered tasks. Each task is small enough to finish with one failing test, one
implementation and one or two commits. Tick a box only when the checks pass. If the plan cannot be
followed as written, stop and use the deviation protocol in `WORKFLOW.md`.
AC ids refer to `PRD.md`. Module detail is in `docs/modules/`.

## Cut rules
- Never cut: trace logging, the golden set, baseline B0 numbers, the eval runner, judge calibration.
- If time runs short, cut in this order: frontend polish, E7 and E6, the SQL branch and router, then
  shrink the matrix to E3, E4, E8.
- If Phase 4 baseline numbers do not exist, stop adding features and finish Phase 4 first.
- A new idea mid-phase goes to "Parked ideas" in `DECISIONS.md`, not into the code.

## Phase 0: scaffold and guardrails for the repo itself
- [x] T001 init repo, `.gitignore`, `.gitattributes`, README stub, first commit
- [x] T002 `pyproject.toml`, src layout, ruff and pytest config
- [x] T003 add `scripts/check_file_length.py` with tests
- [x] T004 add `scripts/check_docs_style.py` with tests
- [x] T005 add `scripts/check_commit_msg.py` with tests
- [x] T006 add `.githooks`, set `core.hooksPath`, verify a bad commit is rejected
- [x] T007 add `CLAUDE.md`, `.claude/rules/` and the docs folder
- [x] T008 `core/config.py` settings from environment, fail fast on missing values
- [x] T009 `core/errors.py` error envelope and handler (AC-AUTH-03 shape)
- [x] T010 `core/logging.py` JSON logs with trace id context
- [x] T011 `core/ids.py` and `core/clock.py`
- [x] T012 `api/app.py` factory and `GET /health`
- [x] T013 `.env.example`, README setup section for D: paths

## Phase 1: database and auth
- [x] T014 `db/session.py` engine and per-request session
- [x] T015 Alembic init and first empty migration
- [x] T016 migration: enable pgvector extension
- [x] T017 `users` model, migration and repository
- [x] T018 `auth/passwords.py` hash and verify (AC-AUTH-01)
- [x] T019 `auth/jwt.py` create and decode (AC-AUTH-02)
- [x] T020 `auth/roles.py` and `auth/deps.py` require_user (AC-AUTH-03)
- [x] T021 `require_admin` (AC-AUTH-04)
- [x] T022 `POST /auth/register`
- [x] T023 `POST /auth/login`
- [ ] T024 `api/public.py` allowlist and the route walk test (AC-AUTH-05)
- [ ] T025 `documents` model, migration and repository
- [ ] T026 `chunks` model with vector and tsvector columns, migration
- [ ] T027 vector index choice, measured, recorded in `DECISIONS.md`
- [ ] T028 `prompt_versions` and `active_prompts` models, migration
- [ ] T029 `query_traces` model, migration
- [ ] T030 `eval_runs` and `eval_results` models, migration
- [ ] T031 read-only database role migration
- [ ] T032 Synthea loader script and tables
- [ ] T033 seed admin user script
- [ ] T034 integration test fixtures against a real Postgres
- [ ] T035 phase review in a fresh session against the PRD

## Phase 2: ingestion
- [ ] T036 `embeddings/tokenizer.py` token counting
- [ ] T037 `embeddings/encoder.py` ONNX session, batching
- [ ] T038 encoder test with a tiny fixture and shape checks
- [ ] T039 `ingestion/parsers/text.py`
- [ ] T040 `ingestion/parsers/pdf.py` and the no-text-layer failure
- [ ] T041 `ingestion/cleaner.py`
- [ ] T042 `chunkers/fixed.py` with invariants tests
- [ ] T043 `chunkers/recursive.py`
- [ ] T044 `chunkers/parent_child.py`
- [ ] T045 `ingestion/hashing.py` duplicate detection (AC-ING-04)
- [ ] T046 `ingestion/pipeline.py` transactional ingest (AC-ING-02, AC-ING-03, AC-ING-05)
- [ ] T047 Celery app and task, Windows `--pool=solo` note
- [ ] T048 `POST /documents` returns 202 (AC-ING-01)
- [ ] T049 `GET /documents` and status
- [ ] T050 seed corpus fetcher: openFDA labels
- [ ] T051 seed corpus fetcher: MedlinePlus topics
- [ ] T052 seed corpus loader and a 200 to 400 document ingest run
- [ ] T053 phase review

## Phase 3: naive RAG end to end
- [ ] T054 `retrieval/dense.py` (AC-RET-01)
- [ ] T055 `retrieval/keyword.py` (AC-RET-02)
- [ ] T056 `retrieval/access.py` filter in SQL (AC-RET-05)
- [ ] T057 `retrieval/fusion.py` RRF (AC-RET-03)
- [ ] T058 `retrieval/retriever.py` config driven, with timings
- [ ] T059 `llm/client.py` interface and fake for tests
- [ ] T060 first real provider adapter
- [ ] T061 `llm/retry.py` backoff and timeouts
- [ ] T062 `llm/cost.py` price table (AC-OBS-03)
- [ ] T063 `prompts/loader.py` front matter and content hash
- [ ] T064 `prompts/renderer.py` delimiters and escaping (AC-CTX-03)
- [ ] T065 `prompts/registry.py` sync and active pointer (AC-PRM-01)
- [ ] T066 `prompts/bundle.py` bundle id (AC-PRM-03)
- [ ] T067 `context/budget.py` and `context/packer.py` (AC-CTX-01, AC-CTX-02)
- [ ] T068 `generation/schema.py` from `OUTPUTS.md`
- [ ] T069 `guardrails/output.py` three layers (AC-GEN-01)
- [ ] T070 `guardrails/citations.py` (AC-GEN-02)
- [ ] T071 `generation/repair.py` and retry once, typed fallback (AC-GEN-04)
- [ ] T072 abstain on weak retrieval (AC-GEN-03)
- [ ] T073 `guardrails/policy.py` disclaimer by code (AC-GEN-06)
- [ ] T074 `generation/answer.py` full flow
- [ ] T075 `observability/trace.py` builder and writer (AC-OBS-01)
- [ ] T076 `POST /query` end to end
- [ ] T077 prompt unit tests for `answer.v1` (AC-PRM-04)
- [ ] T078 manual smoke test, ten questions, notes in `PROJECT_NOTES.md`
- [ ] T079 phase review

## Phase 4: golden set, eval harness, baseline
- [ ] T080 golden item schema and validator (AC-EVL-01)
- [ ] T081 golden loader with split handling
- [ ] T082 golden items batch 1, single fact, 10 items, hand verified
- [ ] T083 golden items batch 2, single fact, 21 items
- [ ] T084 golden items batch 3, multi chunk, 19 items
- [ ] T085 golden items batch 4, unanswerable, 19 items
- [ ] T086 golden items batch 5, adversarial, 6 items
- [ ] T087 `evals/metrics/retrieval.py` recall@k, MRR, hit rate (AC-EVL-02)
- [ ] T088 `evals/stats.py` bootstrap and paired comparison (AC-EVL-05)
- [ ] T089 `evals/cache.py` disk cache for LLM calls (AC-EVL-04)
- [ ] T090 `evals/judges/faithfulness.py` labels, code computes score
- [ ] T091 `evals/judges/correctness.py`
- [ ] T092 `evals/metrics/citation.py` and `abstention.py`
- [ ] T093 `evals/labeler.py` failure labels (AC-EVL-03)
- [ ] T094 `evals/runner.py` with a fake pipeline test
- [ ] T095 `evals/report.py` tables with intervals
- [ ] T096 `evals/cli.py`
- [ ] T097 run baseline B0 retrieval-only, commit numbers
- [ ] T098 run baseline B0 full on dev, commit numbers
- [ ] T099 build the judge calibration set, 40 outputs, hand labeled
- [ ] T100 `evals/calibration.py` agreement, kappa, interval (AC-EVL-07)
- [ ] T101 CI workflow: lint, test, retrieval-only gate (AC-EVL-06)
- [ ] T102 set tolerances from measured intervals, record in `DECISIONS.md`
- [ ] T103 set non-functional targets in `PRD.md` from the baseline
- [ ] T104 phase review

## Phase 5: technique matrix
- [ ] T105 config variants plumbing: chunk size, strategy, mode, rerank, top-k as config only
- [ ] T106 E1 chunk size 256, 512, 1024: run and record
- [ ] T107 E2 chunking strategy: run and record
- [ ] T108 E3 dense, keyword, hybrid: run and record
- [ ] T109 `embeddings/reranker.py` ONNX cross-encoder and `retrieval/rerank_stage.py` (AC-RET-04)
- [ ] T110 E4 reranker on and off: run and record
- [ ] T111 E5 top-k 3, 5, 10 and context budget: run and record
- [ ] T112 E6 second embedding model: run and record (cuttable)
- [ ] T113 `prompts/answer.v2` strict version, prompt tests, E8 run and record
- [ ] T114 `prompts/answer.v3` structured version, E8 run and record
- [ ] T115 E9 stronger generator model: run and record
- [ ] T116 results table generator and the quality, cost, latency plot
- [ ] T117 README results section with the table and the interpretation
- [ ] T118 `scripts/check_ac_coverage.py`: every AC id appears in a test name, wire into CI
- [ ] T119 phase review

## Phase 6: guardrails, limits, cache, prompts admin, SQL
- [ ] T120 `guardrails/input.py` length, PII flag, injection heuristics (AC-GRD-02)
- [ ] T121 policy refusal for diagnosis and dose (AC-GEN-05)
- [ ] T122 injection test on the adversarial slice (AC-GRD-01)
- [ ] T123 `ratelimit/token_bucket.py` with Lua (AC-LIM-01), explained to Ali
- [ ] T124 `ratelimit/budget.py` daily budget (AC-LIM-02)
- [ ] T125 Redis down behavior (AC-LIM-03)
- [ ] T126 `cache/semantic.py` (AC-CAC-01, AC-CAC-02)
- [ ] T127 E10 cache wrong-hit measurement, then enable decision
- [ ] T128 `observability/metrics.py` and `/metrics` (AC-OBS-02)
- [ ] T129 admin prompt endpoints and activation pointer (AC-PRM-02)
- [ ] T130 regression slice: add failures from eval runs
- [ ] T131 `sql/schema_allowlist.py`
- [ ] T132 `sql/validator.py` and its table of cases (AC-SQL-01, AC-SQL-02), explained to Ali
- [ ] T133 `sql/executor.py` read-only, limit, timeout (AC-SQL-03)
- [ ] T134 `sql/generator.py` and `text2sql.v1` tests
- [ ] T135 `sql/service.py` safe failure (AC-SQL-04)
- [ ] T136 `router/classifier.py` with fallback (AC-RTR-01, AC-RTR-02)
- [ ] T137 golden items: structured 19 and mixed 6, hand verified
- [ ] T138 SQL and router eval metrics and a run
- [ ] T139 phase review

## Phase 7: frontend, delivery, documentation
- [ ] T140 Vite React TypeScript scaffold
- [ ] T141 `api/` client and types
- [ ] T142 login and register page (AC-FE-01)
- [ ] T143 upload panel and status polling
- [ ] T144 chat page, answer card, abstain state
- [ ] T145 citation list with source chunk reveal (AC-FE-02)
- [ ] T146 dashboard: stage latency and cost (AC-FE-03)
- [ ] T147 dashboard: failure labels and prompt versions
- [ ] T148 Dockerfile for the API
- [ ] T149 Dockerfile for the worker
- [ ] T150 `docker-compose.yml`
- [ ] T151 CI job that builds both images (AC-DKR-01)
- [ ] T152 final eval run on the held-out test split, commit the numbers
- [ ] T153 README: architecture, setup, Docker, results, limitations, honest status
- [ ] T154 final review in a fresh session against the whole PRD
- [ ] T155 `PROJECT_NOTES.md` completed, LinkedIn draft after the README is done
