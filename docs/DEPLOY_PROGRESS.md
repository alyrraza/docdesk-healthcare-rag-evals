# Deployment and README progress

Started 2026-10-15. Resume rule: read this file first, continue at the first unticked item.
Unattended session, zero LLM provider calls. Phase 5 files are not touched.

## Step 1: inspect (done)
Found: CI workflow (test, retrieval-gate), `scripts/fetch_model.py` (pinned revision plus sha256), `scripts/ci_gate.py`
and the 20 document fixture corpus in `evals/ci/corpus/medlineplus`, `scripts/seed_admin.py`, `scripts/smoke_llm.py`
(syncs and activates the answer prompt), `GET /health` (liveness, no database), Celery worker `docdesk.worker.entry`,
Alembic in `migrations/` (the read-only role password comes from READONLY_DATABASE_URL), `.env.example`, README stub.
Missing: Dockerfile, compose file, .dockerignore, Makefile, LICENSE, demo path, retrieval-only command.
Docker is not installed on this laptop, so the container is verified in CI (Step 4).
Settings refuse placeholder secrets ("change-me", "example"), so a copied `.env.example` cannot start the API.
The demo path therefore generates `.env` with random secrets (`scripts/make_env.py`).
`POST /query` already answers 503 `llm_not_configured` without a Groq key. Retrieval without the model is a script
(`scripts/demo_retrieve.py`), not a new route.

Plan: make_env + demo_seed + demo_retrieve (tests first) -> Dockerfile, entrypoint, compose, .dockerignore ->
CI job image-build -> F12 gate proof -> readme_results.py -> README + architecture -> LICENSE, checklist, scan -> push.

## Checklist
- [x] Step 1 inspect and plan
- [ ] Step 2 container files, demo path
- [ ] Step 3 verify container (no Docker here, moved to CI)
- [ ] Step 4 CI job image-build, push to ghcr on main
- [ ] Step 5 F12 gate proof and test
- [ ] Step 6 README, readme_results.py, architecture diagram, LICENSE
- [ ] Step 7 secret scan, GO_PUBLIC_CHECKLIST.md
- [ ] Step 8 targeted tests, b0_regression, push, CI, notes

## Log
