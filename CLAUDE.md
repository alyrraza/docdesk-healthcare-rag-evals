# DocDesk v2

Healthcare RAG service with a built-in evaluation harness. Python 3.11, FastAPI,
Postgres + pgvector, Redis, Celery, ONNX embeddings, small React frontend.
Portfolio project: the owner (Ali) must be able to explain every function in an
interview, so clarity beats cleverness.

## Work loop (one task at a time)
1. Take the next unchecked task in `docs/PLAN.md`. If the work is not in the
   plan, stop and ask before doing it.
2. Read only the files the task needs (map below). Do not read the whole docs folder.
3. Write the test first. The test name contains the acceptance criterion id,
   for example `test_ac_auth_01_password_is_hashed`.
4. Implement the smallest change that makes the test pass.
5. Run the checks: `python -m ruff check .`, `python -m pytest -q`,
   `python scripts/check_file_length.py`, `python scripts/check_docs_style.py`.
6. Commit using `docs/COMMITS.md`. One task is one or more commits. Never mix
   refactor and feature in a commit. The commit hooks reject bad messages.
7. Tick the task in `docs/PLAN.md` and tell Ali in plain English what you did.
8. If anything fails or the plan cannot be followed as written: STOP and report
   the exact error and your proposed fix. Never quietly substitute another
   approach (for example an in-memory counter instead of Redis).

## Which file to read for which task
- Why and what we are building: `docs/PRD.md`
- Architecture, data model, request flow: `docs/SYSTEM_DESIGN.md`, `docs/MODULES.md`
- API, auth, database: `docs/modules/backend.md`
- Parsing, chunking, embedding: `docs/modules/ingestion.md`
- Retrieval, fusion, rerank: `docs/modules/retrieval.md`
- Prompts, context packing, generation, guardrails: `docs/modules/generation.md`,
  `docs/CONTEXT.md`, `docs/OUTPUTS.md`, `docs/PROMPT_STANDARD.md`
- Router and SQL branch: `docs/modules/sql-branch.md`
- Evals and golden set: `docs/modules/evals.md`, `docs/FAILURE_MODES.md`
- Tracing, cache, rate limit, metrics: `docs/modules/observability.md`
- Frontend: `docs/modules/frontend.md`
- Recipes for common tasks: `docs/SKILLS.md`
- Machine and environment gotchas: `docs/REMEMBER.md`
- Decisions already made: `docs/DECISIONS.md`

## Hard rules (the short list, full list in `docs/RULES.md`)
- Every source file stays under 200 lines (tests 300). One responsibility per file.
- Every function has a type-annotated signature and a one line docstring that
  says WHY it exists, not what the code does.
- No bare `except`, no swallowed errors. Log with the trace id and re-raise or return a typed error.
- Every route declares its auth dependency. Public routes live in an allowlist.
- Never build a prompt by string concatenation. Use `prompts/renderer.py`, which
  wraps retrieved text in untrusted-data delimiters.
- Never skip, delete or weaken a test to make a task pass.
- No new dependency unless it is listed in `docs/TECHSTACK.md`.
- Auth, the SQL validator and the rate limiter are security-sensitive: after
  writing them, explain them line by line to Ali before committing.
- No em dash and no en dash in any markdown file. Use a comma, colon or a new sentence.
- Never commit secrets, `.env`, `PROJECT_NOTES.md`, model files or datasets.

## Environment
- Everything lives on drive D:. Never install or cache anything on C: (it is full).
- Docker is NOT run on this laptop. We only write Dockerfiles; CI builds them.
- Windows: Celery workers use `--pool=solo`. See `docs/REMEMBER.md`.

## End of session
Update `PROJECT_NOTES.md` (local only, in `.gitignore`) following the template
in the strategy doc, and add any new decision to `docs/DECISIONS.md`.
