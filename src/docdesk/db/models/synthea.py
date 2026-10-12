"""Synthetic patient tables for the SQL branch. Identifying columns are deliberately left out."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from docdesk.db.models.base import Base


class SyntheaPatientRow(Base):
    """One synthetic patient: demographics only, no names, SSN or address."""

    __tablename__ = "synthea_patients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    birthdate: Mapped[date] = mapped_column(Date, nullable=False)
    deathdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    race: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SyntheaConditionRow(Base):
    """A diagnosis recorded for a patient."""

    __tablename__ = "synthea_conditions"
    __table_args__ = (Index("ix_synthea_conditions_patient_id", "patient_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("synthea_patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    stop_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class SyntheaMedicationRow(Base):
    """A medication prescribed to a patient."""

    __tablename__ = "synthea_medications"
    __table_args__ = (Index("ix_synthea_medications_patient_id", "patient_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("synthea_patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stop_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dispenses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


class SyntheaEncounterRow(Base):
    """A visit between a patient and the health system."""

    __tablename__ = "synthea_encounters"
    __table_args__ = (Index("ix_synthea_encounters_patient_id", "patient_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("synthea_patients.id", ondelete="CASCADE"), nullable=False
    )
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stop_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    encounter_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_claim_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    reason_description: Mapped[str | None] = mapped_column(Text, nullable=True)
