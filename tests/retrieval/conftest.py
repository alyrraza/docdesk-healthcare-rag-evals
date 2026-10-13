"""Fixtures for retrieval tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from fakes.corpus import Corpus


@pytest.fixture
def corpus(db_session: Session) -> Corpus:
    """A builder bound to the rolled back test session."""
    return Corpus(db_session)
