"""Tests for connection models."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl and Path fields during validation

import pytest
from budjira.models.connection import Connection, ConnectionList
from pydantic import ValidationError


class TestConnection:
    """Test Connection model."""

    def test_create_valid_connection(self) -> None:
        """Test creating a valid connection."""
        conn = Connection(
            name="Test Connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        assert conn.name == "Test Connection"
        assert str(conn.url) == "https://test.atlassian.net/"
        assert conn.email == "test@example.com"
        assert conn.project_key == "TEST"
        assert conn.is_active is True
        assert conn.cache_enabled is False
        assert conn.cache_ttl_hours == 24

    def test_project_key_must_be_uppercase(self) -> None:
        """Test that project key must be uppercase."""
        with pytest.raises(ValidationError, match="must be uppercase"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="test",
            )

    def test_project_key_alphanumeric(self) -> None:
        """Test that project key must be alphanumeric."""
        with pytest.raises(ValidationError, match="must contain only alphanumeric"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST-123",
            )

    def test_invalid_email(self) -> None:
        """Test that email must be valid."""
        with pytest.raises(ValidationError):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="not-an-email",
                project_key="TEST",
            )

    def test_get_credential_key(self) -> None:
        """Test credential key generation."""
        conn = Connection(
            name="Test Connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        key = conn.get_credential_key()
        assert key == "budjira_test_connection"


class TestConnectionList:
    """Test ConnectionList model."""

    def test_find_by_name(self) -> None:
        """Test finding connection by name."""
        conn = Connection(
            name="My Connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        conn_list = ConnectionList(connections=[conn])

        found = conn_list.find_by_name("My Connection")
        assert found is not None
        assert found.project_key == "TEST"

        not_found = conn_list.find_by_name("Other")
        assert not_found is None

    def test_add_connection(self) -> None:
        """Test adding a connection."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        conn_list = ConnectionList()
        conn_list.add(conn)

        assert len(conn_list.connections) == 1
        assert conn_list.connections[0].name == "Test"

    def test_add_duplicate_raises_error(self) -> None:
        """Test that adding duplicate connection raises error."""
        conn1 = Connection(
            name="Conn1",
            url="https://test1.atlassian.net",
            email="test1@example.com",
            project_key="TEST1",
        )
        conn2 = Connection(
            name="Conn1",  # Same name!
            url="https://test2.atlassian.net",
            email="test2@example.com",
            project_key="TEST2",
        )

        conn_list = ConnectionList()
        conn_list.add(conn1)

        with pytest.raises(ValueError, match="already exists"):
            conn_list.add(conn2)

    def test_remove_connection(self) -> None:
        """Test removing a connection."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        conn_list = ConnectionList(connections=[conn])
        assert len(conn_list.connections) == 1

        removed = conn_list.remove("Test")
        assert removed is True
        assert len(conn_list.connections) == 0

        # Try to remove again
        removed = conn_list.remove("Test")
        assert removed is False

    def test_update_connection(self) -> None:
        """Test updating a connection."""
        conn = Connection(
            name="Original",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        conn_list = ConnectionList(connections=[conn])

        # Update connection
        updated_conn = Connection(
            name="Original",  # Same name
            url="https://updated.atlassian.net",
            email="updated@example.com",
            project_key="TEST2",
        )

        success = conn_list.update(updated_conn)
        assert success is True
        assert conn_list.connections[0].email == "updated@example.com"
        assert str(conn_list.connections[0].url) == "https://updated.atlassian.net/"

        # Try to update non-existent
        other_conn = Connection(
            name="Other",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        success = conn_list.update(other_conn)
        assert success is False
