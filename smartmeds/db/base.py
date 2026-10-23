"""
Storage-agnostic database interface for SmartMeds.

Every backend (SQLite, MongoDB, ...) implements :class:`DatabaseBackend`, so
the rest of the application never needs to know where data lives. Records are
plain dictionaries ("documents") to keep the interface identical across
backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping, Optional

MedicationDoc = Dict[str, Any]
DoseLogDoc = Dict[str, Any]


class DatabaseBackend(ABC):
    """
    Common persistence interface implemented by every storage backend.

    Example:
        >>> with create_database() as db:
        ...     db.save_medication({"name": "Aspirin"})
    """

    backend_name: str = "base"

    @abstractmethod
    def connect(self) -> None:
        """Open the connection and prepare the storage."""

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the connection."""

    @abstractmethod
    def save_medication(self, record: Mapping[str, Any]) -> MedicationDoc:
        """Insert a medication and return the stored document."""

    @abstractmethod
    def get_all_medications(self) -> List[MedicationDoc]:
        """Return every stored medication document."""

    @abstractmethod
    def get_medication(self, medication_id: str) -> Optional[MedicationDoc]:
        """Return a medication document by ID, or None if it does not exist."""

    @abstractmethod
    def get_medication_by_name(self, name: str) -> Optional[MedicationDoc]:
        """Return a medication document by name (case-insensitive), or None."""

    @abstractmethod
    def update_medication(self, medication_id: str, updates: Mapping[str, Any]) -> bool:
        """Apply field updates to a medication. Returns True if it existed."""

    @abstractmethod
    def delete_medication(self, medication_id: str) -> bool:
        """Delete a medication. Returns True if something was deleted."""

    @abstractmethod
    def log_dose(self, log: Mapping[str, Any]) -> DoseLogDoc:
        """Insert a dose log entry and return the stored document."""

    @abstractmethod
    def get_dose_logs(
        self,
        medication_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DoseLogDoc]:
        """Return dose log entries, newest first, optionally filtered."""

    def __enter__(self) -> "DatabaseBackend":
        self.connect()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
