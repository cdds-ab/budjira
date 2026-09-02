"""Secure credential storage and retrieval."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from budjira.config.settings import get_settings

if TYPE_CHECKING:
    from pathlib import Path

    from budjira.models.connection import Connection


class CredentialStore:
    """Manages secure storage of API tokens for Jira connections.

    Credentials are stored in individual JSON files with restricted permissions (0o600)
    to prevent unauthorized access. Each connection's credentials are stored separately
    using the connection's credential key.
    """

    def __init__(self) -> None:
        """Initialize credential store with credentials directory."""
        self.credentials_dir = get_settings().credentials_dir
        # Ensure directory exists with restricted permissions
        self.credentials_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _get_credential_file(self, connection: Connection) -> Path:
        """Get credential file path for a connection.

        Args:
            connection: Connection to get credential file for

        Returns:
            Path to credential file
        """
        key = connection.get_credential_key()
        return self.credentials_dir / f"{key}.json"

    def store(self, connection: Connection, api_token: str) -> None:
        """Store API token for a connection.

        Args:
            connection: Connection to store token for
            api_token: Jira API token to store

        Raises:
            ValueError: If API token is empty
        """
        if not api_token or not api_token.strip():
            raise ValueError("API token cannot be empty")

        credential_file = self._get_credential_file(connection)

        # Store as JSON with metadata
        data = {
            "api_token": api_token.strip(),
            "email": connection.email,
            "url": str(connection.url),
        }

        # Write with restricted permissions
        credential_file.write_text(json.dumps(data, indent=2))
        credential_file.chmod(0o600)  # Owner read/write only

    def retrieve(self, connection: Connection) -> str | None:
        """Retrieve API token for a connection.

        Args:
            connection: Connection to retrieve token for

        Returns:
            API token if found, None otherwise
        """
        credential_file = self._get_credential_file(connection)

        if not credential_file.exists():
            return None

        try:
            data = json.loads(credential_file.read_text())
            token = data.get("api_token")
            return str(token) if token is not None else None
        except (json.JSONDecodeError, KeyError):
            # Invalid credential file
            return None

    def delete(self, connection: Connection) -> bool:
        """Delete stored API token for a connection.

        Args:
            connection: Connection to delete token for

        Returns:
            True if credential was deleted, False if not found
        """
        credential_file = self._get_credential_file(connection)

        if credential_file.exists():
            credential_file.unlink()
            return True
        return False

    def has_credentials(self, connection: Connection) -> bool:
        """Check if credentials exist for a connection.

        Args:
            connection: Connection to check

        Returns:
            True if credentials exist, False otherwise
        """
        return self._get_credential_file(connection).exists()

    def store_credential(self, key: str, token: str) -> None:
        """Store a credential by key (for non-connection credentials like Tempo).

        Args:
            key: Unique credential key
            token: Token to store

        Raises:
            ValueError: If token is empty
        """
        if not token or not token.strip():
            raise ValueError("Token cannot be empty")

        credential_file = self.credentials_dir / f"{key}.json"
        data = {"token": token.strip()}
        credential_file.write_text(json.dumps(data, indent=2))
        credential_file.chmod(0o600)

    def get_credential(self, key: str) -> str | None:
        """Retrieve a credential by key.

        Args:
            key: Credential key to retrieve

        Returns:
            Token if found, None otherwise
        """
        credential_file = self.credentials_dir / f"{key}.json"
        if not credential_file.exists():
            return None

        try:
            data = json.loads(credential_file.read_text())
            return data.get("token")  # type: ignore[no-any-return]
        except (json.JSONDecodeError, KeyError):
            return None

    def delete_credential(self, key: str) -> bool:
        """Delete a credential by key (for non-connection credentials like Tempo).

        Args:
            key: Credential key to delete

        Returns:
            True if credential was deleted, False if not found
        """
        credential_file = self.credentials_dir / f"{key}.json"
        if credential_file.exists():
            credential_file.unlink()
            return True
        return False


# Global credential store instance
_credential_store: CredentialStore | None = None


def get_credential_store() -> CredentialStore:
    """Get global credential store instance (singleton).

    Returns:
        CredentialStore instance
    """
    global _credential_store
    if _credential_store is None:
        _credential_store = CredentialStore()
    return _credential_store
