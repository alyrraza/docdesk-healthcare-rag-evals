"""Content hash used to spot the same file uploaded twice by the same user (AC-ING-04)."""

from __future__ import annotations

import hashlib


def content_hash(data: bytes) -> str:
    """Fingerprint the file bytes so identical uploads can be detected without comparing text."""
    return hashlib.sha256(data).hexdigest()
