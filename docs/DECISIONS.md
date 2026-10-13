# Decisions log

Newest first. Each entry: date, decision, why, what it supersedes. Specs older than their
decisions are marked superseded in the spec file, so nobody builds from stale text.

## 2026-10-13: modular monolith, not separate microservices
Decision: one FastAPI app, one Celery worker, one eval CLI, with strict module boundaries
(`MODULES.md`). Each module has one folder, one public interface, and files under 200 lines.
Why: separate services for a solo developer, no Docker on the laptop and about 9 GB of disk would
multiply infrastructure and hide the work that matters (retrieval, evals, prompts). Strict
module boundaries keep the extraction path open. If a module is ever split out, its interface is
already the contract.
Supersedes: the "microservices for each thing" idea from the first brief.

## 2026-10-13: golden set 100 items, with dev and test splits
Decision: 100 hand-verified items (60 dev, 40 held-out test) and a separate judge calibration set
of 40 hand-labeled outputs. Every headline number carries a bootstrap interval.
Why: current practitioner guidance calls sets under 100 items "basically vibes" and wants
slice-level checks. 100 is the most one person can hand-verify well in the time. The intervals
make the small size honest.
Supersedes: 80 questions and 20 hand-labeled outputs in `DOCDESK_V2_PROJECT_KICKOFF.md`.

## 2026-10-13: judge calibration with Cohen's kappa
Decision: freeze the judge (model, prompt, schema, settings), label a separate calibration set by
hand, report raw agreement, Cohen's kappa and a bootstrap interval, count parse failures as
errors. No universal kappa threshold is used. Acceptance is set against the owner's own
agreement between two labeling passes on different days.

## 2026-10-13: judge outputs labels, code computes scores
Decision: faithfulness and correctness judges return per-claim or per-fact labels. Scores are
computed by code. Why: deterministic arithmetic belongs in code, and labels can be inspected.

## 2026-10-13: Stripe, webhooks and Caddy removed
Why: billing is already shown in a separate paid client project. DocDesk v2 spends the time on
RAG engineering and evaluation instead. JWT auth, roles, rate limit and a daily token budget stay.

## 2026-10-13: Docker as files only
Why: no Docker on the laptop and no budget for a cloud host. Dockerfiles and compose are
validated by building in GitHub Actions. CV wording stays honest: "containerized, image built in CI".

## 2026-10-13: route walk reads the OpenAPI schema
Decision: the public route test (AC-AUTH-05) lists routes from `app.openapi()` and treats an
operation with a bearer security requirement as protected. Why: FastAPI 0.143 wraps included
routers, so `app.routes` no longer lists their routes and a walk over it passed without checking
anything. Limit: a route declared with `include_in_schema=False` is not seen, so do not use that flag.

## 2026-10-13: tests use a separate database
Decision: integration tests read `TEST_DATABASE_URL` only, and the fixture refuses a database whose
name does not end in `_test`. Why: tests drop and recreate tables, which must never touch real data.

## 2026-10-13: documents table adds chunk_count and is_shared
Decision: `documents` has `chunk_count` (AC-ING-02 says the count is stored) and `is_shared`.
Seeded public corpus documents are owned by the admin user and marked shared, so every user can
retrieve them. Uploaded documents are private to the owner. Why: the data model listed neither
column, and the access filter (AC-RET-05) needs a rule for the shared corpus. Easy to change
before T056 if the plan should differ.

## 2026-10-13: embedding column is vector(384)
Decision: `chunks.embedding` is `vector(384)`, the output size of the small sentence embedding
models planned (MiniLM and bge-small class). Why: pgvector needs a fixed size and the model is not
chosen until T037. If E6 picks a second model with another size, it gets its own column or table
through a new migration. The model name and revision are stored on every chunk.

## 2026-10-13: vector index is HNSW with cosine distance
Decision: `chunks.embedding` gets an HNSW index (m 16, ef_construction 64), query time
`hnsw.ef_search` 40. Measured with `scripts/bench_vector_index.py` on 20000 synthetic clustered
vectors of 384 dimensions, 50 queries, top 10, server side time from EXPLAIN ANALYZE, on the
hosted test database:

| Setting | Median ms | p95 ms | Recall at 10 | Build s |
|---|---|---|---|---|
| exact scan, no index | 9.25 | 13.32 | 1.00 | 0 |
| HNSW ef_search 40 | 0.38 | 0.50 | 1.00 | 6.8 |
| HNSW ef_search 100 | 0.63 | 0.93 | 1.00 | 6.8 |
| IVFFlat lists 141, probes 1 | 0.20 | 0.26 | 1.00 | 2.2 |
| IVFFlat lists 141, probes 10 | 0.70 | 0.90 | 1.00 | 2.2 |
| IVFFlat lists 141, probes 30 | 1.86 | 2.23 | 1.00 | 2.2 |

Why HNSW: IVFFlat builds its lists from the rows present, so it should be built after the corpus
is loaded and rebuilt as it grows. HNSW can be created on an empty table and stays valid while
documents are added. Both were fast enough. Caveat: the data is synthetic and easy (recall 1.00
everywhere). An earlier run on uniform random vectors, which has no structure, gave recall 0.19
for HNSW and 0.20 for IVFFlat at probes 10, so the result depends on how clustered the real
embeddings are. Re-measure recall on the real corpus at T052 and record the number here. At 20000
rows an exact scan costs only 9 ms, so the index is a scaling choice, not a necessity yet.

