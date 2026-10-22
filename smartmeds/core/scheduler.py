"""
Medication scheduler module.

Handles scheduling of medication reminders and tracking
of upcoming doses.
"""

from __future__ import annotations

import threading
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional

from smartmeds.core.medication import FrequencyUnit, Medication
from smartmeds.utils.logger import get_logger

logger = get_logger(__name__)

ReminderCallback = Callable[[Medication], None]


class DoseEvent:
    """Represents a scheduled dose event."""

    def __init__(self, medication: Medication, scheduled_time: datetime) -> None:
        self.medication = medication
        self.scheduled_time = scheduled_time
        self.taken: bool = False
        self.taken_at: Optional[datetime] = None

    def mark_taken(self) -> None:
        """Mark this dose as taken."""
        self.taken = True
        self.taken_at = datetime.now()
        self.medication.take_dose()
        logger.info("Dose taken: %s at %s", self.medication.name, self.taken_at)

    def is_overdue(self, grace_minutes: int = 30) -> bool:
        """Check if this dose is overdue."""
        if self.taken:
            return False
        deadline = self.scheduled_time + timedelta(minutes=grace_minutes)
        return datetime.now() > deadline

    def __str__(self) -> str:
        status = "✅ Taken" if self.taken else ("⚠️  Overdue" if self.is_overdue() else "⏳ Pending")
        return f"{self.medication.name} @ {self.scheduled_time.strftime('%H:%M')} — {status}"


class MedicationScheduler:
    """
    Manages medication schedules and dose tracking.

    Example:
        >>> scheduler = MedicationScheduler()
        >>> scheduler.add_medication(med)
        >>> upcoming = scheduler.get_upcoming_doses(hours=24)
    """

    def __init__(self) -> None:
        self._medications: Dict[str, Medication] = {}
        self._callbacks: List[ReminderCallback] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_medication(self, medication: Medication) -> None:
        """
        Add a medication to the scheduler.

        Args:
            medication: The Medication to schedule.
        """
        self._medications[medication.name] = medication
        logger.info("Added medication to scheduler: %s", medication.name)

    def remove_medication(self, name: str) -> bool:
        """
        Remove a medication from the scheduler.

        Args:
            name: Name of the medication to remove.

        Returns:
            True if removed, False if not found.
        """
        if name in self._medications:
            del self._medications[name]
            logger.info("Removed medication from scheduler: %s", name)
            return True
        return False

    def get_upcoming_doses(self, hours: int = 24) -> List[DoseEvent]:
        """
        Get all upcoming doses within the specified time window.

        Args:
            hours: Number of hours to look ahead.

        Returns:
            List of DoseEvents sorted by scheduled time.
        """
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        upcoming: List[DoseEvent] = []

        for medication in self._medications.values():
            if not medication.is_active():
                continue

            for dose_time in medication.schedule.specific_times:
                # Build today's and tomorrow's dose events
                for day_offset in range(2):
                    scheduled = datetime.combine(
                        (now + timedelta(days=day_offset)).date(), dose_time
                    )
                    if now <= scheduled <= cutoff:
                        upcoming.append(DoseEvent(medication, scheduled))

        return sorted(upcoming, key=lambda e: e.scheduled_time)

    def get_todays_schedule(self) -> List[DoseEvent]:
        """Get all doses scheduled for today."""
        return self.get_upcoming_doses(hours=24)

    def register_reminder_callback(self, callback: ReminderCallback) -> None:
        """
        Register a function to be called when a dose reminder fires.

        Args:
            callback: Function accepting a Medication instance.
        """
        self._callbacks.append(callback)

    def list_medications(self) -> List[Medication]:
        """Return all managed medications."""
        return list(self._medications.values())

    def __len__(self) -> int:
        return len(self._medications)
