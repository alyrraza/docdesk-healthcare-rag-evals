# References

Created 2026-10-13. What each source was used for, its date, and how far to trust it. The goal was
sources from June to September 2026. Where only an older source was available, it is marked.

## From the target window (June to September 2026)
| Source | Date | Used for |
|---|---|---|
| Analytics Vidhya, "Spec-Driven Development with Claude Code" | 2026-08-23 | SPEC and PLAN files, checkable criteria, fresh execution session, one commit per task, stop on failure, independent review, enforce rules in code, date the specs |
| OneUptime, "How to Calibrate an LLM-as-a-Judge Against Human Labels with Cohen's Kappa" | 2026-08-31 | judge calibration procedure: separate calibration set, freeze the judge, count parse failures, kappa plus bootstrap interval, held-out split |
| Kunal Ganglani, "AI Engineering Evals: Regression Gates for Prompts, Tools, RAG" | 2026-08-10, updated 2026-09-11 | gate design by layer, per-slice failure budgets, golden set sizing, PR gate versus nightly suite, cache judge outputs |
| Openlayer, "RAG Evaluation in Production" | 2026-07-13 | groundedness vs faithfulness definitions, retrieval metrics, starting thresholds (0.80 flag, 0.70 block), "logging alone is observation" |
| inference.net, "AI regression testing for LLM apps" | 2026-06-15 | assert contracts in code and judge quality with a rubric, paired comparison against a baseline, failures become regression cases |
| Maxim, "Prompt Injection Defense for Production AI Agents" | 2026-06-02, modified 2026-07-03 | defense in depth for injection, output scanning, tool allowlists (the page did not cover delimiting or testing) |
| AppScale, "Context Engineering for Production LLM Agents" | 2026-06-23 | select, compress, order, isolate; budget per slot; track cache hit rate. Only the summary was readable, not the full text |
| Claude Code documentation, "How Claude remembers your project" | current | CLAUDE.md under 200 lines, imports still load at launch, path-scoped rules, hooks for enforcement, AGENTS.md support |

## Slightly outside the window
| Source | Date | Used for | Caution |
|---|---|---|---|
| TechPlained, "Vibe Coding in 2026: What Production Teams Actually Do" | 2026-05-09, updated 2026-10-08 | failure patterns of generated code, hard bans for auth and security code, tests as spec | the 60 to 70 percent figure for tests catching model mistakes is the author's estimate |
| Digital Applied, "Context Engineering: Agent Reliability Playbook" | 2026-05-26 | poisoning, distraction, confusion, clash, rot | the figures cited (tool counts, token onsets) come from earlier studies on specific models; directional only |

## Older sources (before June 2026), used only where nothing newer was readable
| Source | Date | Used for | Caution |
|---|---|---|---|
| Tian Pan, "Prompt Versioning and Change Management in Production AI Systems" | 2026-03-13 | immutable versions, semantic versioning rules, bundle contents, pointer based rollback, 3 percent tolerance | I did not find a readable June to September article on prompt versioning, so this is the main source for that part |
| Tian Pan, "JSON Mode Won't Save You" | 2026-04-09 | structured output failure modes, flat schemas, retry once with the error, typed fallbacks | |
| LogRocket, "The LLM context problem in 2026" | 2026-03-04 | strategies for pruning, summarization and quarantine | secondary numbers |

## What is NOT sourced
- The starting numbers in `CONTEXT.md` (6000 token budget and its split) are design defaults to be tuned.
- The 200 line and 300 line file limits and the 40 line function guideline are project choices.
- Prefix caching discount, provider free-tier limits and model names must be checked at the time of use.
