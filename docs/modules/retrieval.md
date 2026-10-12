# Module: retrieval

Created 2026-10-13. Criteria: AC-RET-01 to 05, AC-GEN-03 (abstain threshold input).
Experiments: E3 dense vs keyword vs hybrid, E4 reranker, E5 top-k.

## Interface
`retrieve(query: str, user: User, config: RetrievalConfig) -> RetrievalResult`
`RetrievalResult` holds ranked `ScoredChunk(chunk_id, document_id, text, score, source)` where
`source` says which leg found it, plus per-stage timings for the trace.
`RetrievalConfig` is a frozen dataclass with an id: mode (`dense`, `keyword`, `hybrid`), `top_n`,
`top_k`, `rerank` on or off, `rrf_k`. The config id is stored on every trace and eval run.

## Files
- `dense.py`: embed the query, run the pgvector cosine query, return top-N with distances.
- `keyword.py`: Postgres full text search (`tsvector`, `ts_rank_cd`), return top-N.
- `fusion.py`: reciprocal rank fusion. Score of an item is the sum over lists of `1 / (rrf_k + rank)`.
  Pure function. Ties break on chunk id so results are deterministic (AC-RET-03).
- `rerank_stage.py`: take the fused top-N, score with the cross-encoder, keep top-k (AC-RET-04).
  If the reranker errors, skip it and record that in the trace.
- `access.py`: the filter that limits every query to documents the user may access (AC-RET-05).
  Applied inside the SQL, not after the fact.
- `retriever.py`: orchestrates the stages from the config and collects timings.

## Why hybrid and why RRF (the interview answer)
Dense search finds meaning matches but can miss exact terms such as a drug name or a dose.
Keyword search finds exact terms but misses paraphrases. Their scores are on different scales, so
adding them is meaningless. RRF uses only ranks, so it needs no score calibration and is hard to
break. Postgres full text search keeps this in one database. Measure it in E3, do not assume it wins.

## Abstain threshold
The best final score is exposed so `generation` can abstain below a threshold (AC-GEN-03).
The threshold is tuned on the dev split using the unanswerable items. Different configs have
different score scales, so the threshold is stored per config id.

## Edge cases
- Empty corpus or a user with no documents: return an empty result, never an error.
- Query with only stop words: keyword leg returns nothing, dense leg still runs.
- Very short query: dense results are noisy, which is another reason for the abstain threshold.
- Near duplicate chunks from overlapping windows: the packer dedupes, retrieval does not.
- The vector index is approximate: report the recall of the index against exact search once, and note it in the README.

## Tests
Unit: RRF with hand-computed examples including ties, config handling. Property test: fusion output
is a permutation of the union of the inputs. Integration: access filter never returns another user's
chunks, dense and keyword legs against a small known corpus. Eval: retrieval metrics need no LLM.
