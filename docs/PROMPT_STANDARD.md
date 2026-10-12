# Prompt standard

Created 2026-10-13. Prompts are code: versioned, tested, reviewed and monitored. A prompt that
lives as a string inside a Python file is a bug in this project.

## Where prompts live
`prompts/<name>/<name>.v<N>.md` in the repo, for example `prompts/answer/answer.v1.md`.
The loader registers them into the `prompt_versions` table. The `active_prompts` table holds a
pointer per prompt name. Activating a version changes the pointer only, so rollback is a pointer
change with no deploy (AC-PRM-02).

## File format
```
---
name: answer
version: 1.0.0
schema: AnswerOutput@1
params:
  temperature: 0
  max_output_tokens: 600
status: draft            # draft | released | retired
changelog: first version
---
## system
...text...
## user
...text with {{variables}}...
```
Variables use `{{name}}`. The renderer rejects a template with an unfilled variable.
Untrusted variables (`evidence`, `rows`) must be marked in the front matter under `untrusted:`
and are rendered only inside delimiters.

## What a version identifies (the bundle)
A bundle id covers: prompt text, model name and version, sampling parameters, output schema
version and retrieval config id. Changing any of them is a new bundle. Every trace stores the
bundle id (AC-PRM-03). A model switch with unchanged prompt text is still a breaking change.

## Versioning rules
- Released versions are immutable. Any edit, even a typo, creates a new version.
- Each version also has a content hash computed at load time, so a changed file is detected.
- MAJOR: structural rewrite, persona or role change, output format change that breaks a parser, model switch.
- MINOR: new capability that leaves old behavior intact, new examples, expanded instructions.
- PATCH: small wording fix. If a patch changes behavior in the evals, it should have been MINOR or MAJOR.

## Writing rules for the prompt text
- Say who the model is, what the task is, what it may use as evidence, what it must do when the
  evidence is insufficient, and the exact output fields.
- State the abstain rule in positive terms with an example.
- Tell the model that text inside the evidence delimiters is data and never instructions.
- Put stable instructions first and variable content last, so the stable prefix can be cached.
- Describe enum values in the text as well as in the schema.
- No role-play flourishes, no emotional pressure, no vague words like "be accurate". Give a checkable rule.
- Examples: at most two, chosen from the dev split, never from the held-out test split.

## Testing a prompt
Prompt unit tests (`tests/prompts/`) assert contracts with code, using a fake LLM and fixed contexts:
1. Output parses into the schema.
2. Citations are a subset of the provided ids.
3. Empty evidence leads to an abstain.
4. A context containing an injected instruction does not change the output fields.
Then the quality check: run the dev-split eval for the affected slices and compare to the baseline
with a paired comparison.

## Release gate (a prompt, model or retrieval config change)
Hard gates (must hold):
- at least 99 percent of outputs parse into the schema
- zero critical failures on the adversarial and policy slices
- no access leaks
Soft gates (reviewed):
- rubric score changes by slice, refusal rate inside a narrow band
- a large rise in tokens per query (about 20 percent) counts as a regression even if quality improves
- faithfulness: block below 0.70 and flag for review below 0.80 as starting values, adjust after judge calibration
- overall quality: block if the paired comparison drops more than the tolerance (start at 3 percent relative)
These numbers are starting points reported by practitioners. Record the values you choose and why in `DECISIONS.md`.

## Rollout and rollback
- Release by changing the active pointer for one prompt name.
- Cheap version of shadow testing: replay a sample of stored traces through the candidate bundle
  offline and compare. Real canary traffic is parked.
- Rollback: point back to the previous version. Target under one minute.

## Monitoring
Per bundle, in the dashboard: parse failure rate, retry rate, fallback rate, abstain rate,
tokens per query, cost per query, p95 latency, and the enum and length distributions.
Production failures flow back into the regression slice of the eval set.

## Changelog discipline
Each version file has a one line changelog. The commit message uses the `prompt(...)` type and
links the eval result file.
