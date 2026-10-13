# Phase 3 review: naive RAG end to end

Reviewed 2026-10-13 against `docs/PRD.md`. Task T079 of `docs/PLAN.md`. No code was edited.

## Scope reviewed

- Diff range: `cc5d46f` (tick T053, last commit before T054) to `1e9cdf0` (HEAD). That is 56 commits, 81 files, 4400 lines added, 51 removed. All commits are by one author.
- Tasks: T054 to T078 and T078a.
- Checks run on HEAD (`1e9cdf0`) in the project venv, with a clean working tree:
  - `ruff check .`: passed.
  - `pytest -q`: all passed, 0 failed (555 tests counted from the progress dots; the summary line was not captured).
  - `check_file_length.py` and `check_docs_style.py`: no output, no violations.
- Two small probes were run against the renderer and the citation check to confirm findings S1 and S2. They changed no files.

## Verdict

Every acceptance criterion this phase owns is implemented and has named tests, with the gaps listed below (AC-OBS-01 is only partly met). Test first order holds for every feature commit. There are no stray source files and no new dependency. The access filter is sound. The renderer and output guardrails have two low severity gaps (S1, S2), one of which is a real injection path that the tests do not cover. No blocking findings. Four things need a decision from Ali: the T078a ordering, the empty abstain threshold, the missing API level cross user test, and S1.

## Acceptance criteria owned by Phase 3

