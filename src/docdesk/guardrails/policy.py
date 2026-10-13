"""Fixed policy texts; the disclaimer is added by code so no model can leave it out (AC-GEN-06)."""

from __future__ import annotations

DISCLAIMER = (
    "This is general information from the provided documents and is not medical advice. "
    "Ask a doctor or pharmacist about your own situation."
)

REFUSAL_MESSAGE = (
    "I can't give a personal diagnosis or a dose for a specific person. "
    "Please ask a doctor or pharmacist."
)


def with_disclaimer(answer: str) -> str:
    """Append the disclaimer once, so every answer carries it however it was produced."""
    if answer.endswith(DISCLAIMER):
        return answer
    return f"{answer}\n\n{DISCLAIMER}"
