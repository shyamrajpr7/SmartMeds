"""
Tests for the helper utilities.
"""

from smartmeds.utils.helpers import redact_uri


class TestRedactUri:
    def test_hides_password(self):
        uri = "mongodb+srv://user:secret@cluster0.example.mongodb.net/db?x=1"

        assert redact_uri(uri) == (
            "mongodb+srv://user:***@cluster0.example.mongodb.net/db?x=1"
        )

    def test_value_is_actually_removed(self):
        uri = "mongodb+srv://user:super-secret@host"

        assert "super-secret" not in redact_uri(uri)

    def test_leaves_credential_free_uris_alone(self):
        assert redact_uri("mongodb://localhost:27017") == "mongodb://localhost:27017"
        assert redact_uri("sqlite:///smartmeds.db") == "sqlite:///smartmeds.db"

    def test_handles_username_without_password(self):
        assert redact_uri("mongodb://user@host/db") == "mongodb://user:***@host/db"
