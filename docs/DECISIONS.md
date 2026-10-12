# Decisions log

Newest first. Each entry: date, decision, why, what it supersedes. Specs older than their
decisions are marked superseded in the spec file, so nobody builds from stale text.

## 2026-10-13: modular monolith, not separate microservices
Decision: one FastAPI app, one Celery worker, one eval CLI, with strict module boundaries
(`MODULES.md`). Each module has one folder, one public interface, and files under 200 lines.
Why: separate services for a solo developer, no Docker on the laptop and about 9 GB of disk would
multiply infrastructure and hide the work that matters (retrieval, evals, prompts). Strict
module boundaries keep the extraction path open. If a module is ever split out, its interface is
already the contract.
Supersedes: the "microservices for each thing" idea from the first brief.

## 2026-10-13: golden set 100 items, with dev and test splits
Decision: 100 hand-verified items (60 dev, 40 held-out test) and a separate judge calibration set
of 40 hand-labeled outputs. Every headline number carries a bootstrap interval.
Why: current practitioner guidance calls sets under 100 items "basically vibes" and wants
slice-level checks. 100 is the most one person can hand-verify well in the time. The intervals
make the small size honest.
Supersedes: 80 questions and 20 hand-labeled outputs in `DOCDESK_V2_PROJECT_KICKOFF.md`.

## 2026-10-13: judge calibration with Cohen's kappa
Decision: freeze the judge (model, prompt, schema, settings), label a separate calibration set by
hand, report raw agreement, Cohen's kappa and a bootstrap interval, count parse failures as
errors. No universal kappa threshold is used. Acceptance is set against the owner's own
agreement between two labeling passes on different days.

## 2026-10-13: judge outputs labels, code computes scores
Decision: faithfulness and correctness judges return per-claim or per-fact labels. Scores are
computed by code. Why: deterministic arithmetic belongs in code, and labels can be inspected.

## 2026-10-13: Stripe, webhooks and Caddy removed
Why: billing is already shown in a separate paid client project. DocDesk v2 spends the time on
RAG engineering and evaluation instead. JWT auth, roles, rate limit and a daily token budget stay.

## 2026-10-13: Docker as files only
Why: no Docker on the laptop and no budget for a cloud host. Dockerfiles and compose are
validated by building in GitHub Actions. CV wording stays honest: "containerized, image built in CI".

## 2026-10-13: route walk reads the OpenAPI schema
Decision: the public route test (AC-AUTH-05) lists routes from `app.openapi()` and treats an
operation with a bearer security requirement as protected. Why: FastAPI 0.143 wraps included
routers, so `app.routes` no longer lists their routes and a walk over it passed without checking
anything. Limit: a route declared with `include_in_schema=False` is not seen, so do not use that flag.

## 2026-10-13: tests use a separate database
Decision: integration tests read `TEST_DATABASE_URL` only, and the fixture refuses a database whose
name does not end in `_test`. Why: tests drop and recreate tables, which must never touch real data.

## Parked ideas (not in scope, do not build)
- Multi-turn conversation memory (adds context clash risk; revisit after the baseline)
- Query rewriting and HyDE (matrix item E7, optional)
- Canary and shadow rollout of prompt versions (offline replay of traces is the cheap version)
- Real hosted deployment (Hugging Face Spaces with hosted Postgres and Redis, when budget allows)