## 2026-10-13: settings reject placeholder secrets
Decision: `Settings` fails at startup when `JWT_SECRET`, `ADMIN_PASSWORD` or the password inside a
database or Redis URL contains "change-me", "changeme", "example" or "placeholder" (any case). Only
a test can switch this off, by setting `Settings.reject_placeholders` on the class, never through
an environment variable. Why: a copied `.env.example` once left the JWT signing secret equal to a
value committed to git.

## 2026-10-13: why the read-only role test was rewritten
Decision: `tests/db/test_readonly_role.py` was changed twice, each time in its own commit, and no
check was weakened. First, the create-table test now runs `SET default_transaction_read_only = off`
before trying to create a table, so it proves the privileges alone stop the write and not just the
read-only session default. Second, after T032 loaded the Synthea tables, the old assertion that the
role holds zero table privileges became false by design, so it now asserts the role holds only
SELECT and only on `synthea_` tables. Why: the old tests passed for the wrong reason or failed for
a correct reason, and a test that cannot fail on a real privilege leak is not a test.

## 2026-10-13: first embedding model is all-MiniLM-L6-v2
Decision: the encoder starts with `sentence-transformers/all-MiniLM-L6-v2` (fp32 ONNX, 90 MB, 384
dimensions, mean pooling, max 256 tokens), revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
It is stored under `.cache/models/` and never committed. Why: it fits `vector(384)` and runs on CPU.
Experiment E6 still compares it with a bge-small class model before the final choice.

## 2026-10-13: ingestion design choices from Phase 2
- Uploads are the raw request body (`POST /documents?title=...`), not multipart. Why: multipart
  needs `python-multipart`, which is not in TECHSTACK. A browser can send a `File` as the body.
  Revisit at the frontend phase.
- Uploaded bytes live in `UPLOAD_DIR` (default `data/uploads`, git-ignored), one file per document
  id, behind `LocalFileStore`. The parser is chosen from the file bytes (a `%PDF-` header), never
  from the file name or mime type.
- A chunk may not be larger than the encoder's `max_length` (256 tokens for MiniLM). The pipeline
  refuses a bigger size instead of letting the model cut the end off silently. Consequence: E1 sizes
  are 128, 200 and 256 tokens (changed from 256, 512, 1024), and the baseline B0 chunk size is 200.
- `chunks.page` (nullable integer, migration 0012) holds the PDF page; text and JSON sources leave it
  null. Parent-child chunking is deferred, see the next entry.
- Seed corpus: one openFDA label per common generic drug (`drug_names.py`, about 160 names) and 150
  MedlinePlus topics spread evenly across the alphabet. About 300 documents, all under `data/corpus/`.
- Re-uploading content whose earlier copy failed re-queues that same document instead of returning
  it as a duplicate.

## 2026-10-13: parent-child chunking is deferred
Decision: none of the experiments E1 to E10 in `docs/modules/evals.md` needs parent-child chunking:
E2 compares fixed and recursive chunking only. There is no `parent_text` column. Revisit only if
E2 shows chunk context is the weak point; it would need a migration then.

Update, same day: the parent-child chunker and its tests were removed from the code (nothing used
them). The idea, if revisited: split into small child chunks for retrieval, store the larger parent
text next to each child, and give the parent to the model. It needs a `parent_text` column and a
migration, and the chunker can be rewritten from this description.

## 2026-10-13: why the dispatch test was replaced (commit 87f0864)
In `tests/ingestion/test_dispatch.py`, the test `test_ac_ing_03_a_pdf_is_recognised_by_its_header_not_its_file_name`
was deleted in the same commit that added the PDF parser tests. It was written when the PDF parser
was a stub, and it asserted that PDF bytes raise a `ParseError` mentioning "PDF". Once T040 made
the parser real, that behaviour was meant to disappear, so the test would have failed for a good
reason. Its intent, that a PDF is chosen by its bytes and not by its name, is now covered by
`test_ac_ing_03_dispatch_sends_pdf_bytes_to_the_pdf_parser` in `tests/ingestion/parsers/test_pdf.py`,
together with tests for no text layer, password protection, corrupt files and zero pages.
Nothing was weakened: the old test checked a stub, the new tests check the real parser.

## 2026-10-13: HNSW recall on the real corpus (T052)
Measured on the 5457 real chunks (298 documents): HNSW with ef_search 40 returned 99.9 percent of the
exact scan's top 10 neighbours (100 random chunks as queries, themselves excluded). The index choice
stands. Chunks and index take 31 MB; the whole main database is 39 MB.

## Parked ideas (not in scope, do not build)
- Multi-turn conversation memory (adds context clash risk; revisit after the baseline)
- Query rewriting and HyDE (matrix item E7, optional)
- Canary and shadow rollout of prompt versions (offline replay of traces is the cheap version)
- Real hosted deployment (Hugging Face Spaces with hosted Postgres and Redis, when budget allows)
