"""
Application configuration for SmartMeds.

Settings are resolved from environment variables so the exact same code can
run against a local SQLite file or a remote MongoDB server:

    SMARTMEDS_DB_BACKEND   sqlite (default) | mongodb
    SMARTMEDS_DB_PATH      Path to the SQLite file
    SMARTMEDS_MONGODB_URI  MongoDB connection string
    SMARTMEDS_MONGODB_DB   MongoDB database name
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

BACKEND_SQLITE = "sqlite"
BACKEND_MONGODB = "mongodb"
SUPPORTED_BACKENDS = (BACKEND_SQLITE, BACKEND_MONGODB)

DEFAULT_DB_PATH = Path.home() / ".smartmeds" / "smartmeds.db"
DEFAULT_MONGODB_URI = "mongodb://localhost:27017"
DEFAULT_MONGODB_DATABASE = "smartmeds"

# Serverless platforms expose a read-only filesystem apart from /tmp, so the
# SQLite fallback has to live somewhere writable when one is deployed.
VERCEL_DB_PATH = Path("/tmp/smartmeds.db")


def _default_db_path(env: Mapping[str, str]) -> Path:
    """Return the default SQLite location for the current environment."""
    if _first(env, "VERCEL"):
        return VERCEL_DB_PATH
    return DEFAULT_DB_PATH


def _first(env: Mapping[str, str], *names: str) -> Optional[str]:
    """Return the first non-empty environment value among ``names``."""
    for name in names:
        value = env.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _database_from_uri(uri: str) -> Optional[str]:
    """
    Extract the database name from a MongoDB connection string.

    Handles both ``mongodb://host/dbname`` and the Atlas style
    ``mongodb+srv://user:pass@cluster.mongodb.net/dbname``.
    """
    if "://" not in uri:
        return None
    remainder = uri.split("://", 1)[1]
    if "/" not in remainder:
        return None
    path = remainder.split("/", 1)[1]
    name = path.split("?", 1)[0].strip()
    return name or None


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the application."""

    db_backend: str = BACKEND_SQLITE
    db_path: Path = DEFAULT_DB_PATH
    mongodb_uri: str = DEFAULT_MONGODB_URI
    mongodb_database: str = DEFAULT_MONGODB_DATABASE

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        """
        Build settings from environment variables.

        Args:
            env: Environment mapping to read from. Defaults to ``os.environ``.

        Returns:
            A populated Settings instance.

        Raises:
            ValueError: If the requested backend is not supported.
        """
        env = os.environ if env is None else env

        db_path = _first(env, "SMARTMEDS_DB_PATH")
        mongodb_uri = _first(env, "SMARTMEDS_MONGODB_URI", "MONGODB_URI", "MONGO_URI")
        mongodb_database = _first(
            env, "SMARTMEDS_MONGODB_DB", "MONGODB_DATABASE", "MONGO_DATABASE"
        )

        explicit_backend = _first(env, "SMARTMEDS_DB_BACKEND", "SMARTMEDS_DB")
        if explicit_backend:
            backend = explicit_backend.lower()
        elif mongodb_uri:
            # A connection string was supplied without an explicit backend:
            # assume MongoDB rather than silently using local SQLite.
            backend = BACKEND_MONGODB
        else:
            backend = BACKEND_SQLITE

        if backend not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unknown database backend: {backend!r}. "
                f"Supported backends: {', '.join(SUPPORTED_BACKENDS)}."
            )

        if not mongodb_database and mongodb_uri:
            mongodb_database = _database_from_uri(mongodb_uri)

        return cls(
            db_backend=backend,
            db_path=(Path(db_path).expanduser() if db_path else _default_db_path(env)),
            mongodb_uri=mongodb_uri or DEFAULT_MONGODB_URI,
            mongodb_database=mongodb_database or DEFAULT_MONGODB_DATABASE,
        )

    @property
    def is_mongodb(self) -> bool:
        """True when the MongoDB backend is selected."""
        return self.db_backend == BACKEND_MONGODB
