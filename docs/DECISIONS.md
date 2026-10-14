# Decisions log

Newest first. Each entry: date, decision, why, what it supersedes. Specs older than their
decisions are marked superseded in the spec file, so nobody builds from stale text.

## 2026-10-14: unanswerable items prove their absence by code (T085)
Decision: an unanswerable golden item carries `absent_terms` and an `absence_scope` (`corpus` or one source
key). `resolve_item` fails the item when any term, whitespace folded and case insensitive, is a substring of
the scope text. Batch 4 (gi-055 to gi-073, 11 dev and 8 test, split by `split_for("unanswerable", n)`) has 8
near misses scoped to their document, 6 absent subjects and 5 out of scope questions scoped to the corpus.
Rules used while choosing items:
- A near miss must not be so close that a careful reader would call the fact stated in other words. Four
  candidates were rejected for that reason (digoxin half-life, daily fluid amount in the dehydration topic,
  grapefruit juice with the buspirone label, blood pressure onset for doxazosin).
- No question asks what the user personally should take or whether the user has a condition.
- Cost questions are avoided: the Synthea tables hold cost columns, so a price question could be answered by
  the SQL branch and would not be unanswerable.
- The review sheet (`scripts/golden_review.py FILE --probe`) shows the top 3 chunks of dense and of keyword
  retrieval under B0 for each such item. It refuses to run when the stored corpus fingerprint differs from b0.
Why: a gold "no answer" that rests on memory is the same kind of risk as a wrong gold answer.
Open question, T086 not started: the adversarial slice needs an expected behaviour (answer, abstain or
refuse) and, for injected instructions, a poisoned document. The schema has neither. See the report of
2026-10-14 and the owner's choice.

## 2026-10-14: label questions reuse the label's wording (owner review rounds 1 and 2)
Decision: the golden questions about drug labels often repeat the wording of the label sentence that
answers them, because the label is the only place that states the fact ("indicated for", "supplied as",
"contraindicated in"). Keyword and hybrid retrieval therefore benefit more than they would with patient
phrasing, and B0 numbers (dense) understate what E3 will show for keyword search. Read E3 with that in mind.
- Parked idea (not built): a paraphrase subset written in patient language, to measure retrieval
  when the question does not copy the source.
- README limitation to write when the baseline is published: the golden questions are close to the
  source wording, so lexical overlap helps.
Round 2 rules from the same review: a question must not say "boxed warning" unless the quote does; a
question about a list must be answerable from the quote (a list that continues past the quote is
reported in `docs/golden_review/list_check.md`, local only); a quote that is not complete gets another fact.

## 2026-10-14: duplicate evidence, alt_sources and the lessons from the batch 1 review
Decision: the golden loader now reports, for every evidence quote, each other corpus document whose
cleaned text (whitespace folded) also holds it. An item with such a duplicate must either name its
own source document in the question (the brand or generic name of a label, the title of a topic), or
list the other documents in `alt_sources` on that evidence entry. The resolver treats an alternate as
gold too (its chunks that hold the quote count). Naming the document is preferred, so retrieval
metrics stay about one document. An alternate must exist and must hold the quote. The loader also
fails a quote that has no gold chunk, and fails a multi chunk item when two of its quotes land in the
same stored chunk (checked against the B0 chunking in the database).
Result on batch 1 before the review fixes: one duplicated quote (gi-006, the benzodiazepine and opioid
warning, held by four other labels). Naming temazepam in the question clears it. The 21 quotes of batch 2
and the 39 quotes of batch 3 each occur in one document only.
Lessons from the owner's review of batch 1, applied to every later batch:
- A quote carries its own context. If it starts mid list, include the heading sentence. A quote must
  not refer to something it does not name, so abbreviations are expanded inside the quote.
- A question must not add a claim the quote does not make.
- Single part questions for single fact items. Drug label questions name the drug.
- No clinical trial remarks or reassuring generalisations. Prefer dosage forms, strengths, warnings,
  indications, definitions and schedules.
- At most 2 items per source document in the whole set (tested). Both corpora are mixed.
Replaced ids: gi-002 and gi-007 could not be widened within the 300 character limit (399 and 500
characters needed) and were dropped; gi-010 was dropped by the owner. They are replaced by gi-012,
gi-013 and gi-011, placed in the same file slots so the split plan order holds. Batch 2 therefore
starts at gi-014 and batch 3 at gi-035.
Why: a quote shared by several labels makes the gold document arbitrary, and a multi chunk item
whose quotes share a chunk would be a single chunk item in disguise.

