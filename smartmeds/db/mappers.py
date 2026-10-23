"""
Conversions between domain objects and storage documents.

The document shape is shared by every backend, so a record written to SQLite
can be read back from MongoDB unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.db.base import DoseLogDoc, MedicationDoc
from smartmeds.utils.helpers import parse_times

DEFAULT_TIME = "08:00"


def _parse_time_list(value: Optional[str]) -> List[Any]:
    """Parse a comma-separated HH:MM string into a list of times."""
    if not value:
        return []
    try:
        return parse_times(value)
    except ValueError:
        return []


def dosage_to_fields(dosage: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Convert a dosage payload into storage fields.

    Args:
        dosage: A mapping with ``amount`` and ``unit`` keys.

    Returns:
        The storage fields describing the dosage.
    """
    return {
        "dosage_amount": float(dosage["amount"]),
        "dosage_unit": DosageUnit(dosage["unit"]).value,
    }


def schedule_to_fields(schedule: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Convert a schedule payload into storage fields.

    Args:
        schedule: A mapping with ``frequency``, ``times_per_day`` and ``times``.

    Returns:
        The storage fields describing the schedule.
    """
    times = list(schedule.get("times") or [])
    return {
        "frequency": FrequencyUnit(schedule.get("frequency", "daily")).value,
        "times_per_day": int(schedule.get("times_per_day") or len(times) or 1),
        "specific_times": ",".join(t.strftime("%H:%M") for t in times),
    }


def medication_to_doc(medication: Medication) -> MedicationDoc:
    """
    Convert a :class:`Medication` into a storable document.

    Args:
        medication: The domain object to convert.

    Returns:
        A document without an ``id`` (assigned by the backend on insert).
    """
    now = datetime.now()
    return {
        "name": medication.name,
        "dosage_amount": medication.dosage.amount,
        "dosage_unit": medication.dosage.unit.value,
        "frequency": medication.schedule.frequency.value,
        "times_per_day": medication.schedule.times_per_day,
        "specific_times": ",".join(
            t.strftime("%H:%M") for t in medication.schedule.specific_times
        ),
        "prescriber": medication.prescriber,
        "start_date": medication.start_date,
        "end_date": medication.end_date,
        "notes": medication.notes,
        "refill_date": medication.refill_date,
        "pills_remaining": medication.pills_remaining,
        "created_at": now,
        "updated_at": now,
    }


def doc_to_medication(doc: Mapping[str, Any]) -> Medication:
    """
    Convert a stored document back into a :class:`Medication`.

    Args:
        doc: A medication document as returned by a backend.

    Returns:
        The reconstructed domain object.
    """
    times = _parse_time_list(doc.get("specific_times")) or _parse_time_list(
        DEFAULT_TIME
    )
    try:
        unit = DosageUnit(doc.get("dosage_unit", DosageUnit.TABLET.value))
    except ValueError:
        unit = DosageUnit.TABLET
    try:
        frequency = FrequencyUnit(doc.get("frequency", FrequencyUnit.DAILY.value))
    except ValueError:
        frequency = FrequencyUnit.DAILY

    medication_id = doc.get("id")
    return Medication(
        name=doc.get("name", ""),
        dosage=Dosage(amount=float(doc.get("dosage_amount") or 0), unit=unit),
        schedule=MedicationSchedule(
            frequency=frequency,
            times_per_day=int(doc.get("times_per_day") or len(times) or 1),
            specific_times=times,
        ),
        prescriber=doc.get("prescriber"),
        start_date=doc.get("start_date") or datetime.now(),
        end_date=doc.get("end_date"),
        notes=doc.get("notes") or "",
        refill_date=doc.get("refill_date"),
        pills_remaining=doc.get("pills_remaining"),
        medication_id=str(medication_id) if medication_id is not None else None,
    )


def dose_log_to_doc(
    medication_id: Optional[str],
    medication_name: str,
    scheduled_time: datetime,
    taken: bool = False,
    taken_at: Optional[datetime] = None,
    skipped: bool = False,
    notes: str = "",
) -> DoseLogDoc:
    """
    Build a dose log document.

    Args:
        medication_id: Identifier of the related medication.
        medication_name: Name of the related medication.
        scheduled_time: When the dose was scheduled for.
        taken: Whether the dose was taken.
        taken_at: When the dose was taken.
        skipped: Whether the dose was skipped.
        notes: Free-form notes.

    Returns:
        The dose log document.
    """
    return {
        "medication_id": medication_id,
        "medication_name": medication_name,
        "scheduled_time": scheduled_time,
        "taken_at": taken_at,
        "taken": taken,
        "skipped": skipped,
        "notes": notes,
        "logged_at": datetime.now(),
    }