| AC | Status | Covering tests | Implementation |
|---|---|---|---|
| AC-RET-01 dense top-N by cosine | Implemented | `tests/retrieval/test_dense.py::test_ac_ret_01_the_closest_chunk_comes_first_with_score_one`, `test_ac_ret_01_top_n_limits_the_number_of_results`, `test_ac_ret_01_a_hit_carries_its_document_title_and_text`, `test_ac_ret_01_a_user_with_no_documents_gets_an_empty_list`; `tests/retrieval/test_retriever.py::test_ac_ret_01_dense_mode_returns_only_the_dense_leg`; HNSW index: `tests/db/test_chunks_model.py::test_ac_ret_01_embedding_column_has_an_hnsw_cosine_index` | `retrieval/dense.py` |
| AC-RET-02 keyword top-N, Postgres FTS | Implemented | `tests/retrieval/test_keyword.py::test_ac_ret_02_only_chunks_containing_the_term_are_returned`, `..._stemming_matches_word_forms`, `..._the_chunk_with_more_matching_terms_ranks_first`, `..._a_query_of_only_stop_words_returns_nothing_not_an_error`, `..._punctuation_and_operators_in_a_question_do_not_break_the_query`; `test_retriever.py::test_ac_ret_02_keyword_mode_returns_only_the_keyword_leg` | `retrieval/keyword.py` |
| AC-RET-03 RRF, ties by chunk id | Implemented | `tests/retrieval/test_fusion.py::test_ac_ret_03_scores_are_hand_computed_sums_of_one_over_k_plus_rank`, `..._a_chunk_found_by_both_legs_is_marked_both`, `..._ties_break_on_chunk_id`, `..._empty_lists_fuse_to_an_empty_list`, `..._output_is_a_sorted_permutation_of_the_union_of_the_inputs`; `test_retriever.py::test_ac_ret_03_hybrid_mode_fuses_both_legs_and_keeps_top_k` | `retrieval/fusion.py`, `retrieval/retriever.py` |
| AC-RET-04 rerank | Not in this phase | none | Phase 5. No reranker code exists, correctly. |
| AC-RET-05 only accessible chunks | Implemented in SQL | `tests/retrieval/test_access.py`: `..._another_users_private_chunk_is_never_returned`, `..._the_owner_sees_their_own_chunk`, `..._shared_corpus_chunks_are_visible_to_everyone`, `..._chunks_of_documents_that_are_not_ready_are_hidden` (each runs both legs). Phase 2 route tests also carry the id. | `retrieval/access.py`. See the security section and gap G3. |
| AC-GEN-01 parse into `AnswerOutput` | Implemented | `tests/generation/test_schema.py` (6 tests: valid, field order, enum, missing field, extra field, abstain sentence); `tests/generation/test_output_guardrails.py::test_ac_gen_01_layer_one_*`, `layer_two_*`, `layer_three_*`; `test_answer.py::test_ac_gen_01_*`; `tests/api/test_query.py::test_ac_gen_01_a_question_gets_an_answer_with_citations_and_the_disclaimer` | `generation/schema.py`, `guardrails/output.py` |
| AC-GEN-02 reject citation outside retrieved set | Implemented | `test_output_guardrails.py::test_ac_gen_02_a_citation_of_an_id_that_was_not_retrieved_is_rejected`, `..._evidence_used_is_checked_too`, `..._check_fields_runs_the_membership_check`; `test_answer.py::test_ac_gen_02_a_citation_of_an_unretrieved_id_triggers_the_retry`; `test_answer_prompt.py::test_ac_prm_04_an_injected_citation_of_a_missing_id_does_not_change_the_output_fields` | `guardrails/citations.py`. Checks labels in the prompt, which map to retrieved chunk ids. |
| AC-GEN-03 abstain below threshold, no generator call | Implemented, threshold is a placeholder | `tests/generation/test_abstain.py` (4 tests); `test_answer.py::test_ac_gen_03_empty_retrieval_abstains_without_calling_the_model`, `..._a_weak_best_score_abstains_without_calling_the_model`; `tests/api/test_query.py::test_ac_gen_03_a_user_with_no_matching_documents_gets_an_abstain_and_no_model_call` | `generation/abstain.py`. See gap G2. |
| AC-GEN-04 retry once with the error, then typed fallback `system_error` | Implemented | `test_answer.py::test_ac_gen_04_invalid_json_is_retried_once_with_the_exact_error_in_the_prompt`, `..._two_invalid_replies_give_the_typed_fallback_and_never_a_third_call`, `..._a_reply_cut_off_by_the_length_limit_counts_as_invalid`, `..._a_provider_failure_gives_the_fallback_instead_of_raising`; `test_repair.py`; `tests/prompts/test_repair_render.py` (7 tests); `tests/llm/test_retry.py` (7 tests); `tests/api/test_query.py::test_ac_gen_04_a_model_failure_returns_the_typed_fallback_and_a_trace` | `generation/answer.py`, `generation/repair.py`, `llm/retry.py` |
| AC-GEN-05 refuse personal diagnosis or dose | Implemented as a first filter | `tests/guardrails/test_input_policy.py` (4 tests: dose, diagnosis, label question not refused, case and spacing); `tests/api/test_query.py::test_ac_gen_05_a_personal_dose_question_is_refused_with_the_policy_message_and_no_model_call`, `..._a_what_does_the_label_say_dose_question_is_still_answered`; `tests/generation/test_policy.py::test_ac_gen_05_the_refusal_message_points_to_a_professional` | `guardrails/input.py`, `query/service.py`. See S5. |
| AC-GEN-06 disclaimer appended in code | Implemented | `tests/generation/test_policy.py::test_ac_gen_06_*` (4 tests, including "not added twice"); the API test for AC-GEN-01 checks the disclaimer on the response | `guardrails/policy.py`, `generation/answer.py:finish` |
| AC-CTX-01 never exceed input token budget | Implemented for the evidence slot | `tests/context/test_budget.py` (4 tests); `tests/context/test_packer.py::test_ac_ctx_01_packed_evidence_never_exceeds_the_budget_for_random_inputs` (random inputs), `..._a_chunk_is_never_cut_in_half`, and the dedupe, cap and threshold tests | `context/budget.py`, `context/packer.py`. See gap G4. |
| AC-CTX-02 drop lowest ranked first, record dropped ids | Implemented | `test_packer.py::test_ac_ctx_02_when_evidence_does_not_fit_the_lowest_ranked_are_dropped_first`, `..._dropped_ids_are_recorded_for_the_trace`, `..._the_kept_items_are_always_a_prefix_of_the_ranking`; `test_answer.py::test_ac_ctx_02_used_and_dropped_ids_are_returned_for_the_trace` | `context/packer.py`, `observability/trace.py` |
| AC-CTX-03 untrusted data delimiters, never in instructions | Implemented, two escape gaps | `tests/prompts/test_renderer.py::test_ac_ctx_03_*` (7 tests); `test_answer.py::test_ac_ctx_03_the_request_carries_the_question_and_the_evidence_inside_delimiters`; `test_answer_prompt.py::test_ac_prm_04_an_injected_instruction_stays_inside_the_evidence_block` | `prompts/renderer.py`. See S1 and S2. |
| AC-PRM-01 released version is immutable | Implemented | `tests/prompts/test_registry.py::test_ac_prm_01_editing_a_released_version_is_refused`, `..._a_draft_may_still_change`, `..._a_new_version_is_a_new_row_next_to_the_old_one`, `..._syncing_the_same_files_again_changes_nothing`, `..._a_new_file_is_stored_as_a_version_row`; `tests/prompts/test_prompt_loader.py::test_ac_prm_01_*` (7 tests: front matter, sections, hash ignores CRLF but not edits, malformed files) | `prompts/loader.py`, `prompts/registry.py` |
| AC-PRM-02 activate changes only the pointer | Function level only | `test_registry.py::test_ac_prm_02_activating_moves_only_the_pointer`, `..._activating_an_unknown_version_is_an_error`; `tests/db/test_prompt_tables.py::test_ac_prm_02_activating_only_moves_the_pointer` | `registry.activate`. The admin route is Phase 6. `get_answer_prompt` reads the pointer per request, so "no deploy" holds. |
| AC-PRM-03 bundle id on every trace | Implemented, except refused requests | `tests/prompts/test_bundle.py` (4 tests); `tests/api/test_query.py::test_ac_obs_01_every_request_leaves_one_trace_row_with_the_bundle_and_config_ids` | `prompts/bundle.py`, `query/service.py`. A refusal calls `trace.add_answer(result, None)`, so its trace has no bundle id. No model is called then, so this is harmless, but "every trace" is literal. |
| AC-PRM-04 prompt unit tests for every active prompt | Implemented for `answer.v1` | `tests/prompts/test_answer_prompt.py` (8 tests: schema and sampling declared, enum values named, abstain example present, well formed reply parses, citations subset of prompt ids, empty evidence means no call, injected instruction stays inside block, injected citation of a missing id) | `prompts/answer/answer.v1.md`. `test_prompt_loader.py::test_ac_prm_01_every_shipped_prompt_loads_and_file_names_match_front_matter` means a new prompt is loaded, but a new prompt does not force new unit tests. |
| AC-OBS-01 one trace row per request with the listed fields | Partly | `tests/observability/test_trace.py` (8 tests); `tests/db/test_query_traces_table.py::test_ac_obs_01_trace_round_trips_with_json_fields`; `tests/api/test_query.py::test_ac_obs_01_every_request_leaves_one_trace_row_with_the_bundle_and_config_ids` | `observability/trace.py`. Present: stage latencies, tokens, cost, bundle id, config id, retrieved, used and dropped ids, input guardrail outcome, validation flags. `cache_hit` is always `False` because the cache is Phase 6. Output guardrail outcomes are in `validation` (flags, raw output kept) but not in `guardrails`, which only holds the input decision. |
| AC-OBS-02 `/metrics` | Not in this phase | none | Phase 6. |
| AC-OBS-03 cost from tokens and versioned price table | Implemented | `tests/llm/test_cost.py` (5 tests, including unknown model is an error and the table has a dated version); `tests/llm/test_client.py`, `test_groq.py::test_ac_obs_03_the_result_has_text_tokens_finish_reason_model_and_cost`; `test_answer.py::test_ac_obs_03_tokens_and_calls_are_added_up_over_the_retry` | `llm/cost.py`, `generation/answer.py:account` |
| AC-AUTH-03, AC-AUTH-05 for the new route | Holds | `tests/api/test_query.py::test_ac_auth_03_a_query_without_a_token_is_401`; the public route allowlist test still passes with `query.router` included | `api/routers/query.py` declares `Depends(require_user)` |

