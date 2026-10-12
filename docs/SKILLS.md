# Skills (task recipes)

Created 2026-10-13. Short, repeatable recipes. Each ends with a done check, so the task is
finished by evidence and not by the model's say-so. They can later be turned into real
Claude Code skills if a recipe is used often.

## S1. Add an endpoint
1. Find the acceptance criterion in `PRD.md`. Write the three tests: success, auth failure, bad input.
2. Add the request and response schemas (Pydantic) in `api/schemas/`.
3. Add the service function in the owning module. The router only calls it.
4. Add the route with its auth dependency and the standard error envelope.
5. Done when: three tests pass, the route is in the OpenAPI output, the public route test still passes.

## S2. Add a module
1. Read `MODULES.md`: responsibility, public interface, allowed dependencies.
2. Create the folder with an `__init__.py` that exports only the public interface.
3. One file per responsibility. Stop at 200 lines and split.
4. Add the module to `MODULES.md` if it is new.
5. Done when: no imports from another module's internals, tests pass, file length check passes.

## S3. Write or change a prompt
1. Read `PROMPT_STANDARD.md` and `OUTPUTS.md`.
2. Copy the latest version file to a new version. Never edit a released file.
3. Decide MAJOR, MINOR or PATCH and write the changelog line.
4. Run the prompt unit tests, then the dev-split eval for the slices that prompt affects.
5. Compare against the baseline with the paired comparison. Record the result.
6. Done when: prompt tests pass, no hard gate regresses, the eval result is committed.

## S4. Add a golden item
1. Pick the type and slice from `modules/evals.md`.
2. Write the question and find the evidence in the corpus by hand.
3. Write gold facts (short, atomic) and the gold chunk ids. For SQL items, write gold SQL and the gold result.
4. Ali verifies and signs the item (`verified_by`, `verified_on`).
5. Done when: the item validates against the schema and the loader test passes.

## S5. Add an eval metric
1. Define it in `modules/evals.md` first: inputs, formula, range, what failure it catches.
2. Write tests with hand-made examples where the right answer is known.
3. Implement as a pure function. LLM-based parts output labels, code computes the score.
4. Add it to the report with a bootstrap interval.
5. Done when: metric tests pass and the report shows it.

## S6. Debug a failing eval item
1. Read the trace for the item: retrieved ids, context, raw output, validation result.
2. Label the primary cause using `FAILURE_MODES.md`. One label only.
3. Fix at the layer that owns the cause (retrieval, packer, prompt, guardrail), not by adding prompt text.
4. Add the item to the regression slice so it can never silently return.
5. Done when: the item passes and the label counts in the report changed as expected.

## S7. Add a migration
1. Add or change the SQLAlchemy model.
2. Generate an Alembic migration, then read it line by line. Autogenerate misses some things.
3. Never edit a committed migration. Add a new one.
4. Done when: upgrade and downgrade both run on a clean database and the integration tests pass.

## S8. Run an experiment from the matrix
1. Confirm the baseline B0 numbers exist and are committed.
2. Change exactly one factor through config, not code edits.
3. Run retrieval-only metrics first (free). Run the generation eval only if retrieval looks promising.
4. Commit the config change, then commit the results file separately.
5. Done when: the row is in the results table with metrics, interval, p95 latency and cost.