## 2026-10-14: the quote validator folds whitespace like the resolver
Decision: `check_quote` collapses every whitespace run to one space on both the quote and the document
text before comparing, the same way `quote_spans` does. A quote that crosses a line break is written
with a single space. Quotes still need real matching words, and still have no leading or trailing
whitespace (schema rule). Supersedes the "exact substring" wording in `docs/modules/evals.md` for the
whitespace part only.
Why: the validator was stricter than the resolver. A quote that the validator rejected would have been
found by the resolver, and a quote copied from a wrapped label would need a newline inside a YAML string.
Test change: `test_ac_evl_01_a_quote_with_different_whitespace_is_not_an_exact_substring` asserted the old
rule and was replaced by two tests (a line break folds; different words still fail). The test that a
missing quote fails now uses a different word instead of a doubled space, which folding makes legal.

## 2026-10-14: PyYAML stays as an allowed dependency
Accepted by the owner. It is declared in `pyproject.toml` and `TECHSTACK.md` (entry of the same day below)
and golden files are read with `yaml.safe_load` only.

## 2026-10-14: smoke test leftovers removed from the main database
The main database held two upload documents from the phase 2 and 3 smoke tests ("FDA sample PDF smoke",
36 chunks made by the fixed chunker, and "Damaged PDF smoke", failed) and 598 files under `data/uploads`
that no document owned after two re-ingests. They were removed with `scripts/clean_leftovers.py` so B0
sees only the seed corpus: 298 documents, 5919 recursive chunks, matching the corpus fingerprint.

## 2026-10-14: PyYAML added for the golden set files
`docs/modules/evals.md` defines golden items as YAML. PyYAML was installed only as a dependency of
`huggingface_hub`, so it is now declared in `pyproject.toml` and `TECHSTACK.md`. Files are read with
`yaml.safe_load` only.

## 2026-10-14: golden items use evidence quotes, not chunk ids
Decision: a golden item has `gold_evidence`, a list of `{source, text}` entries, instead of
`gold_chunk_ids`. `source` is the stable key `seed:<corpus>:<source id>` stored in `documents.source`,
and `text` is a verbatim quote of at most 300 characters that must be an exact substring of the
document's cleaned text. A chunk is gold for an entry if it contains the whole quote or overlaps at
least half of it by position. All entries of a multi chunk item are required for its recall.
Unanswerable items have an empty list and a `no_evidence_reason`. Full rules: `docs/modules/evals.md`.
Why: E1 and E2 change the chunking and every re-ingest creates new ids, so chunk ids in the golden
set would go stale after each experiment. A quote survives both, and it is what the owner reads
when verifying an item.
Supersedes: `gold_chunk_ids` in the golden item format of 2026-10-13.
Side change: seed documents now store `seed:<corpus>:<source id>` in `documents.source` (it was
only `seed:<corpus>`, which names a group and not a document). The prefix is unchanged, so the
reset script still finds them.

## 2026-10-14: T087 and T088 are done before T082 to T086
Decision: the retrieval metrics (T087) and the bootstrap statistics (T088) are built before the golden
item batches. Task ids and acceptance criteria do not change.
Why: neither task depends on golden items, and the golden batches need the owner's hand checking, so
the code work does not wait for it.

## 2026-10-14: the per-document cap stays at 2 in B0
Decision: `packer.max_per_document` stays at 2 in `evals/configs/b0.toml`. Experiment E5 varies it
together with top-k.
Why: B0 must describe the system as built. The weakness it causes (found in the phase 3 smoke
question) is measured by E5, not hidden by changing the baseline.

## 2026-10-14: T078a was built before its plan line existed
T078a (refuse personal dose and diagnosis requests, AC-GEN-05) was implemented before its line was
added to `PLAN.md`. The owner accepted the history as it is. No commit is rewritten.

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

## 2026-10-13: LLM models and limits for phases 3 to 5
Checked live on this date (Groq `/models`, OpenRouter `/models`, a tiny Groq call for headers, Groq docs).
- Generator: Groq `openai/gpt-oss-120b` (OpenAI family). Price $0.15 per 1M input and $0.60 per 1M
  output tokens.
- Daily judge: Groq `qwen/qwen3.8-27b` (Alibaba family). Price $0.80 per 1M input and $4.00 per 1M
  output tokens. Different family from the generator, as the plan requires.
- Calibration cross check judge (40 items only): OpenRouter `google/gemma-4-31b-it:free`, fallback
  `nvidia/nemotron-3-super-120b-a12b:free`. Both exist in the live list. The `openrouter/free` router
  is never used, because it hides which model answered.
- Limits seen on the Groq account: 8,000 tokens per minute and 1,000 requests per day for each of the
  two models; the docs list 200,000 tokens per day per model (the headers do not show the daily token
  limit, so this is the documented figure). Working budget: about 200K generator tokens and 200K judge
  tokens per day. One answer call is roughly 1.5K to 3K tokens, so a day allows about 70 to 130 real
  answers. A full eval of 75 items with a judge call each will not fit in one day on the free tier, so
  eval runs must use the disk cache and may be spread over two days.