Note on tags: the `ac_gen_01` tag on `tests/core/test_config_llm.py` (default models differ, startup fails if generator equals judge) and on the Groq client tests is a convenience. Those tests prove the model settings and the adapter, not the schema parse. Do not count them as extra evidence for AC-GEN-01. Same for the `ac_obs_03` tag on the client and fake tests.

## Tasks skipped or changed from the plan

No task was skipped. All 26 are ticked, T079 (this review) is not. Test commit comes before feature commit for every group (`cacdf15`, `4d95fe5`, `877d91a`, `2781887`, `325547d`, `854b6da`, `4297904`, `4474083`). Items that differ from the plan as written:

1. **T078a was built before it was in the plan.** The failing tests (`4474083`) and the feature (`0b4032c`) come first. The plan line and the decision entry arrive in `a2506bc`, after the code. `PROJECT_NOTES.md` shows the smoke test found the gap and the decision note says the reading was "agreed with the owner", so the intent was approved. But the order breaks step 1 of the work loop ("if the work is not in the plan, stop and ask"), and AC-GEN-05 had no task until then.
2. **T067 packer does more than the plan names.** It also drops near duplicates (word overlap of 0.8 within one document), caps chunks per document (default 2) and has an optional `min_score`. All have tests. The cap hurt the smoke test (metoclopramide side effects abstained although dense put the right label first), and was left alone as experiment E5 (`fba1bee` records it as a known weakness). `min_score` is not passed by `generate_answer`, so it is unused code today.
3. **T060 first provider is Groq.** Models, limits and the "same provider weakness" are in `DECISIONS.md` (`b0ed788`).
4. **T061 gained a retry for the provider's JSON validation failure** (`9488de9`, test first in `eb534c8`) and **error codes kept in messages** (`70b974e`, test first in `fd5d07b`). Both were found by the T078 smoke test. Neither is a plan task. Both are small, tested, and fix real failures.
5. **T077 is test only** (`3882d72`, with `de64810` renaming an expectation). `answer.v1.md` was edited first in `b3e69f1` to add the repair section and the JSON instruction. The prompt is still `status: draft`, so editing it does not break AC-PRM-01.
6. **T078 smoke test notes** are in `PROJECT_NOTES.md`, which is local. The three open questions there (per document cap, input guardrail task, how to run eval days) are now answered by T078a and the Phase 4 insert, except the cap.
7. **T089 was moved into Phase 4 as T079b**, and T079a to T079e were inserted before the golden set (`f9f310c`, `ddd15e0`, `1e9cdf0`). This is planning for Phase 4, committed after T078a, and sits outside this phase's scope.

