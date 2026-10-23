"""
Factory for creating the configured storage backend.
"""

from __future__ import annotations

from typing import Optional

from smartmeds.db.base import DatabaseBackend
from smartmeds.utils.config import BACKEND_MONGODB, BACKEND_SQLITE, Settings


def create_database(settings: Optional[Settings] = None) -> DatabaseBackend:
    """
    Create and connect the database backend selected by the configuration.

    The backend is chosen with the ``SMARTMEDS_DB_BACKEND`` environment
    variable (``sqlite`` or ``mongodb``).

    Args:
        settings: Optional explicit settings. Defaults to the environment.

    Returns:
        A connected database backend.

    Raises:
        ValueError: If the configured backend is unknown.
    """
    settings = settings or Settings.from_env()

    if settings.db_backend == BACKEND_MONGODB:
        from smartmeds.db.mongo_database import MongoDatabase

        backend: DatabaseBackend = MongoDatabase(
            uri=settings.mongodb_uri,
            database=settings.mongodb_database,
        )
    elif settings.db_backend == BACKEND_SQLITE:
        from smartmeds.db.database import Database

        backend = Database(db_path=settings.db_path)
    else:
        raise ValueError(
            f"Unknown database backend: {settings.db_backend!r}. "
            f"Supported backends: {BACKEND_SQLITE}, {BACKEND_MONGODB}."
        )

    backend.connect()
    return backend
