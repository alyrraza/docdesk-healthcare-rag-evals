---
paths:
  - "src/docdesk/ingestion/**/*.py"
  - "src/docdesk/embeddings/**/*.py"
  - "src/docdesk/retrieval/**/*.py"
---

# Ingestion and retrieval rules

- Ingestion runs only inside Celery tasks. An upload request never parses or embeds.
- A document is ingested in one transaction: either all chunks are stored and the
  status becomes `ready`, or nothing is stored and the status becomes `failed` with a reason.
- Every chunk stores: document id, position, token count, chunker version, embedding
  model version. Changing the chunker or the model means a new version string.
- Retrieval functions are pure where possible: query vector in, ranked chunk ids and
  scores out. Fusion and reranking never touch the database.
- Every retrieval path filters by the requesting user's accessible documents. No exceptions.
- Reciprocal rank fusion must be deterministic: ties break on chunk id.
- Embedding and reranker models run through ONNX Runtime on CPU. No PyTorch dependency.
- Read `docs/modules/ingestion.md` and `docs/modules/retrieval.md` before editing.
