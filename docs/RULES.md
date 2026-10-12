# Rules

Created 2026-10-13. Rules marked ENFORCED are checked by a script or git hook, because a
rule that only lives in a document gets forgotten as context fills. Rules marked REVIEW
cannot be checked by a script, so they are checked in the end-of-phase review (see `WORKFLOW.md`).

## Code structure
- ENFORCED: source files 200 lines or fewer, test files 300 or fewer (`scripts/check_file_length.py`).
- ENFORCED: ruff passes on staged Python files.
- REVIEW: one responsibility per file and per function. Functions stay under about 40 lines.
- REVIEW: modules talk through their public interface in `docs/MODULES.md`. No reaching into another module's internals.
- REVIEW: no global mutable state. Dependencies are passed in.
- REVIEW: every function has type annotations and a one line docstring that says why it exists.

## Errors and logging
- REVIEW: no bare `except`, no `except Exception: pass`. Catch the specific error, log it with the trace id, then re-raise or return a typed error.
- REVIEW: every external call (database, Redis, LLM, HTTP) has a timeout.
- REVIEW: resources are closed by context managers (files, sessions, connections).

## Security
- REVIEW: every route declares its auth dependency. Public routes are an allowlist and a test enforces it (AC-AUTH-05).
- REVIEW: parameterized queries only. No f-string SQL.
- REVIEW: no secret in the repo. Secrets come from environment variables via `core/config.py`.
- REVIEW: auth, the SQL validator and the rate limiter are written by Claude and then explained line by line to Ali before commit. Ali must be able to rebuild them from memory.
- REVIEW: retrieved text is untrusted. It goes into prompts only through the renderer, inside delimiters.

## Tests
- REVIEW: test first, with the acceptance criterion id in the test name.
- REVIEW: never skip, delete or weaken a test to get green. A test that can be skipped can no longer fail.
- REVIEW: every new endpoint has a success test, an auth failure test and a bad input test.

## Prompts and evals
- REVIEW: released prompts are immutable. See `PROMPT_STANDARD.md`.
- REVIEW: the generator and the judge are different models.
- REVIEW: gold answers are verified by Ali. The held-out split is not used for tuning.
- REVIEW: report every headline metric with a confidence interval.

## Dependencies and scope
- REVIEW: no dependency that is not listed in `TECHSTACK.md`. Add it to that file in the same commit, with the reason.
- REVIEW: no feature that is not in `PRD.md`. Scope changes go through `DECISIONS.md` first.
- REVIEW: do not change files outside the task's listed files. A diff that touches unrelated files is a failed task.

## Commits and docs
- ENFORCED: commit subjects follow `COMMITS.md` (commit-msg hook).
- ENFORCED: no em dash or en dash in any markdown file (pre-commit hook).
- REVIEW: `PROJECT_NOTES.md`, `.env`, datasets, model files and caches are never committed.

## Environment
- REVIEW: nothing is installed or cached on C:. Everything lives on D: (see `REMEMBER.md`).
- REVIEW: Docker is never run on this laptop. Dockerfiles are validated in CI.
