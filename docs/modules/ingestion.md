# Module: ingestion and embeddings

Created 2026-10-13. Criteria: AC-ING-01 to 05. Experiments: E1 chunk size, E2 chunking strategy, E6 embedding model.

## Pipeline (`ingestion/pipeline.py`)
`ingest_document(document_id)`: load file, parse, clean, chunk, embed in batches, write all chunks in
one transaction, set status. Any exception rolls back, sets `failed` with a reason, and re-raises
so Celery records it (AC-ING-03).

## Files
- `parsers/pdf.py`, `parsers/text.py`: return a list of `(page, text)` blocks. One file per format.
  A scanned PDF with no text layer fails with a clear reason. OCR is out of scope.
- `cleaner.py`: normalize whitespace, remove repeated headers and footers, fix hyphenation across lines.
- `chunkers/fixed.py`, `chunkers/recursive.py`: each exposes
  `chunk(blocks, size, overlap) -> list[Chunk]`. A chunker never splits mid-sentence if it can avoid it.
  Each has a `VERSION` string stored on every chunk (AC-ING-05).
- `hashing.py`: content hash for duplicate upload detection (AC-ING-04).
- `tasks.py`: the Celery task. Thin wrapper over `ingest_document`.
- `seed.py`: downloads and loads the public corpus (openFDA labels, MedlinePlus topics, papers).
- `embeddings/encoder.py`: ONNX Runtime session, batching, pooling and normalization per the model card.
  `embeddings/tokenizer.py`: token counting shared with the context packer.
  `embeddings/reranker.py`: ONNX cross-encoder, `score(query, passages)`.

## Decisions to make with data, not opinion
- Chunk size and overlap: experiment E1 (128, 200, 256 tokens; MiniLM truncates above 256).
- Strategy: fixed vs recursive: E2. Parent-child (retrieve small, return the parent) is deferred and
  its code removed, see `DECISIONS.md`.
- Embedding model: two small open models compared in E6. Record the model name and revision on each chunk.

## Edge cases to handle
- Empty file, huge file (size limit with a clear error), password protected PDF, wrong mime type.
- Tables in PDFs (text order scrambles): note as a known limitation, do not pretend it works.
- Same content uploaded concurrently: the unique constraint on (owner, content hash) decides.
- Worker killed mid-job: the transaction means no partial chunks; status returns to `queued` on retry.
- Windows: run the worker with `--pool=solo`.

## Tests
Unit: each parser with small fixture files, each chunker for size and overlap invariants (no chunk over
the size limit, overlap is correct, concatenation covers the text), the cleaner. Integration: full
pipeline against a real Postgres, failure rolls back, duplicate upload creates no new chunks.
