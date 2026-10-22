"""Tests for the Medication model."""

from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest

from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)


@pytest.fixture
def sample_medication() -> Medication:
    """Create a sample medication for testing."""
    return Medication(
        name="Metformin",
        dosage=Dosage(amount=500.0, unit=DosageUnit.MG),
        schedule=MedicationSchedule(
            frequency=FrequencyUnit.DAILY,
            times_per_day=2,
            specific_times=[time(8, 0), time(20, 0)],
        ),
        prescriber="Dr. Smith",
        pills_remaining=30,
    )


class TestDosage:
    def test_str_representation(self) -> None:
        dosage = Dosage(amount=500.0, unit=DosageUnit.MG)
        assert str(dosage) == "500.0 mg"

    def test_tablet_unit(self) -> None:
        dosage = Dosage(amount=1.0, unit=DosageUnit.TABLET)
        assert str(dosage) == "1.0 tablet"


class TestMedication:
    def test_is_active_for_current_medication(self, sample_medication: Medication) -> None:
        assert sample_medication.is_active() is True

    def test_is_inactive_for_future_start(self) -> None:
        med = Medication(
            name="FutureMed",
            dosage=Dosage(1.0, DosageUnit.TABLET),
            schedule=MedicationSchedule(FrequencyUnit.DAILY),
            start_date=datetime.now() + timedelta(days=7),
        )
        assert med.is_active() is False

    def test_is_inactive_after_end_date(self, sample_medication: Medication) -> None:
        sample_medication.end_date = datetime.now() - timedelta(days=1)
        assert sample_medication.is_active() is False

    def test_needs_refill_when_low(self, sample_medication: Medication) -> None:
        sample_medication.pills_remaining = 5
        assert sample_medication.needs_refill(threshold=7) is True

    def test_does_not_need_refill_when_sufficient(self, sample_medication: Medication) -> None:
        sample_medication.pills_remaining = 30
        assert sample_medication.needs_refill(threshold=7) is False

    def test_take_dose_decrements_pills(self, sample_medication: Medication) -> None:
        initial = sample_medication.pills_remaining
        result = sample_medication.take_dose()
        assert result is True
        assert sample_medication.pills_remaining == initial - 1

    def test_take_dose_fails_when_empty(self, sample_medication: Medication) -> None:
        sample_medication.pills_remaining = 0
        result = sample_medication.take_dose()
        assert result is False

    def test_str_contains_name(self, sample_medication: Medication) -> None:
        assert "Metformin" in str(sample_medication)

    def test_str_contains_status(self, sample_medication: Medication) -> None:
        assert "Active" in str(sample_medication)
