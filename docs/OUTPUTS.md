# Structured outputs

Created 2026-10-13. Every model call returns data that is parsed into a Pydantic schema.
No regex on free text. Schemas stay flat, because large nested schemas with many optional
fields fail more often and make constrained decoding slower.

## Design rules
- Reasoning style fields come BEFORE conclusion fields, so the model lists evidence before it answers.
- Use short enums for anything the code branches on. Describe the allowed values in the prompt as
  well as in the schema, because models drift (returning `complete` where `completed` is expected).
- Split a complex extraction into two simple calls rather than one big schema.
- Anything deterministic is NOT in the schema: the disclaimer, scores, timestamps and costs are added by code.

## AnswerOutput (generation)
```python
class AnswerOutput(BaseModel):
    evidence_used: list[str]          # chunk ids the answer relies on, written first
    answer: str                       # the answer text, no disclaimer
    citations: list[str]              # subset of evidence_used
    confidence: Literal["high", "medium", "low"]
    abstained: bool
    abstain_reason: Literal[
        "none", "no_evidence", "weak_evidence",
        "out_of_scope", "unsafe_request", "system_error",
    ]
```
Field rules (checked in code, layer 2):
- `abstained` is true: `abstain_reason` is not `none`, `citations` is empty, `answer` is the fixed abstain sentence.
- `abstained` is false: `abstain_reason` is `none` and `citations` has at least one id.
- Every id in `citations` and `evidence_used` is in the retrieved set (AC-GEN-02).

## RouterOutput
```python
class RouterOutput(BaseModel):
    reason: str                       # one short sentence, first
    route: Literal["documents", "structured", "both"]
```

## SqlOutput
```python
class SqlOutput(BaseModel):
    tables_used: list[str]            # first, so the model commits to tables before writing SQL
    sql: str                          # a single SELECT statement
```

## Judge outputs (labels only, code computes scores)
```python
class ClaimLabel(BaseModel):
    claim: str
    supported: bool
    evidence_id: str | None

class FaithfulnessJudgement(BaseModel):
    claims: list[ClaimLabel]          # score = supported / total, computed by code

class FactLabel(BaseModel):
    fact: str                         # one gold fact from the golden item
    present: bool

class CorrectnessJudgement(BaseModel):
    facts: list[FactLabel]            # score = present / total, computed by code
    contradicts_gold: bool
```

## Validation layers
1. Schema: parse with Pydantic. Provider strict or JSON mode is a baseline, not the whole defense.
2. Field rules: the rules above. These catch valid JSON with wrong content, such as a citation of a
   chunk that was never retrieved or high confidence on an abstained answer.
3. Semantic checks: numbers and units in the answer must appear in the cited chunks. Flag, do not
   silently fix.

## Retry and fallback
- On failure, retry ONCE with the validation error appended to the prompt. Retrying with the same
  prompt tends to repeat the mistake.
- If the retry fails, return the typed fallback: `abstained = true`, `abstain_reason = system_error`,
  empty citations. Write the raw output to the trace and queue the case for review. Never raise to the user.
- Never loop more than once. A chain of calls multiplies failure: 97 percent per call success is
  about 74 percent over ten chained calls.

## Monitoring (what drifts silently)
Log every structured output with its input. Track, per prompt bundle: parse failure rate, retry
rate, fallback rate, enum value distribution, citation count distribution, abstain rate, answer
length distribution. Alert in the dashboard when a distribution moves away from the dev baseline.
Provider model updates can change these without any code change.

## API envelope
Success: `{"data": ..., "trace_id": "..."}`. Error:
`{"error": {"code": "...", "message": "...", "trace_id": "..."}}`. The answer response adds
`disclaimer` and `citations` with the chunk text and document title for each id.