- OpenRouter: about 50 requests per day, free models only (ids end in `:free`).
- Weakness to remember: the generator and the daily judge both run on Groq. They are different model
  families, but an outage, a rate limit or a change of Groq's serving setup hits both at once, and the
  shared serving stack can share quirks. The 40 item cross check on OpenRouter is how we measure
  whether the daily judge can be trusted.
- Data rule: only the public seed corpus (openFDA, MedlinePlus) and golden set questions are ever sent
  to a free model. No real patient data and none of the owner's private documents.
- Tests use a fake LLM client. Only `scripts/smoke_llm.py` calls the real provider.

## 2026-10-13: how AC-GEN-05 is read (task T078a)
PRD wording: "WHEN a question asks for a personal diagnosis or a dose THE system SHALL refuse with the
policy message." The words "personal diagnosis" are clear, but "a dose" alone could mean any dose
question, which would also block "what does the label say about the recommended dose". Reading used,
as agreed with the owner:
- Answer, with citation and disclaimer, when the question asks what a document or label says
  (recommended dose, side effects, uses, how a condition is diagnosed in general).
- Refuse with the policy message and point to a doctor or pharmacist when the question asks what THIS
  person should take, or whether THEY have a condition. "This person" is the asker, a relative they
  name, or "the patient".
- When unsure, refuse.
How it works: `guardrails/input.py` refuses only when two things are both present: a word that points at
a specific person (I, my, me, we, he, she, the patient) and a cue for a dose decision (dose, how much,
should I take, safe for me) or a diagnosis (do I have, diagnose, what is wrong with me). Simple patterns
are a first filter, not the whole defense. The refusal skips retrieval and the model, uses the fixed
`REFUSAL_MESSAGE` plus the disclaimer, and stores `unsafe_request` and the reason in the trace.
Known limits: patterns miss unusual phrasings and can refuse harmless questions such as "How much
should I know about aspirin dose?". A mixed question ("According to the label, what dose should I
take?") is refused, on purpose. Measure on the policy slice of the golden set in phase 4.

## 2026-10-13: eval pacing, cache and budget guard
Decided with the owner after the phase 3 token measurements (numbers in `docs/modules/evals.md`).
- The pacer (`llm/pacer.py`) works inside one process. Limit of that choice: two processes using the
  same key (for example an eval run and the API, or two parallel runs) do not see each other, so
  together they can pass the per minute or per day limit. For now run one eval at a time and keep the
  API idle during a full run. A shared limiter in Redis is the fix if this becomes a problem.
- The daily budget guard stops at 85 percent of the documented daily token limit and keeps its own
  ledger of tokens used in the last 24 hours. Groq's docs do not say when the daily limit resets; the
  reset header (1 minute 26.4 seconds for 1,000 requests a day) suggests continuous refill, so the
  guard uses a rolling 24 hour window. Unverified until a real daily 429 shows its wait time.
- OpenRouter free models: 20 requests per minute, 50 requests per day, counted per UTC day.
- B0 is dense top-5 and is pinned in `evals/configs/b0.toml` with a content hash, frozen after its
  first stored result. The live API default stays hybrid; the difference is written in `evals.md`.
- Judge output uses JSON mode where supported, the parser strips a fenced json block, and parse
  failures are counted in the report.

## 2026-10-13: first person dose phrasing and what the adversarial slice measures (task T079j)
The phase 3 review found that "Is it ok for me to take 500 mg?" was not refused: it has a person word
but no dose cue. T079j adds cues for "ok, okay, fine, alright or safe" followed by "for me, him, her, us,
my X or the patient to take", and for "if or when" followed by a subject and take. "Safe for my child to
take X" was already refused. Label questions such as "Is it ok to take famotidine with food according to
the label?" still pass because they name no person.
- The filter stays pattern based on purpose. It is a first filter, not a classifier, and no attempt is made
  to cover every phrasing. Misses are expected.
- The adversarial slice of the golden set (T086) and the policy slice measure what the patterns miss.
  That miss rate is a reported number in Phase 4, not a bug to hide. Fixes come only from measured misses.
- Accepted trade-off, as before: when unsure the filter refuses, so some harmless questions are refused.

## 2026-10-13: the abstain threshold 0.0 is a placeholder
`ABSTAIN_POLICY` in `query/service.py` uses a default threshold of 0.0, so only an empty retrieval
abstains. The value is not tuned. It will be set in T102a from the B0 score distribution on the dev split.
Fused RRF scores are tiny (the maximum is about 0.033), so a threshold on them needs the measured
distribution, not a guess. Until T102a, the `weak_evidence` abstain path is not exercised live. It is
covered by unit tests with other thresholds only, so AC-GEN-03 must not be described as protection
against weak evidence in demos or in the README.
