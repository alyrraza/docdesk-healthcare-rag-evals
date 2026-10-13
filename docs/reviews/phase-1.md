# Phase 1 review: database and auth

Reviewed 2026-10-13 against `docs/PRD.md`. Task T035 of `docs/PLAN.md`. No code was edited.

## Scope reviewed

- Diff range: `741eb20` (tick T013, last Phase 0 commit) to `9e50ffe` (tick T034). That is 86 commits, 73 files, 3557 lines added.
- Tasks: T014 to T034.
- Checks run on HEAD (`0c00880`) in the project venv. HEAD includes the post phase commits listed below, so the results cover the phase plus those:
  - `ruff check .`: passed.
  - `pytest -q`: 152 passed, 0 skipped, 0 failed. The integration tests ran against a real Postgres.
  - `check_file_length.py` and `check_docs_style.py`: no violations.

## Verdict

All five acceptance criteria tagged to this phase (AC-AUTH-01 to AC-AUTH-05) are implemented and covered by named tests. The schema work (T025 to T031) lays groundwork for criteria that belong to later phases. Those are not implemented yet and are listed separately below. There are no blocking findings. There are four observations to decide on before Phase 2.

## Acceptance criteria owned by Phase 1

| AC | Status | Covering tests | Implementation |
|---|---|---|---|
| AC-AUTH-01: store a salted hash, never the password | Implemented | `tests/auth/test_passwords.py::test_ac_auth_01_password_is_hashed`, `test_ac_auth_01_hash_is_salted`, `test_ac_auth_01_correct_password_verifies`, `test_ac_auth_01_wrong_password_fails`, `test_ac_auth_01_malformed_hash_fails_instead_of_raising`; `tests/api/test_register.py::test_ac_auth_01_register_stores_a_hash_and_never_the_password` (reads the `users` table and checks for an argon2 hash) | `auth/passwords.py`, `auth/service.py`, `POST /auth/register` |
| AC-AUTH-02: login returns a JWT with `sub`, `role`, `exp` | Implemented | `tests/auth/test_jwt.py::test_ac_auth_02_token_carries_sub_role_and_exp` (asserts the claim set is exactly those three), `test_ac_auth_02_expiry_follows_the_configured_lifetime`, `test_ac_auth_02_expired_token_is_rejected`; `tests/api/test_login.py::test_ac_auth_02_login_returns_a_token_with_sub_role_exp` | `auth/jwt.py`, `POST /auth/login` |
| AC-AUTH-03: missing, malformed or expired token gives 401 in the error envelope | Implemented | `tests/auth/test_deps.py::test_ac_auth_03_missing_token_gives_401_envelope`, `test_ac_auth_03_malformed_token_gives_401_envelope`, `test_ac_auth_03_wrong_scheme_gives_401_envelope`, `test_ac_auth_03_expired_token_gives_401_envelope`; envelope shape in `tests/core/test_errors.py::test_ac_auth_03_app_error_uses_the_standard_envelope` | `auth/deps.py::require_user`, `auth/roles.py` |
| AC-AUTH-04: non-admin on an admin route gives 403 | Implemented | `tests/auth/test_require_admin.py::test_ac_auth_04_non_admin_gets_403_envelope`, `test_ac_auth_04_admin_is_allowed`, `test_ac_auth_04_missing_token_is_401_not_403` | `auth/deps.py::require_admin` |
| AC-AUTH-05: fail a test when a route is public and not allowlisted | Implemented | `tests/api/test_public_routes.py::test_ac_auth_05_every_public_route_is_in_the_allowlist`, `test_ac_auth_05_an_unprotected_route_outside_the_allowlist_is_found`, `test_ac_auth_05_a_route_with_require_user_is_not_flagged`, `test_ac_auth_05_allowlist_has_no_stale_entries`, `test_ac_auth_05_the_walk_sees_the_real_routes` | `api/public.py` |

Notes on the evidence:
- The AC-AUTH-05 walk has a negative test that adds an unprotected route and checks it is caught, so the test cannot pass vacuously.
- AC-AUTH-02 login is checked by decoding the returned token with the real `decode_token`, which requires `exp`, `sub` and `role`.
- Extra behaviour tested beyond the criteria: duplicate email gives 409, role escalation through register is ignored, wrong password and unknown email return the same message, tokens signed with another secret are rejected.

## Foundations for criteria owned by later phases

These have a test carrying the AC id, but only for the database column or role. The behaviour itself is not built yet, so they are not marked implemented.

