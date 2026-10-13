"""Input policy: refuse personal dose or diagnosis requests (AC-GEN-05).

This is a first filter of simple patterns, not the whole defense. The rule has two parts that must
both hold to refuse: the question is about a specific person, and it asks what they should take or
whether they have a condition. A general question about a label, however it mentions doses, passes.
When the patterns are unsure the choice is to refuse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Who the question is about: the asker, a relative, or "the patient".
PERSON = re.compile(r"\b(i|i'm|i've|i'd|me|my|mine|myself|we|our|he|she|him|her|his|the patient)\b")
SUBJECT = r"(i|we|he|she|the patient|my \w+|our \w+)"

# What they want to know: what to take, or what they have.
DOSE_CUES = re.compile(
    r"\b(dose|dosage|dosing|how much|how many|how often|how long should)\b"
    rf"|\b(should|can|may|could|would|do|does) {SUBJECT} "
    r"(take|use|get|give|have|stop|start|be taking|be given)\b"
    r"|\bsafe for (me|him|her|my \w+|our \w+)\b"
    # "is it ok for me to take ...", "is it ok if I take ...", "is it okay when my son takes ..."
    r"|\b(ok|okay|fine|alright|safe) for (me|him|her|us|my \w+|our \w+|the patient) to "
    r"(take|use|have|get|stop|start)\b"
    rf"|\b(ok|okay|fine|alright|safe) (if|when) {SUBJECT} (take|takes|use|uses|have|has|get|gets)\b"
)
DIAGNOSIS_CUES = re.compile(
    rf"\b(do|does|did|am|is|are|could|might|may) {SUBJECT} (have|having|got|suffer)\b"
    r"|\bdiagnos(e|ing)\b"
    r"|\bwhat('s| is) wrong with\b"
    r"|\bwhat (do|does) \w+ have\b"
    r"|\bwhat could (it|this|that) be\b"
)


@dataclass(frozen=True)
class PolicyDecision:
    """Whether to refuse, and a short stable reason for the trace."""

    refused: bool
    reason: str


def check_policy(question: str) -> PolicyDecision:
    """Refuse only when a question about a specific person asks for a dose or a diagnosis."""
    text = " ".join(question.lower().split())
    if not PERSON.search(text):
        return PolicyDecision(False, "allowed")
    if DOSE_CUES.search(text) and not DIAGNOSIS_CUES.search(text):
        return PolicyDecision(True, "personal_dose")
    if DIAGNOSIS_CUES.search(text):
        return PolicyDecision(True, "personal_diagnosis")
    return PolicyDecision(False, "allowed")
