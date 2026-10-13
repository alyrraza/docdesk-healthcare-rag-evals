"""Manual smoke test: ten questions through retrieval, the real Groq model and the trace (T078).

This is the ONLY place that calls a real model. Automated tests use a fake client.
Only public seed corpus questions are asked; no patient data and no private documents.

Usage:
    python scripts/smoke_llm.py            # needs GROQ_API_KEY in .env
Results go to .cache/smoke/smoke_llm.json (git-ignored). The key is never printed.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from docdesk.api.query_deps import build_counter, build_encoder, build_llm
from docdesk.core.config import get_settings
from docdesk.core.ids import new_trace_id
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import default_session_factory
from docdesk.prompts.registry import NoActivePromptError, activate, get_active, sync_prompts
from docdesk.query.service import answer_question

QUESTIONS = [
    "What are the common side effects of metoclopramide?",
    "What condition is glimepiride used to treat?",
    "What does the naproxen label warn about stomach bleeding?",
    "What is metabolic syndrome?",
    "What is levothyroxine used for?",
    "How is type 2 diabetes treated?",
    "What is atherosclerosis?",
    "What are the warnings for phenytoin sodium?",
    "What is the capital of France?",
    "What dose of famotidine should I take for my stomach pain?",
]
PAUSE_SECONDS = 20  # the free tier allows 8000 tokens per minute per model
OUT = Path(".cache/smoke/smoke_llm.json")


def main() -> None:
    """Run the questions, print a short table and save the full answers."""
    settings = get_settings()
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value():
        raise SystemExit("GROQ_API_KEY is missing in .env, the smoke test is blocked")
    llm = build_llm(settings.groq_api_key.get_secret_value())
    encoder, counter = build_encoder(settings.model_dir), build_counter(settings.model_dir)
    results = []
    with default_session_factory()() as session:
        sync_prompts(session, Path("prompts"))
        try:
            get_active(session, "answer")
        except NoActivePromptError:
            activate(session, "answer", "1.0.0", None)
        session.commit()
        prompt = get_active(session, "answer")
        admin = UserRepository(session).get_by_email(settings.admin_email or "")
        if admin is None:
            raise SystemExit("admin user not found, run scripts/seed_admin.py first")
        for index, question in enumerate(QUESTIONS):
            if index:
                time.sleep(PAUSE_SECONDS)
            trace_id = new_trace_id()
            answer = answer_question(
                session,
                trace_id=trace_id,
                user_id=uuid.UUID(str(admin.id)),
                question=question,
                encoder=encoder,
                counter=counter,
                llm=llm,
                prompt=prompt,
                model=settings.generator_model,
            )
            results.append(
                {
                    "question": question,
                    "answer": answer.output.answer,
                    "abstained": answer.abstained,
                    "abstain_reason": answer.output.abstain_reason,
                    "citations": [f"{c.label}: {c.document_title}" for c in answer.citations],
                    "flags": answer.flags,
                    "tokens_in": answer.tokens_in,
                    "tokens_out": answer.tokens_out,
                    "llm_calls": answer.llm_calls,
                    "retry_used": answer.retry_used,
                    "error_code": answer.error_code,
                    "model": answer.model,
                    "trace_id": trace_id,
                }
            )
            row = results[-1]
            print(
                f"{index + 1:>2}. abstained={row['abstained']!s:<5} tokens={row['tokens_in']}+"
                f"{row['tokens_out']} cites={len(row['citations'])} | {question}"
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    tokens = sum(r["tokens_in"] + r["tokens_out"] for r in results)
    print(f"total tokens used: {tokens}; full answers in {OUT}")


if __name__ == "__main__":
    main()
