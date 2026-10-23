"""
Tests for the HTTP API.

Uses ``mongomock`` so the suite runs without a MongoDB server.
"""

import pytest
from fastapi.testclient import TestClient

from smartmeds.api import dependencies
from smartmeds.api.app import app


@pytest.fixture
def client(monkeypatch):
    """A test client backed by an in-memory mongomock database."""
    mongomock = pytest.importorskip("mongomock")
    import pymongo

    monkeypatch.setattr(pymongo, "MongoClient", mongomock.MongoClient)
    monkeypatch.setenv("SMARTMEDS_DB_BACKEND", "mongodb")
    monkeypatch.setenv("SMARTMEDS_MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("SMARTMEDS_MONGODB_DB", "smartmeds_test")

    dependencies.reset_db()
    with TestClient(app) as test_client:
        yield test_client
    dependencies.reset_db()


@pytest.fixture
def medication_payload():
    """A valid medication creation payload."""
    return {
        "name": "Metformin",
        "dosage": {"amount": 500, "unit": "mg"},
        "schedule": {
            "frequency": "daily",
            "times_per_day": 2,
            "times": ["08:00:00", "20:00:00"],
        },
        "prescriber": "Dr. House",
        "notes": "Take with food",
        "pills_remaining": 30,
    }


class TestHealth:
    def test_health_reports_backend(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["backend"] == "mongodb"

    def test_health_is_also_under_api_prefix(self, client):
        assert client.get("/api/health").status_code == 200

    def test_root_lists_endpoints(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "endpoints" in response.json()


class TestMedications:
    def test_create_medication(self, client, medication_payload):
        response = client.post("/api/medications", json=medication_payload)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Metformin"
        assert body["dosage"] == {"amount": 500.0, "unit": "mg"}
        assert body["schedule"]["times"] == ["08:00:00", "20:00:00"]
        assert body["id"]

    def test_list_medications(self, client, medication_payload):
        client.post("/api/medications", json=medication_payload)
        client.post(
            "/api/medications",
            json={**medication_payload, "name": "Aspirin"},
        )

        response = client.get("/api/medications")

        assert response.status_code == 200
        assert {m["name"] for m in response.json()} == {"Metformin", "Aspirin"}

    def test_get_medication(self, client, medication_payload):
        created = client.post("/api/medications", json=medication_payload).json()

        response = client.get(f"/api/medications/{created['id']}")

        assert response.status_code == 200
        assert response.json()["name"] == "Metformin"

    def test_get_unknown_medication_returns_404(self, client):
        assert client.get("/api/medications/missing").status_code == 404

    def test_update_medication(self, client, medication_payload):
        created = client.post("/api/medications", json=medication_payload).json()

        response = client.patch(
            f"/api/medications/{created['id']}",
            json={"pills_remaining": 5, "notes": "Updated"},
        )

        assert response.status_code == 200
        assert response.json()["pills_remaining"] == 5
        assert response.json()["notes"] == "Updated"

    def test_update_unknown_medication_returns_404(self, client):
        response = client.patch("/api/medications/missing", json={"notes": "x"})
        assert response.status_code == 404

    def test_delete_medication(self, client, medication_payload):
        created = client.post("/api/medications", json=medication_payload).json()

        assert client.delete(f"/api/medications/{created['id']}").status_code == 204
        assert client.get(f"/api/medications/{created['id']}").status_code == 404

    def test_delete_unknown_medication_returns_404(self, client):
        assert client.delete("/api/medications/missing").status_code == 404

    def test_invalid_payload_returns_422(self, client):
        response = client.post("/api/medications", json={"name": "No dosage"})
        assert response.status_code == 422


class TestSchedule:
    def test_schedule_lists_upcoming_doses(self, client, medication_payload):
        client.post("/api/medications", json=medication_payload)

        response = client.get("/api/schedule")

        assert response.status_code == 200
        assert response.json()[0]["medication"] == "Metformin"

    def test_schedule_is_empty_without_medications(self, client):
        assert client.get("/api/schedule").json() == []


class TestDoseLogs:
    def test_create_dose_log(self, client, medication_payload):
        created = client.post("/api/medications", json=medication_payload).json()

        response = client.post(
            "/api/dose-logs",
            json={
                "medication_id": created["id"],
                "scheduled_time": "2024-01-01T08:00:00",
                "taken": True,
                "taken_at": "2024-01-01T08:05:00",
            },
        )

        assert response.status_code == 201
        assert response.json()["medication_name"] == "Metformin"
        assert response.json()["taken"] is True

    def test_list_dose_logs(self, client, medication_payload):
        created = client.post("/api/medications", json=medication_payload).json()
        client.post(
            "/api/dose-logs",
            json={
                "medication_id": created["id"],
                "scheduled_time": "2024-01-01T08:00:00",
                "taken": True,
            },
        )

        response = client.get("/api/dose-logs")

        assert response.status_code == 200
        assert len(response.json()) == 1


class TestInteractions:
    def test_check_interactions(self, client):
        response = client.post(
            "/api/interactions/check",
            json={"medications": ["warfarin", "aspirin"]},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["severity"] == "high"

    def test_check_requires_two_medications(self, client):
        response = client.post(
            "/api/interactions/check", json={"medications": ["aspirin"]}
        )
        assert response.status_code == 422
