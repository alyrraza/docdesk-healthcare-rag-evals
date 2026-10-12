# Remember

Created 2026-10-13. Facts about this machine and this owner that are easy to forget and
expensive to rediscover.

## Disk and environment
- Everything goes on drive D:. C: has under 2 GB free. Put these on D: before the first install:
  - the project folder and the virtual environment
  - `PIP_CACHE_DIR`, for example `D:\dev-cache\pip`
  - `HF_HOME`, for example `D:\dev-cache\huggingface` (the embedding model cache)
  - `npm config set cache D:\dev-cache\npm` for the frontend
- D: had about 9 GB free on 2026-10-13. This stack without Docker needs roughly 2 to 3 GB. If free
  space drops under 2 GB, stop and clean before installing anything.
- The first message of this project said "local disk C". C: is full, so the working assumption is D:.
  If that is wrong, tell Claude before the first install.
- Docker is not installed and will not be installed. We write Dockerfiles and a compose file, and
  GitHub Actions builds the image. Do not try to run `docker` locally.
- Python 3.11.4 is installed. Use a venv inside the project folder on D:.

## Services without Docker
- Postgres with pgvector: a hosted free tier (Neon or Supabase). The network round trip inflates
  vector search latency, so report database time as its own stage and note the environment in the
  README. If a native Windows Postgres with pgvector works cleanly, prefer it for latency numbers.
- Redis: Memurai Developer (Windows native).
- Celery on Windows: run workers with `--pool=solo` (or `--pool=threads`). The default prefork pool
  does not work properly. Record this as an error and fix in `PROJECT_NOTES.md`.
- Embeddings: download a pre-exported ONNX model from Hugging Face. No PyTorch install.
- Free LLM tiers have rate limits. Check them before planning an eval run, and rely on the disk
  cache so a rerun never pays twice.

## Habits that keep the history clean
- Activate the venv before committing, or the hooks cannot find ruff.
- `git config core.hooksPath .githooks` once per clone.
- Windows line endings: keep `.gitattributes` with `* text=auto` and `*.sh text eol=lf`
  (the hook scripts must be LF or they fail).
- Shell is Git Bash or PowerShell. Use `python`, not `python3`, in commands.

## Owner expectations
- Ali must be able to explain every function in an interview. Explain after writing, in plain
  English, with the trade-off.
- Explanations in the chat may be in Roman Urdu. All files and code comments are in English.
- No em dash and no en dash anywhere in markdown.
- Concepts first, code second: when a new concept appears (BM25, RRF, kappa), explain it with an
  analogy before using it.
- A project is not listed on the CV until the README standard in the strategy doc is met.
  Until a hosted deployment exists, the honest CV wording is "containerized, image built in CI".
- No Stripe, no payments. That is already shown in a separate paid client project.
- Scope creep is the known risk. If a new idea appears mid-phase, write it in `DECISIONS.md`
  under "parked" and keep going.
