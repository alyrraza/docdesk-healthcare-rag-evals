# Phase 2 review: ingestion

Reviewed 2026-10-13 against `docs/PRD.md`. Task T053 of `docs/PLAN.md`. No code was edited.

## Scope reviewed

- Diff range: `adbf0fc` (last commit before T036) to `6aafb16` (tick T052). That is 47 commits, 81 files, 3952 lines added, 24 removed.
- Tasks: T036 to T052.
- Checks run on HEAD (`6aafb16`) in the project venv, with a clean working tree:
  - `ruff check .`: passed.
  - `pytest`: 349 passed, 0 skipped, 0 failed. The integration tests ran against a real Postgres and the `model` tests ran against the real MiniLM ONNX files.
  - `check_file_length.py` and `check_docs_style.py`: no violations.

## Verdict

All five acceptance criteria tagged to this phase (AC-ING-01 to AC-ING-05) are implemented and covered by named tests. No blocking findings. Three tasks ended up different from the plan as written (T044, T040 and the E1 sizes behind T042 and T043), and several changes were made without a plan task. All of these were recorded in `docs/DECISIONS.md`, but `CLAUDE.md` says to stop and ask first, and the history does not show that happened. Details below.

## Acceptance criteria owned by Phase 2

| AC | Status | Covering tests | Implementation |
|---|---|---|---|
| AC-ING-01: upload returns 202 with an id and status `queued`, without waiting for embedding | Implemented | `tests/api/test_documents_upload.py::test_ac_ing_01_upload_returns_202_with_an_id_and_queued_status`, `test_ac_ing_01_upload_without_a_token_is_401`, `test_ac_ing_01_an_empty_upload_is_rejected`, `test_ac_ing_01_a_missing_title_is_rejected`, `test_ac_ing_01_a_file_over_the_size_limit_is_413`, `test_ac_ing_01_the_uploaded_route_needs_login_in_the_openapi_schema`; `tests/ingestion/test_tasks.py::test_ac_ing_01_the_task_has_a_stable_public_name` | `api/routers/documents.py`, `documents/service.py`, `ingestion/tasks.py`, `worker/celery_app.py` |
| AC-ING-02: worker sets `ready` and stores the chunk count | Implemented | `tests/ingestion/test_pipeline.py::test_ac_ing_02_a_good_file_becomes_ready_with_its_chunk_count`; `tests/ingestion/test_tasks.py::test_ac_ing_02_running_the_task_makes_the_document_ready`; `tests/api/test_documents_read.py::test_ac_ing_02_list_shows_my_documents_with_status_and_chunk_count`, `test_ac_ing_02_get_one_returns_its_status_and_failure_reason`; `tests/ingestion/seed/test_loader.py::test_ac_ing_02_ingest_all_marks_good_files_ready_and_reports_bad_ones` | `ingestion/pipeline.py`, `GET /documents`, `GET /documents/{id}` |
| AC-ING-03: failure sets `failed` with a reason and stores no partial chunks | Implemented | `tests/ingestion/test_pipeline.py::test_ac_ing_03_a_file_with_no_text_fails_with_its_reason_and_no_chunks`, `test_ac_ing_03_a_model_crash_fails_the_document_without_leaking_details`, `test_ac_ing_03_a_database_error_on_the_last_chunk_leaves_no_partial_chunks`, `test_ac_ing_03_a_failed_document_can_be_retried_and_becomes_ready`; parser reasons in `tests/ingestion/parsers/test_pdf.py` (no text layer, password protected, corrupt, zero pages) and `test_text.py` (blank, not UTF-8, null bytes); `tests/ingestion/test_tasks.py::test_ac_ing_03_a_failing_file_raises_so_celery_records_the_failure`; `tests/api/test_documents_upload.py::test_ac_ing_03_if_the_queue_is_down_the_document_is_failed_and_the_user_told` | `ingestion/pipeline.py`, `ingestion/errors.py`, `ingestion/parsers/` |
| AC-ING-04: same user, identical content twice, no duplicate chunks | Implemented | `tests/ingestion/test_hashing.py` (4 tests, including the published SHA-256 of `abc`); `tests/api/test_documents_upload.py::test_ac_ing_04_the_same_content_twice_returns_the_first_document`, `test_ac_ing_04_another_user_uploading_the_same_content_gets_their_own_document`; `tests/ingestion/test_pipeline.py::test_ac_ing_04_ingesting_a_ready_document_again_adds_no_chunks`; `tests/ingestion/seed/test_loader.py::test_ac_ing_04_registering_the_same_corpus_twice_creates_nothing_new` | `ingestion/hashing.py`, `documents/service.py`, owner plus hash rule from Phase 1 |
| AC-ING-05: each chunk stores document id, position, token count, chunker version and embedding model version | Implemented | `tests/ingestion/test_pipeline.py::test_ac_ing_05_every_chunk_records_position_tokens_and_versions` (the end to end check); `tests/db/test_chunks_model.py::test_ac_ing_05_chunk_stores_position_token_count_and_versions` (Phase 1 column test); chunker invariants in `tests/ingestion/chunkers/test_fixed.py`, `test_recursive.py`, `test_parent_child.py` (size limit, overlap, every sentence covered, metadata filled); `tests/embeddings/test_encoder.py::test_ac_ing_05_the_model_name_and_revision_are_exposed_for_chunk_rows` | `ingestion/pipeline.py`, `ingestion/chunkers/`, `embeddings/encoder.py` |

