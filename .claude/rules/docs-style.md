---
paths:
  - "**/*.md"
---

# Writing rules for every markdown file

- No em dash and no en dash anywhere. Rewrite the sentence or use a comma or colon.
  `python scripts/check_docs_style.py` enforces this and the commit hook runs it.
- Write like a confident human engineer: short, specific sentences. No filler openers,
  no "leverage", "robust", "seamless", "delve".
- README and LinkedIn text must sound like Ali wrote them. State what was measured,
  with the number, and what trade-off was accepted.
- Date every spec. When a decision changes, add a dated note and mark the old text superseded.
