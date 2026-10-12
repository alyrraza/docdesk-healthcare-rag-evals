# How to use this pack

This folder is the context for building DocDesk v2 with Claude Code. It is not the app.

## First time
1. Create the project folder on D:, for example `D:\MLOps\docdesk-v2`, and open a terminal there.
2. Copy everything from this pack into the folder, keeping the structure. Note the hidden
   folders `.claude` and `.githooks`.
3. `git init`, then `git config core.hooksPath .githooks`.
4. Create the venv inside the folder, activate it, and `pip install pytest ruff` so the hooks work.
5. Run `python -m pytest tests/scripts -q`. The 13 tests of the enforcement scripts should pass.
6. Make the first commits as tasks T001 to T007 in `docs/PLAN.md`.
7. Open Claude Code in the folder. It reads `CLAUDE.md` on its own.

## Starting each work session
Planning change (PRD, design or plan): start Claude Code in plan mode and say what changes.
Building: start a fresh session and say
"Do the next task in docs/PLAN.md. Follow CLAUDE.md. Stop and report if anything fails."
Phase review: start another fresh session and say
"Review the diff of Phase N against docs/PRD.md. For each acceptance criterion in this phase, say
implemented or not and name the test that covers it. List any changed file outside the phase scope."

## What is enforced and what is not
Enforced by hooks: file length, no em or en dash in markdown, ruff on staged Python, commit subject format.
Everything else in `docs/RULES.md` is checked in the phase review. Read it once.

## Keeping it small
`CLAUDE.md` must stay under 200 lines. Do not add `@` imports to it, because imported files load at
launch and cost context. Add new rules to the right file in `.claude/rules/` with a `paths:` list.
