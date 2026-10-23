"""Database layer for SmartMeds."""

from smartmeds.db.base import DatabaseBackend, DoseLogDoc, MedicationDoc
from smartmeds.db.database import Database
from smartmeds.db.factory import create_database
from smartmeds.db.mappers import (
    doc_to_medication,
    dose_log_to_doc,
    medication_to_doc,
)

__all__ = [
    "Database",
    "DatabaseBackend",
    "DoseLogDoc",
    "MedicationDoc",
    "create_database",
    "doc_to_medication",
    "dose_log_to_doc",
    "medication_to_doc",
]
