"""Rule based query decomposition: one sub query per drug name in a multi drug question (E7).

No model is called. A question that names two or more different drugs is split so that each drug
gets its own retrieval, and the lists are merged with RRF by the caller.
"""

from __future__ import annotations

import re

from docdesk.ingestion.seed.drug_names import COMMON_DRUGS

# Words that often follow a generic name in a label title, such as "warfarin sodium".
SALT_WORDS = (
    "sodium", "hydrochloride", "carbonate", "calcium", "potassium", "sulfate", "hcl", "maleate",
    "tartrate", "acetate", "citrate", "succinate", "besylate", "mesylate", "phosphate",
    "bromide", "chloride", "hydrobromide", "fumarate",
)


def mention_pattern() -> re.Pattern[str]:
    """One regex for every known drug name, longest first, with an optional salt word."""
    names = sorted(COMMON_DRUGS, key=len, reverse=True)
    names_part = "|".join(re.escape(name) for name in names)
    salt_part = "|".join(SALT_WORDS)
    return re.compile(rf"\b(?:{names_part})(?:\s+(?:{salt_part}))?\b", re.IGNORECASE)


PATTERN = mention_pattern()


def drug_mentions(question: str) -> list[str]:
    """Distinct drug mentions in the order they appear, lowercased."""
    found: list[str] = []
    for match in PATTERN.finditer(question):
        name = match.group(0).lower()
        if name not in found:
            found.append(name)
    return found


def sub_queries(question: str) -> list[str]:
    """One query per drug when two or more different drugs are named, else an empty list.

    Each sub query is the drug name followed by the question with every drug mention removed,
    so the dense search is not pulled toward the other drug.
    """
    mentions = drug_mentions(question)
    if len(mentions) < 2:
        return []
    stem = " ".join(PATTERN.sub(" ", question).split())
    return [f"{mention} {stem}" for mention in mentions]
