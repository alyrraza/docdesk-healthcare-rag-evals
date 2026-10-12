# Module: router and SQL branch

Created 2026-10-13. Criteria: AC-SQL-01 to 04, AC-RTR-01 and 02. Cut-order item: this branch is
cut before the core RAG and eval work if time runs short (see `PLAN.md`).

## Data
Synthea synthetic patients loaded into `synthea_patients`, `synthea_conditions`,
`synthea_medications`, `synthea_encounters`. Synthetic only. Never any real patient data.

## router
- `classifier.py`: `route(question) -> RouterOutput` using the `router.v1` prompt. A question about
  document content goes to `documents`, a question about counts, lists or patients goes to
  `structured`, a question that needs both goes to `both`.
- On any error or invalid output the router falls back to `documents` and records it (AC-RTR-02).
- The router is evaluated on its own: golden items carry a gold route, and `router_error` is a failure label.

## sql
- `schema_allowlist.py`: the tables and columns the model may use, with short descriptions that are
  also fed to the prompt. Everything else is forbidden.
- `generator.py`: builds the prompt (allowlisted schema only, no data), calls the model, parses `SqlOutput`.
- `validator.py`: security-sensitive. Parse the statement with a SQL parser, not regex. Reject unless:
  exactly one statement, a `SELECT`, no `INTO`, no function calls outside a small allowlist, every
  table and column in the allowlist, no comments hiding a second statement (AC-SQL-01, AC-SQL-02).
- `executor.py`: connects as `docdesk_readonly`, sets a statement timeout and a row limit, returns
  rows as plain data (AC-SQL-03). Rows go into the context packer as untrusted evidence.
- `service.py`: `answer_structured(question, user)` ties them together. Validation failure returns a
  safe message and does not execute (AC-SQL-04).

## Why defense in depth here
The model's SQL is untrusted output. The validator blocks bad statements. The read-only role means a
validator bug still cannot write. The timeout and row limit stop expensive queries. Each layer is
tested alone.

## Edge cases
- Questions that need a join across allowlisted tables: allowed if the join columns are allowlisted.
- Empty result: the answer says no matching records and cites the query, it does not invent rows.
- Ambiguous question: the model may return a query that is valid but answers a different question;
  that is `sql_error` in the eval (result mismatch) and a prompt problem, not a validator problem.
- Prompt injection through row text (a free-text column): rows are untrusted evidence.

## Tests
Validator: a table of accepted and rejected statements, including stacked statements, `INSERT`, `DROP`,
`SELECT ... INTO`, comments, unions to non-allowlisted tables, quoted identifiers. Executor: timeout
and row limit work, read-only role cannot write. Router: fallback on garbage output. Eval: execution
accuracy (result set equals gold result).
