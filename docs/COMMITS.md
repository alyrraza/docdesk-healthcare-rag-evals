# Commit conventions

Created 2026-10-13.

## Format
`type(scope): subject` on the first line, 72 characters or fewer, lowercase, no full stop.

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `build`, `ci`,
`eval` (harness or golden set change), `prompt` (prompt file change).

Scopes match module folders: `auth`, `api`, `db`, `ingestion`, `embeddings`, `retrieval`,
`generation`, `context`, `guardrails`, `prompts`, `sql`, `router`, `cache`, `ratelimit`,
`observability`, `evals`, `frontend`, `ci`, `docs`.

Examples:
- `feat(auth): add salted password hashing`
- `test(retrieval): add failing test for rrf tie breaking`
- `fix(ingestion): roll back chunks when parsing fails`
- `eval(evals): record baseline B0 retrieval metrics`
- `prompt(prompts): add answer v2 with strict abstain rule`

The body (optional) explains WHY, in two or three lines. The diff already shows what.

## Rhythm
- One logical change per commit. A task in `PLAN.md` is usually two to four commits:
  failing test, implementation, then refactor or docs if needed.
- Never mix a refactor with a feature. Never mix code with unrelated docs.
- Commit when the checks pass, not at the end of the day.
- Experiment results are their own commit: the config change, then the results file.
- Do not rewrite history after pushing. Fix forward with a new commit.

## About the commit count
The plan has 155 tasks. With a test commit and an implementation commit for most of them, a
natural count lands well above 100, roughly 200 to 350 over the month. Do not split commits
artificially to chase a number. A reviewer who opens the history
should see real, small, reversible steps. Padding with empty or trivial commits is easy to
spot and hurts more than a short history.

## Attribution
Claude Code adds a co-author trailer to commits it creates. Keep it.

## Hook setup (once per clone)
```
git config core.hooksPath .githooks
```
Activate the virtual environment first so the hooks find `python` and ruff.
