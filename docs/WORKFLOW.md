# Workflow

Created 2026-10-13. Spec-driven: the PRD says what, the plan says in what order, the
tests say when it is done. The loop below follows the Requirements, Design, Tasks, Execute
pattern, with planning and execution in separate sessions.

## Session types
1. Planning session (plan mode). Used when the PRD, design or plan changes. Claude interviews
   Ali about edge cases and trade-offs, then edits `PRD.md`, `SYSTEM_DESIGN.md` or `PLAN.md`.
   No code is written here. Ali reviews the edited files before closing the session.
2. Execution session (fresh, normal mode). Reads `CLAUDE.md`, the task, and only the module
   file the task needs. Implements one task at a time. A fresh session is used because the
   planning session carries rejected ideas and exploration that pollute the context.
3. Review session (fresh). At the end of each phase a clean session compares the full phase
   diff against `PRD.md`. For each acceptance criterion it reports implemented or not and
   which test covers it, and it flags changed files outside the scope. The session that wrote
   the code does not certify its own work.

## Task loop (execution session)
1. Pick the next unchecked task in `PLAN.md`.
2. Read the task's module file and the acceptance criteria it names.
3. Write the failing test. Run it. Confirm it fails for the right reason.
4. Implement the smallest change that passes.
5. Run ruff, pytest, the file length check and the docs style check.
6. Commit (see `COMMITS.md`). Tick the task.
7. Explain to Ali in plain English: what changed, why this approach, one edge case.
8. If a step fails: stop, show the exact error, explain the likely cause, propose the fix, wait.
   Do not work around it, and do not swap in a different approach silently.

## Definition of done for a task
- The acceptance criteria named in the task have passing tests that name them.
- The checks pass without skipped tests.
- The diff touches only the files the task lists.
- Ali has read the explanation. For security-sensitive modules, Ali has re-explained it back.

## Deviation protocol
If the plan cannot be followed as written, do not improvise. Add a dated entry to
`DECISIONS.md` with the problem, the options and the choice, update the affected spec files
with "superseded on <date>" notes, then continue.

## Keeping context small
- `CLAUDE.md` stays under 200 lines. Details live in `docs/` and are read on demand.
- Path-scoped rules in `.claude/rules/` load only when matching files are touched.
- Long exploration (reading logs, searching a dataset) is done in a subagent that returns a
  short summary, not in the main session.
- Never paste large logs into the session. Save them to a file and grep what you need.
- After a failed attempt, do not keep retrying in the same polluted context. Summarize the
  state in two lines and start a fresh session if the task needs more than two more tries.

## Enforcement
Rules that must hold are checked by git hooks, not remembered by the model.
See `RULES.md` for which rules are ENFORCED. Phase 5 adds an acceptance criteria coverage check
(task T118) so that a criterion with no test fails the build.

## End of every session
- Update `PROJECT_NOTES.md` (local only) with what was built, errors hit, and interview notes.
- Add decisions to `DECISIONS.md`.
- Tick finished tasks in `PLAN.md`.
