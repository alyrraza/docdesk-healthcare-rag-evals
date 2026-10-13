"""Table definitions, one file per table group."""

from docdesk.db.models.base import Base
from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.db.models.evals import EvalResultRow, EvalRunRow
from docdesk.db.models.fingerprint import CorpusFingerprintRow
from docdesk.db.models.prompts import ActivePromptRow, PromptVersionRow
from docdesk.db.models.synthea import (
    SyntheaConditionRow,
    SyntheaEncounterRow,
    SyntheaMedicationRow,
    SyntheaPatientRow,
)
from docdesk.db.models.traces import QueryTraceRow
from docdesk.db.models.users import UserRow

__all__ = [
    "ActivePromptRow",
    "Base",
    "ChunkRow",
    "CorpusFingerprintRow",
    "DocumentRow",
    "EvalResultRow",
    "EvalRunRow",
    "PromptVersionRow",
    "QueryTraceRow",
    "SyntheaConditionRow",
    "SyntheaEncounterRow",
    "SyntheaMedicationRow",
    "SyntheaPatientRow",
    "UserRow",
]
