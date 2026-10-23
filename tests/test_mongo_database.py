"""
Tests for the MongoDB backend.

Uses ``mongomock`` so the suite runs without a MongoDB server.
"""

from datetime import datetime, time, timedelta

import pytest

from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.db.mappers import doc_to_medication, medication_to_doc
from smartmeds.db.mongo_database import MongoDatabase


@pytest.fixture
def db():
    """A connected MongoDatabase backed by an in-memory mongomock client."""
    mongomock = pytest.importorskip("mongomock")
    database = MongoDatabase(client=mongomock.MongoClient(), database="smartmeds_test")
    database.connect()
    yield database
    database.close()


def _medication(name: str = "Metformin") -> Medication:
    return Medication(
        name=name,
        dosage=Dosage(amount=500.0, unit=DosageUnit.MG),
        schedule=MedicationSchedule(
            frequency=FrequencyUnit.DAILY,
            times_per_day=2,
            specific_times=[time(8, 0)],
        ),
        prescriber="Dr. House",
        notes="Take with food",
        pills_remaining=30,
    )


class TestMongoDatabase:
    def test_connect_creates_collections(self, db):
        assert db.get_all_medications() == []

    def test_save_medication_returns_id(self, db):
        doc = db.save_medication(medication_to_doc(_medication()))
        assert doc["id"]
        assert doc["name"] == "Metformin"
        assert doc["dosage_amount"] == 500.0
        assert doc["dosage_unit"] == "mg"

    def test_get_all_medications(self, db):
        db.save_medication(medication_to_doc(_medication("Aspirin")))
        db.save_medication(medication_to_doc(_medication("Metformin")))

        names = [doc["name"] for doc in db.get_all_medications()]
        assert names == ["Aspirin", "Metformin"]

    def test_get_medication_by_id(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))
        found = db.get_medication(saved["id"])

        assert found is not None
        assert found["name"] == "Metformin"

    def test_get_medication_by_name_is_case_insensitive(self, db):
        db.save_medication(medication_to_doc(_medication("Ibuprofen")))

        assert db.get_medication_by_name("ibuprofen") is not None
        assert db.get_medication_by_name("unknown") is None

    def test_update_medication(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))

        assert db.update_medication(saved["id"], {"pills_remaining": 3}) is True
        assert db.get_medication(saved["id"])["pills_remaining"] == 3
        assert db.update_medication("missing", {"pills_remaining": 1}) is False

    def test_delete_medication(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))

        assert db.delete_medication(saved["id"]) is True
        assert db.get_all_medications() == []
        assert db.delete_medication(saved["id"]) is False

    def test_log_dose(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))
        log = db.log_dose(
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

        assert log["id"]
        logs = db.get_dose_logs()
        assert len(logs) == 1
        assert logs[0]["medication_name"] == "Metformin"

    def test_get_dose_logs_filtered_by_medication(self, db):
        first = db.save_medication(medication_to_doc(_medication("Aspirin")))
        second = db.save_medication(medication_to_doc(_medication("Metformin")))

        base = {
            "scheduled_time": datetime.now(),
            "taken": False,
            "skipped": False,
            "notes": "",
        }
        db.log_dose(
            {**base, "medication_id": first["id"], "medication_name": "Aspirin"}
        )
        db.log_dose(
            {**base, "medication_id": second["id"], "medication_name": "Metformin"}
        )

        assert len(db.get_dose_logs(medication_id=first["id"])) == 1
        assert len(db.get_dose_logs()) == 2

    def test_get_dose_logs_respects_limit(self, db):
        saved = db.save_medication(medication_to_doc(_medication()))
        for offset in range(3):
            db.log_dose(
                {
                    "medication_id": saved["id"],
                    "medication_name": saved["name"],
                    "scheduled_time": datetime.now() + timedelta(minutes=offset),
                    "taken": False,
                    "skipped": False,
                    "notes": "",
                }
            )

        assert len(db.get_dose_logs(limit=2)) == 2

    def test_documents_survive_a_round_trip(self, db):
        medication = _medication()
        saved = db.save_medication(medication_to_doc(medication))

        restored = doc_to_medication(saved)
        assert restored.name == medication.name
        assert restored.dosage == medication.dosage
        assert restored.schedule.frequency == medication.schedule.frequency
        assert restored.pills_remaining == medication.pills_remaining
        assert restored.medication_id == saved["id"]
