"""
Shared FastAPI dependencies.

The database backend is created once per server instance and reused for every
request. That matters on serverless platforms (Vercel), where a cold start
would otherwise open a new MongoDB connection on each invocation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

from smartmeds.db import DatabaseBackend, create_database
from smartmeds.utils.config import Settings

_backend: Optional[DatabaseBackend] = None


def get_db() -> DatabaseBackend:
    """
    Return the shared database backend, connecting on first use.

    Returns:
        The connected backend.

    Raises:
        HTTPException: 503 when the database cannot be reached.
    """
    global _backend

    if _backend is not None:
        return _backend

    try:
        _backend = create_database(Settings.from_env())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return _backend


def reset_db() -> None:
    """Close and forget the cached backend (used by the test suite)."""
    global _backend

    if _backend is not None:
        _backend.close()
    _backend = None