Notes on the evidence:
- AC-ING-03 "no partial chunks" has a real failure test: it makes the database fail on the last chunk and then counts rows. It does not only check the status.
- AC-ING-04 is covered at three layers: the hash, the upload route (returns the first document) and the worker (a ready document gets no new chunks). The cross-user test shows the rule is per owner, as the PRD says.
- AC-ING-01 "without waiting for embedding" is proven with a fake queue, so the test shows the route returns after enqueueing, not that a real broker was used. A real Celery plus Redis round trip is not tested in the suite. The T052 corpus run is the only real end to end use of the pipeline.

## Other criteria touched by this phase

| AC | Status | Test | Remaining |
|---|---|---|---|
| AC-RET-05: only chunks from documents the user may access | Partly. The document routes and the seed loader follow the visibility rule (own plus shared). | `tests/api/test_documents_read.py::test_ac_ret_05_list_includes_shared_documents_but_not_other_peoples_private_ones`, `test_ac_ret_05_someone_elses_private_document_looks_like_it_does_not_exist`, `test_ac_ret_05_a_shared_document_can_be_read_by_anyone_signed_in`; `tests/ingestion/seed/test_loader.py::test_ac_ret_05_corpus_files_become_shared_documents_owned_by_the_admin` | The criterion is about chunks. The retrieval query does not exist yet (Phase 3). This closes the observation in the Phase 1 review that no test carried the id. |
| AC-AUTH-03: protected routes give 401 | Covered for the new routes | `tests/api/test_documents_read.py::test_ac_auth_03_both_routes_need_a_token`; `test_documents_upload.py::test_ac_ing_01_upload_without_a_token_is_401` | none |
| AC-AUTH-05: no public route outside the allowlist | Still holds | `tests/api/test_public_routes.py` passes with `documents.router` included | none |
| AC-RET-01: HNSW index | Evidence added | `docs/DECISIONS.md` entry for T052: 99.9 percent of the exact top 10 on 5457 real chunks (298 documents), ef_search 40 | the retrieval query (Phase 3) |

Weak spot: the AC id in a test name is not always the id the test proves. About 37 tests for the seed fetchers (`test_openfda.py`, `test_medlineplus.py`, `test_common.py`, the fetch script tests) carry `ac_ing_01`, but they test downloading and parsing corpus files, not the upload route. The tests are fine. The tag is a convenience, so a reader should not count them as extra evidence for AC-ING-01.

## Tasks skipped or changed from the plan

No task was skipped. All 17 are ticked and each has a feature commit, and almost all have a test commit before it. Tasks that differ from the text in `docs/PLAN.md`:

1. **T044 parent-child chunker: built, but not usable.** The chunker and its tests exist (`1565100`). Then `31577e5` and `5000300` make the pipeline refuse `parent_child`, and `58fccfa` records "deferred" in `DECISIONS.md`. There is no `parent_text` column. The task is ticked, but the strategy cannot be stored or retrieved. This matches the module doc as edited in `58fccfa`, but the ticked task overstates what works. See observation 1.
2. **T042, T043 and E1 sizes changed.** The pipeline refuses a chunk size above the encoder's `max_length` (256 for MiniLM), so the E1 sizes went from 256, 512, 1024 to 128, 200, 256, and baseline B0 from 512 to 200 tokens. This edits `docs/PLAN.md` (T106, T107), `docs/modules/evals.md` and `docs/modules/ingestion.md`. The reason is sound (silent truncation would break the experiment), but it changes the experiment design from the PRD and plan, and the commit is `docs(docs)` with the decision recorded afterwards.
3. **T040 PDF parser: new dependency, new column.** `pypdf` was added to `docs/TECHSTACK.md` in the same feature commit that added it to `pyproject.toml`. Citations need the page, so `chunks.page` and migration `0012` were added (`880598c`, `844d914`). Neither is a plan task.
4. **T040 test replaced.** Commit `87f0864` deleted `test_ac_ing_03_a_pdf_is_recognised_by_its_header_not_its_file_name` from `tests/ingestion/test_dispatch.py`. It asserted that PDF bytes fail with "PDF" (the T039 placeholder behaviour). The new `tests/ingestion/parsers/test_pdf.py::test_ac_ing_03_dispatch_sends_pdf_bytes_to_the_pdf_parser` covers the same dispatch rule, so this is a replacement, not a weakening. The commit message has no body saying so, and the project rule asks for the reason when a test changes.
5. **T048 upload format.** The upload is the raw request body (`POST /documents?title=...`), not multipart, because `python-multipart` is not in `docs/TECHSTACK.md`. This is recorded in `DECISIONS.md` and "revisit at the frontend phase". PRD AC-ING-01 says "a file is uploaded" and does not fix the encoding, so the criterion holds. The frontend will need to send the `File` as the body.
6. **T047 `--pool=solo` note.** Present: `worker/celery_app.py` picks `solo` on Windows, `worker/entry.py` has the command in its docstring, and `docs/REMEMBER.md` explains it. `REMEMBER.md` is local only, so a fresh clone gets only the code comment and the docstring.
7. **T052 size.** 298 documents and 5457 chunks, inside the 200 to 400 target. The seed set is one openFDA label per drug (about 160 names) plus 150 MedlinePlus topics.

