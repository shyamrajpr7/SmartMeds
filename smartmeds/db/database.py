"""
SQLite database handler for SmartMeds.

Provides persistence for medications, dose logs, and user preferences
using SQLAlchemy with a local SQLite database.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from smartmeds.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DB_PATH = Path.home() / ".smartmeds" / "smartmeds.db"


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


class Database:
    """
    Database manager for SmartMeds.

    Handles all persistence operations using SQLAlchemy ORM.

    Example:
        >>> db = Database()
        >>> db.connect()
        >>> records = db.get_all_medications()
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or DEFAULT_DB_PATH
        self._engine = None
        self._SessionFactory = None

    def connect(self) -> None:
        """Initialize the database connection and create tables."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{self._db_path}"
        self._engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self._engine)
        self._SessionFactory = sessionmaker(bind=self._engine)
        logger.info("Database connected: %s", self._db_path)

    def _get_session(self) -> Session:
        if self._SessionFactory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._SessionFactory()

    def save_medication(self, record: MedicationRecord) -> MedicationRecord:
        """Persist a medication record to the database."""
        with self._get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info("Saved medication: %s (id=%s)", record.name, record.id)
            return record

    def get_all_medications(self) -> List[MedicationRecord]:
        """Retrieve all medication records."""
        with self._get_session() as session:
            return session.query(MedicationRecord).all()

    def get_medication_by_name(self, name: str) -> Optional[MedicationRecord]:
        """Find a medication record by name."""
        with self._get_session() as session:
            return (
                session.query(MedicationRecord)
                .filter(MedicationRecord.name.ilike(name))
                .first()
            )

    def delete_medication(self, medication_id: int) -> bool:
        """Delete a medication record by ID."""
        with self._get_session() as session:
            record = session.get(MedicationRecord, medication_id)
            if record:
                session.delete(record)
                session.commit()
                return True
            return False

    def log_dose(self, log: DoseLog) -> DoseLog:
        """Record a dose log entry."""
        with self._get_session() as session:
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def get_dose_logs(
        self,
        medication_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[DoseLog]:
        """Retrieve dose log entries, optionally filtered by medication."""
        with self._get_session() as session:
            query = session.query(DoseLog)
            if medication_id is not None:
                query = query.filter(DoseLog.medication_id == medication_id)
            return query.order_by(DoseLog.scheduled_time.desc()).limit(limit).all()
