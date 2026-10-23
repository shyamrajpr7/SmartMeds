"""
MongoDB database handler for SmartMeds.

Provides persistence for medications, dose logs, and user preferences using
PyMongo against a MongoDB server (local or Atlas).

Documents use the same shape as the SQL backends, so records are portable
between SQLite and MongoDB:

    {
        "_id": "b1f3...",
        "name": "Metformin",
        "dosage_amount": 500.0,
        "dosage_unit": "mg",
        "frequency": "daily",
        "times_per_day": 2,
        "specific_times": "08:00,20:00",
        ...
    }
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from smartmeds.db.base import DatabaseBackend, DoseLogDoc, MedicationDoc
from smartmeds.utils.config import DEFAULT_MONGODB_DATABASE, DEFAULT_MONGODB_URI
from smartmeds.utils.helpers import redact_uri
from smartmeds.utils.logger import get_logger

logger = get_logger(__name__)

MEDICATIONS_COLLECTION = "medications"
DOSE_LOGS_COLLECTION = "dose_logs"


class MongoDatabase(DatabaseBackend):
    """
    MongoDB manager for SmartMeds.

    Handles all persistence operations using PyMongo.

    Example:
        >>> db = MongoDatabase(uri="mongodb://localhost:27017")
        >>> db.connect()
        >>> records = db.get_all_medications()

    Args:
        uri: MongoDB connection string.
        database: Name of the database to use.
        client: Optional pre-built ``MongoClient`` (useful for tests).
        timeout_ms: Server selection timeout in milliseconds. Atlas needs a
            generous value: SRV lookup, TLS handshake and authentication can
            take several seconds on a cold or paused cluster.
    """

    backend_name = "mongodb"

    def __init__(
        self,
        uri: str = DEFAULT_MONGODB_URI,
        database: str = DEFAULT_MONGODB_DATABASE,
        client: Optional[Any] = None,
        timeout_ms: int = 30000,
        connect_timeout_ms: int = 10000,
    ) -> None:
        self._uri = uri
        self._database_name = database
        self._client: Any = client
        self._timeout_ms = timeout_ms
        self._connect_timeout_ms = connect_timeout_ms
        self._db: Any = None
        self._medications: Any = None
        self._dose_logs: Any = None

    @property
    def database_name(self) -> str:
        """Name of the MongoDB database in use."""
        return self._database_name

    def connect(self) -> None:
        """Open the connection to MongoDB and ensure indexes exist."""
        if self._db is not None:
            return

        if self._client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:  # pragma: no cover - depends on env
                raise RuntimeError(
                    "pymongo is required for the MongoDB backend. "
                    "Install it with 'pip install pymongo'."
                ) from exc
            self._client = MongoClient(
                self._uri,
                serverSelectionTimeoutMS=self._timeout_ms,
                connectTimeoutMS=self._connect_timeout_ms,
                appname="smartmeds",
            )
            self._client.admin.command("ping")

        self._db = self._client[self._database_name]
        self._medications = self._db[MEDICATIONS_COLLECTION]
        self._dose_logs = self._db[DOSE_LOGS_COLLECTION]
        self._ensure_indexes()
        logger.info(
            "Database connected: %s/%s",
            redact_uri(self._uri),
            self._database_name,
        )

    def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client is not None:
            self._client.close()
        self._client = None
        self._db = None
        self._medications = None
        self._dose_logs = None

    def _ensure_indexes(self) -> None:
        """Create the indexes the application relies on."""
        self._medications.create_index([("name", 1)])
        self._dose_logs.create_index([("scheduled_time", -1)])
        self._dose_logs.create_index([("medication_id", 1)])

    def _require_collections(self) -> None:
        if self._medications is None or self._dose_logs is None:
            raise RuntimeError("Database not connected. Call connect() first.")

    @staticmethod
    def _to_medication_doc(doc: Mapping[str, Any]) -> MedicationDoc:
        """Convert a raw MongoDB document into the public document shape."""
        result = {key: value for key, value in doc.items() if key != "_id"}
        result["id"] = str(doc.get("_id"))
        return result

    @staticmethod
    def _to_dose_log_doc(doc: Mapping[str, Any]) -> DoseLogDoc:
        """Convert a raw dose log document into the public document shape."""
        result = {key: value for key, value in doc.items() if key != "_id"}
        result["id"] = str(doc.get("_id"))
        return result

    def save_medication(self, record: Mapping[str, Any]) -> MedicationDoc:
        """Persist a medication document to MongoDB."""
        self._require_collections()
        doc: Dict[str, Any] = dict(record)
        doc.pop("id", None)
        doc["_id"] = uuid.uuid4().hex
        doc.setdefault("created_at", datetime.now())
        doc["updated_at"] = datetime.now()
        self._medications.insert_one(doc)
        logger.info("Saved medication: %s (id=%s)", doc.get("name"), doc["_id"])
        return self._to_medication_doc(doc)

    def get_all_medications(self) -> List[MedicationDoc]:
        """Retrieve all medication documents."""
        self._require_collections()
        cursor = self._medications.find().sort("created_at", 1)
        return [self._to_medication_doc(doc) for doc in cursor]

    def get_medication(self, medication_id: str) -> Optional[MedicationDoc]:
        """Find a medication document by ID."""
        self._require_collections()
        doc = self._medications.find_one({"_id": str(medication_id)})
        return self._to_medication_doc(doc) if doc else None

    def get_medication_by_name(self, name: str) -> Optional[MedicationDoc]:
        """Find a medication document by name (case-insensitive)."""
        self._require_collections()
        pattern = f"^{re.escape(name)}$"
        doc = self._medications.find_one({"name": {"$regex": pattern, "$options": "i"}})
        return self._to_medication_doc(doc) if doc else None

    def update_medication(self, medication_id: str, updates: Mapping[str, Any]) -> bool:
        """Apply field updates to a medication document."""
        self._require_collections()
        changes = dict(updates)
        changes["updated_at"] = datetime.now()
        result = self._medications.update_one(
            {"_id": str(medication_id)}, {"$set": changes}
        )
        return bool(result.matched_count > 0)

    def delete_medication(self, medication_id: str) -> bool:
        """Delete a medication document by ID."""
        self._require_collections()
        result = self._medications.delete_one({"_id": str(medication_id)})
        return bool(result.deleted_count > 0)

    def log_dose(self, log: Mapping[str, Any]) -> DoseLogDoc:
        """Record a dose log entry."""
        self._require_collections()
        doc: Dict[str, Any] = dict(log)
        doc.pop("id", None)
        doc["_id"] = uuid.uuid4().hex
        doc.setdefault("logged_at", datetime.now())
        self._dose_logs.insert_one(doc)
        logger.info("Logged dose: %s (id=%s)", doc.get("medication_name"), doc["_id"])
        return self._to_dose_log_doc(doc)

    def get_dose_logs(
        self,
        medication_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DoseLogDoc]:
        """Retrieve dose log entries, optionally filtered by medication."""
        self._require_collections()
        query: Dict[str, Any] = {}
        if medication_id is not None:
            query["medication_id"] = medication_id
        cursor = self._dose_logs.find(query).sort("scheduled_time", -1).limit(limit)
        return [self._to_dose_log_doc(doc) for doc in cursor]