## Changed files outside the phase scope

Every file under `src/` maps to a T054 to T078a task. No migration was added: the prompt and trace tables came from Phase 1. `pyproject.toml` is untouched, so no dependency was added. The notes say a small front matter parser was written instead of using PyYAML, which is correct under the dependency rule.

Files that do not map to a task, or were touched for another reason:

1. `tests/conftest.py` and deletion of `tests/db/conftest.py` (`b316400`): the `db_session` fixture moved so `tests/retrieval/` can use it. A separate `refactor` commit, so the rule against mixing refactor and feature holds.
2. `src/docdesk/core/config.py`, `.env.example`, `tests/core/test_config_llm.py`: LLM keys and four model ids, plus a startup check that generator and judge differ and that cross check models end in `:free`. Needed by T059 and T060, but there is no plan line for config.
3. `src/docdesk/api/query_deps.py`, `api/schemas/query.py`, `query/service.py`, `generation/result.py`, `guardrails/errors.py`, `guardrails/input.py`: support files for T074, T076 and T078a. Each is one responsibility and under 200 lines.
4. `scripts/smoke_llm.py`: T078. It calls the real provider and activates the prompt, so it is the only code path that runs `sync_prompts` and `activate` in practice. See gap G5.
5. `docs/PLAN.md` (ticks, T078a, the Phase 4 insert), `docs/DECISIONS.md` (three entries: LLM models and limits, AC-GEN-05 reading, eval pacing), `docs/modules/evals.md` (+86 lines, the eval budget and pacing section). The last of these and the Phase 4 insert are not Phase 3 work.
6. `tests/fakes/corpus.py`, `tests/fakes/llm.py`, `tests/retrieval/conftest.py`: shared test helpers, fine.

## Security review

### Access filter (`retrieval/access.py`): sound

