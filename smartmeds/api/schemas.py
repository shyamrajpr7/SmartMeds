"""
Request and response models for the SmartMeds HTTP API.

These models describe the JSON contract of the API. They are deliberately
decoupled from the storage documents so the wire format stays stable even if
the database layout changes.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field

from smartmeds.core.interactions import InteractionSeverity
from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.db.mappers import (
    doc_to_medication,
    dosage_to_fields,
    schedule_to_fields,
)


class DosageIn(BaseModel):
    """Dosage of a medication."""

    amount: float = Field(gt=0, description="Amount of the active ingredient")
    unit: DosageUnit = Field(description="Unit of the dosage")


class ScheduleIn(BaseModel):
    """When and how often a medication is taken."""

    frequency: FrequencyUnit = Field(default=FrequencyUnit.DAILY)
    times_per_day: int = Field(default=1, ge=1, le=24)
    times: List[time] = Field(
        default_factory=list,
        description="Times of day the medication is taken (HH:MM)",
    )


class MedicationIn(BaseModel):
    """Payload used to create a medication."""

    name: str = Field(min_length=1, max_length=255)
    dosage: DosageIn
    schedule: ScheduleIn
    prescriber: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: str = ""
    refill_date: Optional[datetime] = None
    pills_remaining: Optional[int] = Field(default=None, ge=0)


class MedicationPatch(BaseModel):
    """Payload used to update part of a medication."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    dosage: Optional[DosageIn] = None
    schedule: Optional[ScheduleIn] = None
    prescriber: Optional[str] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None
    refill_date: Optional[datetime] = None
    pills_remaining: Optional[int] = Field(default=None, ge=0)


class DosageOut(BaseModel):
    """Dosage as returned by the API."""

    amount: float
    unit: DosageUnit


class ScheduleOut(BaseModel):
    """Schedule as returned by the API."""

    frequency: FrequencyUnit
    times_per_day: int
    times: List[time]


class MedicationOut(BaseModel):
    """A medication as returned by the API."""

    id: str
    name: str
    dosage: DosageOut
    schedule: ScheduleOut
    prescriber: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    notes: str = ""
    refill_date: Optional[datetime] = None
    pills_remaining: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DoseLogIn(BaseModel):
    """Payload used to record a dose."""

    medication_id: str
    scheduled_time: datetime
    taken: bool = False
    taken_at: Optional[datetime] = None
    skipped: bool = False
    notes: str = ""


class DoseLogOut(BaseModel):
    """A dose log entry as returned by the API."""

    id: str
    medication_id: Optional[str] = None
    medication_name: str
    scheduled_time: datetime
    taken_at: Optional[datetime] = None
    taken: bool = False
    skipped: bool = False
    notes: str = ""
    logged_at: Optional[datetime] = None


class InteractionRequest(BaseModel):
    """Payload used to check for drug interactions."""

    medications: List[str] = Field(
        min_length=2,
        description="At least two medication names to compare",
    )


class InteractionOut(BaseModel):
    """A drug interaction as returned by the API."""

    drug_a: str
    drug_b: str
    severity: InteractionSeverity
    description: str
    recommendation: str


class DoseEventOut(BaseModel):
    """An upcoming dose as returned by the API."""

    medication: str
    dosage: str
    scheduled_time: datetime
    taken: bool
    overdue: bool


class HealthOut(BaseModel):
    """Service health information."""

    status: str
    version: str
    backend: str
    database: Optional[str] = None


def medication_from_payload(payload: MedicationIn) -> Medication:
    """
    Build a domain :class:`Medication` from a create payload.

    Args:
        payload: The validated request body.

    Returns:
        The domain object ready to be persisted.
    """
    times = payload.schedule.times or [time(8, 0)]
    return Medication(
        name=payload.name,
        dosage=Dosage(amount=payload.dosage.amount, unit=payload.dosage.unit),
        schedule=MedicationSchedule(
            frequency=payload.schedule.frequency,
            times_per_day=payload.schedule.times_per_day or len(times),
            specific_times=times,
        ),
        prescriber=payload.prescriber,
        start_date=payload.start_date or datetime.now(),
        end_date=payload.end_date,
        notes=payload.notes,
        refill_date=payload.refill_date,
        pills_remaining=payload.pills_remaining,
    )


def patch_to_updates(payload: MedicationPatch) -> Dict[str, Any]:
    """
    Translate a partial update into storage document fields.

    Args:
        payload: The validated request body.

    Returns:
        A mapping of storage fields to their new values.
    """
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "dosage" in updates:
        updates.update(dosage_to_fields(updates.pop("dosage")))
    if "schedule" in updates:
        updates.update(schedule_to_fields(updates.pop("schedule")))
    return updates


def medication_out(doc: Mapping[str, Any]) -> MedicationOut:
    """
    Convert a storage document into the API response model.

    Args:
        doc: A medication document as returned by a backend.

    Returns:
        The API representation of the medication.
    """
    medication = doc_to_medication(doc)
    return MedicationOut(
        id=str(doc.get("id", "")),
        name=medication.name,
        dosage=DosageOut(
            amount=medication.dosage.amount,
            unit=medication.dosage.unit,
        ),
        schedule=ScheduleOut(
            frequency=medication.schedule.frequency,
            times_per_day=medication.schedule.times_per_day,
            times=medication.schedule.specific_times,
        ),
        prescriber=medication.prescriber,
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        notes=medication.notes,
        refill_date=doc.get("refill_date"),
        pills_remaining=medication.pills_remaining,
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


def dose_log_out(doc: Mapping[str, Any]) -> DoseLogOut:
    """
    Convert a dose log document into the API response model.

    Args:
        doc: A dose log document as returned by a backend.

    Returns:
        The API representation of the dose log.
    """
    return DoseLogOut(
        id=str(doc.get("id", "")),
        medication_id=doc.get("medication_id"),
        medication_name=doc.get("medication_name", ""),
        scheduled_time=doc.get("scheduled_time") or datetime.now(),
        taken_at=doc.get("taken_at"),
        taken=bool(doc.get("taken", False)),
        skipped=bool(doc.get("skipped", False)),
        notes=doc.get("notes", ""),
        logged_at=doc.get("logged_at"),
    )