| AC | Phase 1 foundation | Test | Still missing |
|---|---|---|---|
| AC-ING-04 duplicate upload | owner plus content hash duplicate rule in the documents repository | `tests/db/test_documents_repository.py::test_ac_ing_04_same_owner_and_hash_is_a_duplicate` | upload endpoint and worker (Phase 2) |
| AC-ING-05 chunk metadata | chunk columns for position, token count, chunker and embedding versions | `tests/db/test_chunks_model.py::test_ac_ing_05_chunk_stores_position_token_count_and_versions` | the chunker that fills them (Phase 2) |
| AC-RET-01 dense retrieval | HNSW cosine index, choice measured in `DECISIONS.md` | `tests/db/test_chunks_model.py::test_ac_ret_01_embedding_column_has_an_hnsw_cosine_index` | the retrieval query (Phase 3) |
| AC-PRM-02 prompt activation | `active_prompts` pointer table | `tests/db/test_prompt_tables.py::test_ac_prm_02_activating_only_moves_the_pointer` | admin endpoint (Phase 6) |
| AC-OBS-01 trace row | `query_traces` table | `tests/db/test_query_traces_table.py::test_ac_obs_01_trace_round_trips_with_json_fields` | writing a row per request (Phase 3 on) |
| AC-SQL-03 read-only role | `docdesk_readonly` role with SELECT only on `synthea_` tables | `tests/db/test_synthea_loader.py::test_ac_sql_03_readonly_role_can_select_synthea_tables`, `tests/db/test_readonly_role.py` | row limit, statement timeout, the SQL branch (Phase 6) |

AC-RET-05 (access filter) has a visibility rule in the documents repository but no test named with its id. Add one when retrieval is built.

## Changed files outside the phase scope

Nothing under `src/` is a stray feature. Every source and migration file maps to a T014 to T034 task. The items below are the files that do not map cleanly to a task.

Inside the diff range:

1. `pyproject.toml`, lint sections. Commits `b8526d8` (ruff `known-first-party`) and `c879be3` (bugbear `extend-immutable-calls` for `Depends`) change tooling config. No task covers this. They are small and fix real lint noise, but `CLAUDE.md` says work not in the plan needs a question first.
2. `docs/TECHSTACK.md`, commit `8615206`. Adds the `pgvector` Python package to the allowed stack so that `2e3c7b3` could add the dependency. The rule is "no new dependency unless listed in TECHSTACK", and here the list was edited to allow it. The package is needed for the `Vector` column (T026), but this was a stack decision made inside a task.
3. `tests/db/test_readonly_role.py`, commit `b3d0499`. An existing test was rewritten, not just extended. It went from "the role holds zero privileges" to "the role holds only SELECT, and only on `synthea_` tables". That is a stricter assertion, so it does not weaken the test. The commit message has no body, though, and `.claude/rules/tests.md` asks for the reason when a test changes.
4. `tests/db/test_eval_tables.py`, commit `5e72e7b`. Changed a test value so it hits the check constraint instead of failing on length. Justified, and the message explains why.
5. Phase 0 files touched by Phase 1 needs, all justified by a task: `.env.example` (T031 and T033 settings), `src/docdesk/core/config.py` (`readonly_database_url`, T031), `src/docdesk/api/app.py` (router include, T022).
6. `docs/PLAN.md` and `docs/DECISIONS.md`. Ticks and decisions, both allowed by `CLAUDE.md`.

After T034 (commits `9e50ffe..HEAD`, outside the phase diff, listed so nothing is missed):

7. `7e038b3`, `e0720da`, `00e6192`: placeholder secret rejection in `core/config.py`, test `tests/core/test_config_placeholders.py`, and a `DECISIONS.md` entry. This is not a task in `docs/PLAN.md`. It is a sensible hardening, but the work loop says to stop and ask first.
8. `0c00880` stops tracking `INSTALL.md`, `docs/COMMITS.md`, `docs/PLAN.md`, `docs/REFERENCES.md`, `docs/REMEMBER.md`, `docs/SKILLS.md` and `docs/WORKFLOW.md`. The files still exist on disk, but `CLAUDE.md` and the hooks point at several of them. A fresh clone will not have them.

## Observations to decide on

1. The route walk reads the OpenAPI schema. FastAPI serves `/docs`, `/redoc` and `/openapi.json` publicly, and those are not in the schema paths, so they are neither allowlisted nor checked. A route declared with `include_in_schema=False` would also escape the walk. No such route exists today (searched `src/`). Decide whether to disable the docs URLs in production or add them to the walk.
2. `find_unprotected_routes` treats any operation with a `security` entry as protected, relying on the note that only `require_user` uses the bearer scheme. A future dependency that adds its own security scheme would be counted as protected without proof. Low risk now.
3. The walk only covers `get`, `post`, `put`, `patch` and `delete`. HEAD and OPTIONS operations are ignored.
4. `CLAUDE.md` asks that auth be explained line by line to Ali before committing. The commit history does not show whether that happened for `passwords.py`, `jwt.py` and `deps.py`. Worth doing before moving on, since the interview rule applies.

## Recommendation

Phase 1 can be closed. Before Phase 2, decide on items 7 and 8 under "Changed files outside the phase scope" (the unplanned placeholder check and the untracked docs), and on observation 1 (public `/docs` and `/openapi.json`).
