# DocDesk v2

Healthcare RAG service with a built-in evaluation harness.

Status: early scaffolding. Results sections come later (see `docs/PLAN.md`).

## Setup on Windows (everything on drive D:)

C: is full on the development laptop, so the project, the virtual environment and every
cache live inside this folder. Nothing is installed or cached on C:.

```powershell
cd "D:\MLOps\DocDesk v2\docdesk-context-pack"
python -m venv .venv
$env:PIP_CACHE_DIR = "$PWD\.cache\pip"
$env:TEMP = "$PWD\.cache\tmp"; $env:TMP = "$PWD\.cache\tmp"
$env:HF_HOME = "$PWD\.cache\hf"
New-Item -ItemType Directory -Force .cache\pip, .cache\tmp, .cache\hf | Out-Null
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env   # then edit the values
git config core.hooksPath .githooks
```

`.cache/` and `.env` are git-ignored. Activate the venv before committing, or the hooks
cannot find ruff.

## Checks

```powershell
python -m ruff check .
python -m pytest -q
python scripts/check_file_length.py
python scripts/check_docs_style.py
```

## Tested versions

Python 3.11.4, fastapi 0.143.0, starlette 1.7.0, pydantic 2.14.1, pydantic-settings 2.15.0,
httpx 0.28.1, pytest 9.1.1, ruff 0.17.0.

## Services

Docker is not run on the development laptop. Dockerfiles are written and built in CI.
Postgres with pgvector comes from a hosted free tier, Redis from Memurai. See `docs/REMEMBER.md`.
