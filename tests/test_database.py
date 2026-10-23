"""
Tests for the SQLite backend.

The same expectations are shared by every backend, so the SQLite and MongoDB
implementations stay interchangeable.
"""

from datetime import datetime

import pytest

from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.db.database import Database
from smartmeds.db.mappers import doc_to_medication, medication_to_doc


@pytest.fixture
def db(tmp_path):
    """A connected SQLite database in a temporary directory."""
    database = Database(db_path=tmp_path / "smartmeds.db")
    database.connect()
    yield database
    database.close()


def _medication(name: str = "Metformin") -> Medication:
    return Medication(
        name=name,
        dosage=Dosage(amount=500.0, unit=DosageUnit.MG),
        schedule=MedicationSchedule(
            frequency=FrequencyUnit.DAILY,
            times_per_day=1,
            specific_times=[datetime.now().time()],
        ),
        prescriber="Dr. House",
        notes="Take with food",
        pills_remaining=30,
    )


class TestSQLiteDatabase:
    def test_save_and_list(self, db):
        db.save_medication(medication_to_doc(_medication("Aspirin")))
        db.save_medication(medication_to_doc(_medication("Metformin")))

        assert [doc["name"] for doc in db.get_all_medications()] == [
            "Aspirin",
            "Metformin",
        ]

    def test_get_medication_by_id(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))

        found = db.get_medication(saved["id"])
        assert found is not None
        assert found["name"] == "Metformin"
        assert db.get_medication("9999") is None

    def test_get_medication_by_name_is_case_insensitive(self, db):
        db.save_medication(medication_to_doc(_medication("Ibuprofen")))

        assert db.get_medication_by_name("ibuprofen") is not None
        assert db.get_medication_by_name("unknown") is None

    def test_update_medication(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))

        assert db.update_medication(saved["id"], {"pills_remaining": 2}) is True
        assert db.get_medication(saved["id"])["pills_remaining"] == 2
        assert db.update_medication("9999", {"pills_remaining": 1}) is False

    def test_delete_medication(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))

        assert db.delete_medication(saved["id"]) is True
        assert db.get_all_medications() == []
        assert db.delete_medication(saved["id"]) is False

    def test_log_dose(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))
        db.log_dose(
            {
                "medication_id": saved["id"],
                "medication_name": saved["name"],
                "scheduled_time": datetime.now(),
                "taken": True,
                "taken_at": datetime.now(),
                "skipped": False,
                "notes": "",
            }
        )

        logs = db.get_dose_logs()
        assert len(logs) == 1
        assert logs[0]["medication_name"] == "Metformin"
        assert len(db.get_dose_logs(medication_id=saved["id"])) == 1

    def test_documents_survive_a_round_trip(self, db):
        medication = _medication()
        saved = db.save_medication(medication_to_doc(medication))

        restored = doc_to_medication(saved)
        assert restored.name == medication.name
        assert restored.dosage == medication.dosage
        assert restored.pills_remaining == medication.pills_remaining
        assert restored.medication_id == saved["id"]
