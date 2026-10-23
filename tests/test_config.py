"""
Tests for the configuration and database backend factory.
"""

from pathlib import Path

import pytest

from smartmeds.db.database import Database
from smartmeds.db.factory import create_database
from smartmeds.utils.config import BACKEND_MONGODB, BACKEND_SQLITE, Settings


class TestSettings:
    def test_defaults_to_sqlite(self):
        settings = Settings.from_env({})

        assert settings.db_backend == BACKEND_SQLITE
        assert settings.is_mongodb is False

    def test_reads_mongodb_backend(self):
        settings = Settings.from_env({"SMARTMEDS_DB_BACKEND": "MongoDB"})

        assert settings.db_backend == BACKEND_MONGODB
        assert settings.is_mongodb is True

    def test_reads_mongodb_uri_and_database(self):
        settings = Settings.from_env(
            {
                "SMARTMEDS_MONGODB_URI": "mongodb://example:27017",
                "SMARTMEDS_MONGODB_DB": "meds",
            }
        )

        assert settings.mongodb_uri == "mongodb://example:27017"
        assert settings.mongodb_database == "meds"

    def test_reads_sqlite_path(self, tmp_path):
        target = tmp_path / "custom.db"
        settings = Settings.from_env({"SMARTMEDS_DB_PATH": str(target)})

        assert settings.db_path == Path(target)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError):
            Settings.from_env({"SMARTMEDS_DB_BACKEND": "postgres"})

    def test_mongodb_uri_alone_selects_mongodb(self):
        settings = Settings.from_env({"MONGODB_URI": "mongodb://example:27017"})

        assert settings.db_backend == BACKEND_MONGODB
        assert settings.is_mongodb is True

    def test_explicit_backend_overrides_uri_detection(self):
        settings = Settings.from_env(
            {
                "SMARTMEDS_DB_BACKEND": "sqlite",
                "MONGODB_URI": "mongodb://example:27017",
            }
        )

        assert settings.db_backend == BACKEND_SQLITE

    def test_vercel_uses_writable_sqlite_path(self):
        settings = Settings.from_env({"VERCEL": "1"})

        assert settings.db_path == Path("/tmp/smartmeds.db")

    def test_vercel_path_is_overridable(self, tmp_path):
        target = tmp_path / "custom.db"
        settings = Settings.from_env({"VERCEL": "1", "SMARTMEDS_DB_PATH": str(target)})

        assert settings.db_path == Path(target)


class TestCreateDatabase:
    def test_creates_sqlite_backend(self, tmp_path):
        settings = Settings(db_backend=BACKEND_SQLITE, db_path=tmp_path / "test.db")

        db = create_database(settings)
        try:
            assert isinstance(db, Database)
            assert db.get_all_medications() == []
        finally:
            db.close()

    def test_creates_mongodb_backend(self, monkeypatch):
        mongomock = pytest.importorskip("mongomock")
        import pymongo

        from smartmeds.db.mongo_database import MongoDatabase

        monkeypatch.setattr(pymongo, "MongoClient", mongomock.MongoClient)

        settings = Settings(
            db_backend=BACKEND_MONGODB,
            mongodb_uri="mongodb://example:27017",
            mongodb_database="meds",
        )
        db = create_database(settings)
        try:
            assert isinstance(db, MongoDatabase)
            assert db.database_name == "meds"
            assert db.get_all_medications() == []
        finally:
            db.close()
