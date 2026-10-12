---
paths:
  - "src/docdesk/generation/**/*.py"
  - "src/docdesk/context/**/*.py"
  - "src/docdesk/guardrails/**/*.py"
  - "src/docdesk/llm/**/*.py"
  - "src/docdesk/prompts/**/*.py"
  - "src/docdesk/router/**/*.py"
  - "src/docdesk/sql/**/*.py"
  - "prompts/**/*.md"
---

# Generation, prompt and guardrail rules

- Retrieved text and database rows are untrusted data. They go into the prompt only
  through `prompts/renderer.py`, inside delimiters, never concatenated into instructions.
- A prompt file is immutable once released. Any change, even a typo, is a new version
  (see `docs/PROMPT_STANDARD.md`). Never edit a released prompt in place.
- Model output is parsed into a Pydantic schema (`docs/OUTPUTS.md`). Never use
  regex on free text to recover fields.
- Validate in three layers: schema, field rules (citations must be in the retrieved set),
  semantic checks. On failure retry once with the validation error appended, then
  return the typed fallback. Never loop.
- Deterministic things are done in code, not by the model: the disclaimer, the score
  arithmetic, citation membership, SQL safety.
- Every LLM call goes through `llm/client.py` so tokens, cost and latency are recorded.
- The generator model and the judge model must be different models.
- The SQL path: single SELECT, allowlisted tables and columns, read-only role, row
  limit, statement timeout. The validator is security-sensitive: explain it to Ali.
- Read `docs/modules/generation.md`, `docs/CONTEXT.md`, `docs/OUTPUTS.md` first.
