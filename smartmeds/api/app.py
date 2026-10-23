"""
FastAPI application exposing the SmartMeds API.

The application is storage-agnostic: it uses whichever backend is configured
(SQLite locally, MongoDB Atlas when deployed to Vercel).

Example:
    >>> uvicorn smartmeds.api.app:app --reload
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from smartmeds import __version__
from smartmeds.api.dependencies import get_db
from smartmeds.api.schemas import (
    DoseEventOut,
    DoseLogIn,
    DoseLogOut,
    HealthOut,
    InteractionOut,
    InteractionRequest,
    MedicationIn,
    MedicationOut,
    MedicationPatch,
    dose_log_out,
    medication_from_payload,
    medication_out,
    patch_to_updates,
)
from smartmeds.core.interactions import InteractionChecker
from smartmeds.core.scheduler import MedicationScheduler
from smartmeds.db import DatabaseBackend, doc_to_medication, medication_to_doc
from smartmeds.utils.config import Settings

checker = InteractionChecker()

router = APIRouter()


@router.get("/health", response_model=HealthOut, tags=["system"])
def health(db: DatabaseBackend = Depends(get_db)) -> HealthOut:
    """Report that the service and its database are reachable."""
    settings = Settings.from_env()
    database = (
        settings.mongodb_database if settings.is_mongodb else str(settings.db_path)
    )
    return HealthOut(
        status="ok",
        version=__version__,
        backend=db.backend_name,
        database=database,
    )


@router.get(
    "/medications",
    response_model=List[MedicationOut],
    tags=["medications"],
)
def list_medications(db: DatabaseBackend = Depends(get_db)) -> List[MedicationOut]:
    """Return every stored medication."""
    return [medication_out(doc) for doc in db.get_all_medications()]


@router.post(
    "/medications",
    response_model=MedicationOut,
    status_code=status.HTTP_201_CREATED,
    tags=["medications"],
)
def create_medication(
    payload: MedicationIn,
    db: DatabaseBackend = Depends(get_db),
) -> MedicationOut:
    """Create a new medication."""
    medication = medication_from_payload(payload)
    doc = db.save_medication(medication_to_doc(medication))
    return medication_out(doc)


@router.get(
    "/medications/{medication_id}",
    response_model=MedicationOut,
    tags=["medications"],
)
def get_medication(
    medication_id: str,
    db: DatabaseBackend = Depends(get_db),
) -> MedicationOut:
    """Return a single medication by ID."""
    doc = db.get_medication(medication_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication not found: {medication_id}",
        )
    return medication_out(doc)


@router.patch(
    "/medications/{medication_id}",
    response_model=MedicationOut,
    tags=["medications"],
)
def update_medication(
    medication_id: str,
    payload: MedicationPatch,
    db: DatabaseBackend = Depends(get_db),
) -> MedicationOut:
    """Update part of a medication."""
    doc = db.get_medication(medication_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication not found: {medication_id}",
        )

    updates = patch_to_updates(payload)
    if updates:
        db.update_medication(medication_id, updates)

    updated = db.get_medication(medication_id) or doc
    return medication_out(updated)


@router.delete(
    "/medications/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["medications"],
)
def delete_medication(
    medication_id: str,
    db: DatabaseBackend = Depends(get_db),
) -> Response:
    """Delete a medication."""
    if not db.delete_medication(medication_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication not found: {medication_id}",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/schedule", response_model=List[DoseEventOut], tags=["schedule"])
def get_schedule(
    hours: int = Query(default=24, ge=1, le=720),
    db: DatabaseBackend = Depends(get_db),
) -> List[DoseEventOut]:
    """Return the upcoming doses for the next N hours."""
    scheduler = MedicationScheduler()
    for doc in db.get_all_medications():
        scheduler.add_medication(doc_to_medication(doc))

    return [
        DoseEventOut(
            medication=event.medication.name,
            dosage=str(event.medication.dosage),
            scheduled_time=event.scheduled_time,
            taken=event.taken,
            overdue=event.is_overdue(),
        )
        for event in scheduler.get_upcoming_doses(hours=hours)
    ]


@router.post(
    "/dose-logs",
    response_model=DoseLogOut,
    status_code=status.HTTP_201_CREATED,
    tags=["dose-logs"],
)
def create_dose_log(
    payload: DoseLogIn,
    db: DatabaseBackend = Depends(get_db),
) -> DoseLogOut:
    """Record that a dose was taken (or skipped)."""
    medication = db.get_medication(payload.medication_id)
    name = medication.get("name", "") if medication else payload.medication_id

    doc = db.log_dose(
        {
            "medication_id": payload.medication_id,
            "medication_name": name,
            "scheduled_time": payload.scheduled_time,
            "taken_at": payload.taken_at,
            "taken": payload.taken,
            "skipped": payload.skipped,
            "notes": payload.notes,
        }
    )
    return dose_log_out(doc)


@router.get("/dose-logs", response_model=List[DoseLogOut], tags=["dose-logs"])
def list_dose_logs(
    medication_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: DatabaseBackend = Depends(get_db),
) -> List[DoseLogOut]:
    """Return dose log entries, newest first."""
    logs = db.get_dose_logs(medication_id=medication_id, limit=limit)
    return [dose_log_out(doc) for doc in logs]


@router.post(
    "/interactions/check",
    response_model=List[InteractionOut],
    tags=["interactions"],
)
def check_interactions(payload: InteractionRequest) -> List[InteractionOut]:
    """Check a list of medications for known interactions."""
    return [
        InteractionOut(
            drug_a=interaction.drug_a,
            drug_b=interaction.drug_b,
            severity=interaction.severity,
            description=interaction.description,
            recommendation=interaction.recommendation,
        )
        for interaction in checker.check(payload.medications)
    ]


def create_app() -> FastAPI:
    """
    Build the FastAPI application.

    Returns:
        The configured application instance.
    """
    app = FastAPI(
        title="SmartMeds API",
        description="An intelligent medication management system.",
        version=__version__,
    )

    # The router is mounted twice on purpose: serverless platforms either
    # preserve or strip the incoming path prefix, and both must work.
    app.include_router(router)
    app.include_router(router, prefix="/api")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["system"])
    def root() -> Dict[str, Any]:
        """Describe the available endpoints."""
        return {
            "name": "SmartMeds API",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
            "endpoints": [
                "GET/POST /api/medications",
                "GET/PATCH/DELETE /api/medications/{id}",
                "GET /api/schedule",
                "GET/POST /api/dose-logs",
                "POST /api/interactions/check",
            ],
        }

    return app


app = create_app()
