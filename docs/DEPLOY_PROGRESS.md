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
- [x] Step 2 container files, demo path (make_env, demo_seed, demo_retrieve, Dockerfile, compose)
- [x] Step 3 no Docker on this laptop, verification moved to CI (Step 4)
- [x] Step 4 CI job image-build (first run: build, smoke, push all passed; test job failed on .env.example, fixed)
- [x] Step 5 F12 gate proof (scratch Neon databases, exit 1 then exit 0) and test
- [x] Step 6 README, readme_results.py, architecture diagram (svg, rendered with Edge and checked), LICENSE
- [x] Step 7 secret scan (only hit: repo name in README, false positive), GO_PUBLIC_CHECKLIST.md
- [x] Step 8 targeted tests, b0_regression ok, push, CI green

## Log
- 2026-10-15: pushed e145fd9, CI green (test, retrieval-gate, image-build, image pushed). 2 pushes used, 1 failure fixed.

## Web interface (started 2026-10-15, unattended)
Precondition checked: `git pull` clean, `.github/workflows/ci.yml` has the split `build-smoke` and `image-push` jobs.

Inspection of the API:
- `POST /query` needs a bearer JWT (`require_user`). Tokens come from `POST /auth/login` (public) after `POST /auth/register`.
- Response: `{"data": {answer, disclaimer, confidence, abstained, abstain_reason, citations[label, chunk_id, document_id, document_title, text, page]}, "trace_id"}`.
- Outcome states: `abstained=false` is Answered; `abstained=true` with `abstain_reason="unsafe_request"` is Refused (dose or diagnosis policy, no model call); any other abstain reason is Abstained.
- Retrieved chunks and scores are NOT in the `/query` response, and no retrieval-only route exists (only `scripts/demo_retrieve.py`).
- Errors use `{"error": {code, message, trace_id}}`. A missing Groq key gives 503 `llm_not_configured`; a missing active prompt gives 503 `prompt_not_active`.

Plan (tests first for each step):
1. New authenticated `POST /retrieve` (same retrieval as `/query`, no model call), so the UI can show chunks and scores and still be useful when generation is unavailable.
2. New package `docdesk.web`: `GET /` serves the page, `GET /static/{name}` serves files from a fixed name list (no path traversal, no mount). Both are added to the public allowlist on purpose; the page holds no data.
3. Static files: `index.html`, `style.css`, `api.js`, `dom.js`, `render.js`, `main.js` (each under 200 lines, no external requests, text set with textContent only).
4. Tests: page and static served, grep test for external URLs and innerHTML, `/retrieve` auth and result.
5. CI: one extra `GET /` step in `build-smoke`. Dockerfile already copies `src`, so the static files are in the image; a test pins that.
6. Screenshots with headless Edge against a scratch database, at most 6 generator calls. README, modules docs, notes.

- [x] Step A /retrieve route
- [x] Step B web package and static files
- [x] Step C CI smoke step and image check
- [x] Step D screenshots (4 generator calls, scratch database dropped)
- [ ] Step E docs, scans, push
