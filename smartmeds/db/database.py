"""
SQLite database handler for SmartMeds.

Provides persistence for medications, dose logs, and user preferences
using SQLAlchemy with a local SQLite database.

The public interface matches every other backend (see
:class:`smartmeds.db.base.DatabaseBackend`), so records can be moved between
SQLite and MongoDB without conversion.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, List, Mapping, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from smartmeds.db.base import DatabaseBackend, DoseLogDoc, MedicationDoc
from smartmeds.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DB_PATH = Path.home() / ".smartmeds" / "smartmeds.db"

MEDICATION_COLUMNS = (
    "name",
    "dosage_amount",
    "dosage_unit",
    "frequency",
    "times_per_day",
    "specific_times",
    "prescriber",
    "start_date",
    "end_date",
    "notes",
    "refill_date",
    "pills_remaining",
    "created_at",
    "updated_at",
)

DOSE_LOG_COLUMNS = (
    "medication_id",
    "medication_name",
    "scheduled_time",
    "taken_at",
    "taken",
    "skipped",
    "notes",
)


def _coerce_int_id(value: Any) -> Optional[int]:
    """Convert an identifier to an int, or None when it is not numeric."""
    if value is None or isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class MedicationRecord(Base):
    """ORM model for persisted medication data."""

    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    dosage_amount = Column(Float, nullable=False)
    dosage_unit = Column(String(50), nullable=False)
    frequency = Column(String(50), nullable=False)
    times_per_day = Column(Integer, default=1)
    specific_times = Column(Text, default="08:00")  # Comma-separated HH:MM
    prescriber = Column(String(255), nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    refill_date = Column(DateTime, nullable=True)
    pills_remaining = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DoseLog(Base):
    """ORM model for recording each dose taken."""

    __tablename__ = "dose_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, nullable=False, index=True)
    medication_name = Column(String(255), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    taken_at = Column(DateTime, nullable=True)
    taken = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    notes = Column(Text, default="")


class Database(DatabaseBackend):
    """
    SQLite database manager for SmartMeds.

    Handles all persistence operations using the SQLAlchemy ORM.

    Example:
        >>> db = Database()
        >>> db.connect()
        >>> records = db.get_all_medications()
    """

    backend_name = "sqlite"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._engine: Optional[Engine] = None
        self._SessionFactory: Optional[sessionmaker[Session]] = None

    @property
    def db_path(self) -> Path:
        """Path of the SQLite file backing this database."""
        return self._db_path

    def connect(self) -> None:
        """Initialize the database connection and create tables."""
        if self._SessionFactory is not None:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{self._db_path}"
        self._engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self._engine)
        self._SessionFactory = sessionmaker(bind=self._engine)
        logger.info("Database connected: %s", self._db_path)

    def close(self) -> None:
        """Dispose of the engine and release the connection pool."""
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        self._SessionFactory = None

    def _get_session(self) -> Session:
        if self._SessionFactory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._SessionFactory()

    @staticmethod
    def _model_to_doc(model: MedicationRecord) -> MedicationDoc:
        """Convert an ORM medication row into the public document shape."""
        doc = {column: getattr(model, column) for column in MEDICATION_COLUMNS}
        doc["id"] = str(model.id)
        return doc

    @staticmethod
    def _log_to_doc(model: DoseLog) -> DoseLogDoc:
        """Convert an ORM dose log row into the public document shape."""
        doc = {column: getattr(model, column) for column in DOSE_LOG_COLUMNS}
        doc["id"] = str(model.id)
        return doc

    def save_medication(self, record: Mapping[str, Any]) -> MedicationDoc:
        """Persist a medication record to the database."""
        values = {k: v for k, v in record.items() if k in MEDICATION_COLUMNS}
        values.setdefault("created_at", datetime.now())
        values.setdefault("updated_at", datetime.now())
        model = MedicationRecord(**values)
        with self._get_session() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            logger.info("Saved medication: %s (id=%s)", model.name, model.id)
            return self._model_to_doc(model)

    def get_all_medications(self) -> List[MedicationDoc]:
        """Retrieve all medication records."""
        with self._get_session() as session:
            models = session.query(MedicationRecord).order_by(MedicationRecord.id).all()
            return [self._model_to_doc(model) for model in models]

    def get_medication(self, medication_id: str) -> Optional[MedicationDoc]:
        """Find a medication record by ID."""
        pk = _coerce_int_id(medication_id)
        if pk is None:
            return None
        with self._get_session() as session:
            model = session.get(MedicationRecord, pk)
            return self._model_to_doc(model) if model else None

    def get_medication_by_name(self, name: str) -> Optional[MedicationDoc]:
        """Find a medication record by name (case-insensitive)."""
        with self._get_session() as session:
            model = (
                session.query(MedicationRecord)
                .filter(MedicationRecord.name.ilike(name))
                .first()
            )
            return self._model_to_doc(model) if model else None

    def update_medication(self, medication_id: str, updates: Mapping[str, Any]) -> bool:
        """Apply field updates to a medication record."""
        pk = _coerce_int_id(medication_id)
        if pk is None:
            return False
        with self._get_session() as session:
            model = session.get(MedicationRecord, pk)
            if model is None:
                return False
            for key, value in updates.items():
                if key in MEDICATION_COLUMNS:
                    setattr(model, key, value)
            setattr(model, "updated_at", datetime.now())
            session.commit()
            return True

    def delete_medication(self, medication_id: str) -> bool:
        """Delete a medication record by ID."""
        pk = _coerce_int_id(medication_id)
        if pk is None:
            return False
        with self._get_session() as session:
            model = session.get(MedicationRecord, pk)
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

    def log_dose(self, log: Mapping[str, Any]) -> DoseLogDoc:
        """Record a dose log entry."""
        values = {k: v for k, v in log.items() if k in DOSE_LOG_COLUMNS}
        if "medication_id" in values:
            values["medication_id"] = _coerce_int_id(values["medication_id"]) or 0
        model = DoseLog(**values)
        with self._get_session() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            logger.info("Logged dose: %s (id=%s)", model.medication_name, model.id)
            return self._log_to_doc(model)

    def get_dose_logs(
        self,
        medication_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DoseLogDoc]:
        """Retrieve dose log entries, optionally filtered by medication."""
        with self._get_session() as session:
            query = session.query(DoseLog)
            if medication_id is not None:
                query = query.filter(
                    DoseLog.medication_id == _coerce_int_id(medication_id)
                )
            models = query.order_by(DoseLog.scheduled_time.desc()).limit(limit).all()
            return [self._log_to_doc(model) for model in models]