## Changed files outside the phase scope

`git diff adbf0fc..HEAD` has no stray feature in `src/`. Every source file maps to a T036 to T052 task. Files that do not map cleanly:

1. `migrations/versions/0012_add_chunk_page.py`, `src/docdesk/db/models/chunks.py`, `tests/db/test_chunks_model.py`, `tests/db/test_migrations.py`. A schema change in a Phase 1 table, driven by T040. No plan task. Tested, and the migration has an up and down test.
2. `pyproject.toml`. Five dependencies added: `tokenizers`, `httpx`, `pypdf`, `onnxruntime`, `numpy`. Four of the five are already listed in `docs/TECHSTACK.md`. Only `pypdf` was added to the list in the same phase. Also a new `model` pytest marker.
3. `src/docdesk/core/config.py` and `.env.example`: `upload_dir`, `model_dir`, `max_upload_bytes`. Needed by T047 and T048, small.
4. `docs/PLAN.md`: ticks, plus the edited text of T106 and T107. `docs/modules/evals.md` and `docs/modules/ingestion.md`: edited for the new E1 sizes and the parent-child deferral. `docs/DECISIONS.md`: four new entries (embedding model, Phase 2 design choices, parent-child deferral, HNSW recall). Ticks and decisions are allowed by `CLAUDE.md`, but editing the experiment design in the plan is more than a tick.
5. `docs/TECHSTACK.md`: the `pypdf` row, see above.
6. `tests/fakes/` (`ingestion.py`, `pdfs.py`) and `tests/ingestion/conftest.py`: shared test helpers, fine.
7. `scripts/fetch_openfda.py`, `scripts/fetch_medlineplus.py`, `scripts/load_corpus.py`: map to T050 to T052.
8. `src/docdesk/ingestion/seed/drug_names.py` (158 lines): a hand-picked list of drug names. Not a rule problem, but the corpus selection is a data decision that Ali should be able to explain.

Behaviour added beyond the written criteria, with tests:
- Re-uploading content whose earlier copy failed re-queues that same document (`test_ac_ing_03_uploading_again_after_a_failure_queues_the_same_document_again`, `test_ac_ing_03_a_failed_document_can_be_retried_and_becomes_ready`). Reasonable, but AC-ING-04 says nothing about retry.
- Upload size limit with 413, empty upload rejected, queue outage marks the document `failed`.
- The parser is chosen from the file bytes (`%PDF-`), not the file name or mime type.

## Observations to decide on

1. **Parent-child is ticked but deferred.** Either leave T044 ticked and keep the note in `DECISIONS.md`, or reopen it as "built, not wired". As it stands the module has code and 9 tests for a strategy the pipeline rejects. Decide whether to keep that code.
2. **Work outside the plan.** The page column, `pypdf`, the E1 size change and the deferral were each decided inside a task. The decisions are recorded afterwards. If the work-loop rule ("not in the plan, stop and ask") is meant literally, these should have been plan edits first. A cheap fix is to add them to `docs/PLAN.md` as tasks, as T044a style notes, so the plan matches the history.
3. **No real broker test.** Celery is tested with an in-process app and a fake queue. Nothing in the suite starts a worker against Redis. The T052 run used the pipeline directly through the loader, not through Celery. AC-ING-01 and AC-ING-02 together depend on that path working. Consider one manual run of `celery -A docdesk.worker.entry worker --pool=solo` and a real upload before Phase 3, and record the result.
4. **Raw body upload.** Revisit at the frontend phase as the decision says. Large files are read up to `max_upload_bytes` (5 MB by default), which is small for real PDFs.
5. **No OCR.** A scanned PDF fails with a clear reason (tested). That is in the PRD scope, but the corpus has no PDFs at all (openFDA and MedlinePlus are text), so the PDF path is only exercised by generated test files, not a real document. Add one real PDF to a manual check.
6. **Security explanations.** Phase 2 has nothing in the "explain line by line" class (auth, SQL validator, rate limiter). The `LocalFileStore` and the seed download folder check (only under `data/` or `.cache/`, source ids cannot escape the folder) are the closest things to security code. Both have tests. A short walk through them for Ali is worth it for the interview rule.

## Recommendation

Phase 2 can be closed. Before Phase 3, decide observations 1 and 2 (what to do with the deferred parent-child code, and whether to write the unplanned work into the plan), and do one manual upload through a real worker (observation 3), because Phase 3 retrieval will rely on chunks that so far were created only through the loader.
