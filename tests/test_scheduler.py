"""Tests for the MedicationScheduler."""

from __future__ import annotations

from datetime import time

import pytest

from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.core.scheduler import DoseEvent, MedicationScheduler


@pytest.fixture
def scheduler() -> MedicationScheduler:
    return MedicationScheduler()


@pytest.fixture
def sample_med() -> Medication:
    return Medication(
        name="Aspirin",
        dosage=Dosage(100.0, DosageUnit.MG),
        schedule=MedicationSchedule(
            frequency=FrequencyUnit.DAILY,
            specific_times=[time(8, 0), time(20, 0)],
        ),
    )


class TestMedicationScheduler:
    def test_add_medication(self, scheduler: MedicationScheduler, sample_med: Medication) -> None:
        scheduler.add_medication(sample_med)
        assert len(scheduler) == 1

    def test_remove_medication(self, scheduler: MedicationScheduler, sample_med: Medication) -> None:
        scheduler.add_medication(sample_med)
        result = scheduler.remove_medication("Aspirin")
        assert result is True
        assert len(scheduler) == 0

    def test_remove_nonexistent_medication(self, scheduler: MedicationScheduler) -> None:
        result = scheduler.remove_medication("DoesNotExist")
        assert result is False

    def test_list_medications(self, scheduler: MedicationScheduler, sample_med: Medication) -> None:
        scheduler.add_medication(sample_med)
        meds = scheduler.list_medications()
        assert len(meds) == 1
        assert meds[0].name == "Aspirin"

    def test_get_upcoming_doses_returns_sorted_events(
        self, scheduler: MedicationScheduler, sample_med: Medication
    ) -> None:
        scheduler.add_medication(sample_med)
        events = scheduler.get_upcoming_doses(hours=24)
        if len(events) > 1:
            for i in range(len(events) - 1):
                assert events[i].scheduled_time <= events[i + 1].scheduled_time

    def test_register_callback(self, scheduler: MedicationScheduler) -> None:
        called_with = []

        def callback(med: Medication) -> None:
            called_with.append(med)

        scheduler.register_reminder_callback(callback)
        assert len(scheduler._callbacks) == 1


class TestDoseEvent:
    def test_mark_taken(self, sample_med: Medication) -> None:
        from datetime import datetime

        event = DoseEvent(sample_med, datetime.now())
        event.mark_taken()
        assert event.taken is True
        assert event.taken_at is not None

    def test_is_not_overdue_when_taken(self, sample_med: Medication) -> None:
        from datetime import datetime

        event = DoseEvent(sample_med, datetime.now())
        event.mark_taken()
        assert event.is_overdue() is False
