---
paths:
  - "tests/**/*.py"
---

# Test rules

- Test names contain the acceptance criterion id from `docs/PRD.md`, lowercase with
  underscores, for example `test_ac_gen_02_citations_must_be_retrieved`.
- Write the failing test first, see it fail for the right reason, then implement.
- Never use `skip`, `xfail` or weaker assertions to get a task green. If a test is
  wrong, say so and fix it in its own commit with the reason in the message.
- Unit tests touch no network and no real LLM. Use fakes from `tests/fakes/`.
- Integration tests need a real Postgres with pgvector and Redis; mark them
  `@pytest.mark.integration`.
- Prompt tests (`tests/prompts/`) check the contract with code: schema validity,
  citation ids in the provided set, abstain when evidence is empty.
- Each endpoint gets one test for the success path, one for missing or invalid
  auth, one for bad input.
- Tests are 300 lines or fewer per file, same one-responsibility rule as source.
