"""
Medication model and related data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import List, Optional


class FrequencyUnit(str, Enum):
    """Units for medication frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AS_NEEDED = "as_needed"


class DosageUnit(str, Enum):
    """Units for medication dosage."""

    MG = "mg"
    ML = "ml"
    TABLET = "tablet"
    CAPSULE = "capsule"
    DROPS = "drops"
    UNITS = "units"


@dataclass
class Dosage:
    """Represents a single dosage specification."""

    amount: float
    unit: DosageUnit

    def __str__(self) -> str:
        return f"{self.amount} {self.unit.value}"


@dataclass
class MedicationSchedule:
    """Defines the schedule for taking a medication."""

    frequency: FrequencyUnit
    times_per_day: int = 1
    specific_times: List[time] = field(default_factory=list)
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday

    def __post_init__(self) -> None:
        if not self.specific_times:
            # Default to 8 AM if no specific times provided
            self.specific_times = [time(8, 0)]


@dataclass
class Medication:
    """
    Represents a medication with all its associated metadata.

    Attributes:
        name: The name of the medication.
        dosage: The dosage information.
        schedule: The schedule for taking the medication.
        prescriber: The prescribing doctor's name.
        start_date: When the medication regimen starts.
        end_date: Optional end date for the medication.
        notes: Any additional notes or instructions.
        refill_date: When a refill is needed.
        pills_remaining: Current pill count for refill tracking.
    """

    name: str
    dosage: Dosage
    schedule: MedicationSchedule
    prescriber: Optional[str] = None
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    notes: str = ""
    refill_date: Optional[datetime] = None
    pills_remaining: Optional[int] = None
    medication_id: Optional[int] = None

    def is_active(self) -> bool:
        """Check if the medication is currently active."""
        now = datetime.now()
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True

    def needs_refill(self, threshold: int = 7) -> bool:
        """
        Check if this medication needs a refill soon.

        Args:
            threshold: Number of pills remaining that triggers a refill warning.

        Returns:
            True if a refill is needed, False otherwise.
        """
        if self.pills_remaining is not None:
            return self.pills_remaining <= threshold
        if self.refill_date:
            return self.refill_date <= datetime.now()
        return False

    def take_dose(self) -> bool:
        """
        Record taking a dose of this medication.

        Returns:
            True if successful, False if no pills remaining.
        """
        if self.pills_remaining is not None:
            if self.pills_remaining <= 0:
                return False
            self.pills_remaining -= 1
        return True

    def __str__(self) -> str:
        status = "Active" if self.is_active() else "Inactive"
        return (
            f"💊 {self.name} | {self.dosage} | "
            f"{self.schedule.frequency.value} | [{status}]"
        )

    def __repr__(self) -> str:
        return (
            f"Medication(name={self.name!r}, dosage={self.dosage!r}, "
            f"schedule={self.schedule!r})"
        )