- One function, `restrict_to_visible`, joins `chunks` to `documents` and applies `status = ready AND (owner_id = user OR is_shared)` inside the SQL. Both `dense_search` and `keyword_search` call it before `order_by` and `limit`, so the limit cannot be filled with hidden rows and then trimmed. There is no Python side post filter that could be skipped.
- `user_id` is a required argument all the way from `claims.user_id` in the route to the query. It cannot be omitted or defaulted.
- Questions never reach SQL as text: the dense leg sends a vector, and the keyword leg passes the question as a bound parameter to `websearch_to_tsquery`. The test with operators and punctuation shows no breakage.
- Only ready documents are visible, so half ingested chunks never leak (tested).
- The citation payload returned to the client comes only from packed items, which come only from filtered retrieval.

Gaps:
- **G3**: all four tests call the legs directly. There is no `/query` test with two users, so nothing proves the whole path (route, retriever, packer, response) never shows user B a user A chunk. `retrieval/retriever.py` has no test that a hybrid result excludes another user's chunk either. Add one API level test.
- The rule is enforced by every leg remembering to call `restrict_to_visible`. A new leg in Phase 5 (reranker input, parent expansion) or Phase 6 (SQL branch, cache) could skip it, and no test scans for that. A test that runs every leg of the retriever against a hidden chunk would turn the convention into a check. The semantic cache in Phase 6 deserves the same test, because a cache keyed on the question alone would bypass this filter.

### Prompt renderer (`prompts/renderer.py`): good design, two gaps

What is right:
- `check_template` refuses an untrusted variable in the system section and refuses one that is not wrapped in its own tag in the user section. Tests cover both.
- Substitution is one pass (`VARIABLE.sub`), so `{{question}}` inside evidence is not expanded (tested).
- Missing and unknown variables are errors, not empty strings.
- `escape_delimiters` is case insensitive and tolerates spaces and newlines before `>`; `</EVIDENCE>` and `</evidence\n>` are neutralised (probe confirmed).
- Retrieved text, document titles and the previous output are all passed through the same function, because titles are part of `evidence_text`.

Findings:

- **S1 (low to medium): the repair message is not escaped.** `repair_prompt` builds `validation_error` from the exact text of the failure, and the repair section places `{{validation_error}}` as plain instructions, outside any tag, because `untrusted` lists only `evidence` and `previous_output`. `check_citations` echoes model supplied strings: `unknown evidence ids: <whatever the model put in citations>`, with no length cap (confirmed by probe: an id of `IGNORE ALL RULES` appears verbatim). `parse_answer` also echoes JSON key names from an `extra_forbidden` error, capped at 500 characters. A poisoned chunk can make the model emit such a string, and it is then fed back as an unmarked instruction on the single retry. The impact is bounded: one retry, no tools, and the retry output goes through the same layers. It is still the one place where retrieved text can reach the instruction side. Fix options: mark `validation_error` untrusted and wrap it in a tag in the repair section, or keep only the layer name and a fixed message plus a count.
- **S2 (low): two delimiter forms are not escaped.** The regex `<(/?)\s*(tag)\s*>` leaves `< /evidence>` and `</evidence foo>` untouched (confirmed by probe). A model may or may not treat them as closing tags. The tests only try `</evidence>` and `<EVIDENCE>`. Easy fix: escape any `<` that is followed by optional `/`, optional spaces and the tag name, whatever comes after, or escape every `<` in untrusted values.
- **S3 (info): the question is not delimited.** `{{question}}` sits in the user section, outside `untrusted`, so a user can type `</evidence>` and fake the end of the block. The user can only influence their own answer, and the access filter and label check still apply. The question length is capped at 1000 characters. A `<question>` tag would be cleaner and cheap.
- **S4 (info): a label is not tied to a chunk by the model's text.** Chunk text can contain `[c2]`, and layer 2 only checks that cited labels exist in the prompt. Layer 3 flags numbers missing from cited evidence but only flags, and never edits (by design). Claims versus citations are a Phase 4 faithfulness question.
- Unit tests in `test_answer_prompt.py` check that an injected instruction stays inside the evidence block and that a fake citation does not change the output fields. Both pass with the fake model, so they prove the structure, not the real model's behaviour.

