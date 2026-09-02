"""Tests for credential storage."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl and Path fields during validation

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from budjira.config.credentials import CredentialStore
from budjira.models.connection import Connection


@pytest.fixture
def mock_settings(tmp_path: Path) -> MagicMock:
    """Create mock settings with temp credentials directory."""
    settings = MagicMock()
    settings.credentials_dir = tmp_path / "credentials"
    settings.credentials_dir.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture
def credential_store(mock_settings: MagicMock) -> CredentialStore:
    """Create credential store with mocked settings."""
    with patch("budjira.config.credentials.get_settings", return_value=mock_settings):
        return CredentialStore()


@pytest.fixture
def test_connection() -> Connection:
    """Create a test connection."""
    return Connection(
        name="Test Connection",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
    )


class TestCredentialStore:
    """Test CredentialStore."""

    def test_store_credentials(self, credential_store: CredentialStore, test_connection: Connection) -> None:
        """Test storing API token."""
        api_token = "test-api-token-12345"

        credential_store.store(test_connection, api_token)

        # Verify file was created
        cred_file = credential_store._get_credential_file(test_connection)
        assert cred_file.exists()

        # Verify file permissions (owner read/write only)
        assert oct(cred_file.stat().st_mode)[-3:] == "600"

        # Verify content
        data = json.loads(cred_file.read_text())
        assert data["api_token"] == api_token
        assert data["email"] == test_connection.email
        assert data["url"] == str(test_connection.url)

    def test_store_empty_token_raises_error(
        self, credential_store: CredentialStore, test_connection: Connection
    ) -> None:
        """Test that storing empty token raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            credential_store.store(test_connection, "")

        with pytest.raises(ValueError, match="cannot be empty"):
            credential_store.store(test_connection, "   ")

    def test_retrieve_credentials(self, credential_store: CredentialStore, test_connection: Connection) -> None:
        """Test retrieving stored API token."""
        api_token = "test-api-token-12345"

        credential_store.store(test_connection, api_token)
        retrieved = credential_store.retrieve(test_connection)

        assert retrieved == api_token

    def test_retrieve_nonexistent_returns_none(
        self, credential_store: CredentialStore, test_connection: Connection
    ) -> None:
        """Test retrieving non-existent credentials returns None."""
        retrieved = credential_store.retrieve(test_connection)
        assert retrieved is None

    def test_retrieve_invalid_json_returns_none(
        self, credential_store: CredentialStore, test_connection: Connection
    ) -> None:
        """Test that invalid JSON file returns None."""
        cred_file = credential_store._get_credential_file(test_connection)
        cred_file.write_text("invalid json{]")

        retrieved = credential_store.retrieve(test_connection)
        assert retrieved is None

    def test_delete_credentials(self, credential_store: CredentialStore, test_connection: Connection) -> None:
        """Test deleting stored credentials."""
        api_token = "test-api-token-12345"

        credential_store.store(test_connection, api_token)
        assert credential_store.has_credentials(test_connection)

        deleted = credential_store.delete(test_connection)
        assert deleted is True
        assert not credential_store.has_credentials(test_connection)

        # Try to delete again
        deleted = credential_store.delete(test_connection)
        assert deleted is False

    def test_has_credentials(self, credential_store: CredentialStore, test_connection: Connection) -> None:
        """Test checking if credentials exist."""
        assert not credential_store.has_credentials(test_connection)

        credential_store.store(test_connection, "test-token")
        assert credential_store.has_credentials(test_connection)

    def test_delete_credential_by_key(self, credential_store: CredentialStore) -> None:
        """Test deleting a key-based credential (e.g. Tempo token)."""
        credential_store.store_credential("budjira_tempo_test", "tempo-token")
        assert credential_store.get_credential("budjira_tempo_test") == "tempo-token"

        deleted = credential_store.delete_credential("budjira_tempo_test")
        assert deleted is True
        assert credential_store.get_credential("budjira_tempo_test") is None

        deleted = credential_store.delete_credential("budjira_tempo_test")
        assert deleted is False

    def test_credential_file_unique_per_connection(self, credential_store: CredentialStore) -> None:
        """Test that each connection gets unique credential file."""
        conn1 = Connection(
            name="Conn1",
            url="https://test1.atlassian.net",
            email="test1@example.com",
            project_key="TEST1",
        )
        conn2 = Connection(
            name="Conn2",
            url="https://test2.atlassian.net",
            email="test2@example.com",
            project_key="TEST2",
        )

        file1 = credential_store._get_credential_file(conn1)
        file2 = credential_store._get_credential_file(conn2)

        assert file1 != file2

        # Store different tokens
        credential_store.store(conn1, "token1")
        credential_store.store(conn2, "token2")

        assert credential_store.retrieve(conn1) == "token1"
        assert credential_store.retrieve(conn2) == "token2"