### Output guardrails (`guardrails/output.py`, `citations.py`, `policy.py`): solid

- Layer 1 uses `model_validate_json` with `extra="forbid"`, so no guessing at fields. Layer 2 catches contradictions (abstained with citations, citation not in `evidence_used`, wrong abstain sentence). Layer 3 flags numbers.
- A reply cut off by the length limit is treated as invalid (`finish_reason == "length"`), tested.
- The disclaimer is added in `finish()` after the model is done, so no model output can drop it, and a double add is prevented (tested). The fallback and the abstain paths go through the same function.
- `with_disclaimer` checks `endswith(DISCLAIMER)`, so a model that copies the disclaimer in its answer is not duplicated. Fine.
- `abstain_output` and `refusal_result` build the typed answers in code, never from model text.
- `fallback` stores the raw output in `raw_output`; `QueryOut` does not return it. The trace stores only `raw_output_kept: true`, not the text, so nothing sensitive is written there. The log line for a failed validation prints the OutputError message, which carries the S1 string, so a log reader should treat it as untrusted too.
- **S5 (low): the input policy is a first filter.** The decision doc says so and lists known limits. One miss I checked by reading the patterns: "Is it ok for me to take 500 mg?" has a person word but no dose cue, so it is not refused. Over refusal is also accepted ("when unsure, refuse"). Nothing on the output side detects a personal dose in the model's reply, and the model has no path to use `unsafe_request` that code checks. Phase 4's policy slice is where the miss rate gets measured. Until then, AC-GEN-05 is true for the phrasings in the tests and no more.

## Other gaps and observations

- **G1: AC-OBS-01 `cache_hit` and output guardrail outcomes.** See the table. Either record the output layer result in `guardrails` (for example `output: passed | retried | failed`) now, or note that the cache field is a placeholder until Phase 6.
- **G2: abstain threshold is 0.0.** `ABSTAIN_POLICY = AbstainPolicy({}, default=0.0)` means only an empty retrieval abstains, so the `weak_evidence` path never fires in the live route. The code is tested with other thresholds. `PROJECT_NOTES.md` notes RRF scores are tiny (max about 0.033), which makes a threshold on the fused score weak. This is planned for Phase 4. Until then do not describe AC-GEN-03 as protecting against weak evidence in demos.
- **G4: token counts use the MiniLM tokenizer, the generator has its own.** Prompts measured 800 to 1500 tokens against a 6000 budget in the smoke test, so it does not matter yet, but AC-CTX-01 is measured in the wrong unit. The packer budgets the evidence slot only; system prompt and question are not measured against the total. Both are far from the limit with the current settings.
- **G5: `sync_prompts` and `activate` run only from `scripts/smoke_llm.py`.** On a fresh database `POST /query` returns 503 `prompt_not_active` until someone runs the script. There is no startup sync. Phase 6 (prompts admin) probably fixes it, but note it for deployment and for the golden set runs.
- **G6: `write_trace` swallows `SQLAlchemyError`.** It logs the trace id and the error type and returns `False`, and a test covers it. The rule says no swallowed errors, but this is a deliberate exception (a trace failure must not fail the user), and it is logged. The return value is ignored by the service, so a lost trace is visible only in the log. A counter in Phase 6 would close this.
- **G7: one real provider, one real model, one real run.** All model behaviour in tests is scripted. The only live evidence is the ten question smoke run (7 of 8 answerable questions cited, the out of scope question abstained, one wrong abstain from the document cap). Nothing is measured yet.

## Decisions for Ali

1. **S1 and S2**: fix before Phase 4? Both are small. Proposed: add `validation_error` to the untrusted list with a `<validation_error>` tag, cap it at 300 characters, and widen the escape regex. Tests first, in a `fix(prompts)` commit.
2. **G3**: add the `/query` two user test now. It is the best single check on AC-RET-05.
3. **T078a ordering**: record in `DECISIONS.md` that it was built before it was in the plan, or accept the history as it is.
4. **G2 / G1**: confirm both are left for Phase 4 and Phase 6 as planned.
5. **Per document cap of 2**: still open (experiment E5). It changes real answers today.
