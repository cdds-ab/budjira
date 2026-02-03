"""Tests for connection models."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl and Path fields during validation

import pytest
from budjira.models.connection import Connection, ConnectionList
from budjira.models.custom_field import CustomFieldConfig, CustomFieldType
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

    def test_tempo_enabled_default_false(self) -> None:
        """Test that tempo_enabled defaults to False."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        assert conn.tempo_enabled is False

    def test_tempo_enabled_can_be_set(self) -> None:
        """Test that tempo_enabled can be set to True."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            tempo_enabled=True,
        )

        assert conn.tempo_enabled is True

    def test_get_tempo_credential_key(self) -> None:
        """Test Tempo credential key generation."""
        conn = Connection(
            name="My Jira",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        key = conn.get_tempo_credential_key()
        assert key == "budjira_tempo_my_jira"

    def test_custom_fields_default_empty(self) -> None:
        """Test that custom_fields defaults to empty dict."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        assert conn.custom_fields == {}

    def test_custom_fields_can_be_set(self) -> None:
        """Test that custom_fields can be set with CustomFieldConfig objects."""
        custom_fields = {
            "affected_system": CustomFieldConfig(
                field_id="customfield_10001",
                type=CustomFieldType.SELECT,
                required=True,
                options=["Infrastructure", "Application"],
            ),
            "environment": CustomFieldConfig(
                field_id="customfield_10002",
                type=CustomFieldType.TEXT,
            ),
        }

        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            custom_fields=custom_fields,
        )

        assert len(conn.custom_fields) == 2
        assert "affected_system" in conn.custom_fields
        assert conn.custom_fields["affected_system"].field_id == "customfield_10001"
        assert conn.custom_fields["affected_system"].type == CustomFieldType.SELECT
        assert conn.custom_fields["affected_system"].required is True

    def test_ai_prompt_default_none(self) -> None:
        """Test that ai_prompt defaults to None."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        assert conn.ai_prompt is None

    def test_ai_prompt_can_be_set(self) -> None:
        """Test that ai_prompt can be set."""
        ai_prompt = """## Project Workflow

This project uses specific issue types:
- Change: For production changes
- Service Request: For service requests

Always include the affected system field.
"""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=ai_prompt,
        )

        assert conn.ai_prompt == ai_prompt
        assert "Change" in conn.ai_prompt
        assert "Service Request" in conn.ai_prompt

    def test_ai_prompt_multiline(self) -> None:
        """Test that ai_prompt handles multiline strings."""
        ai_prompt = "Line 1\nLine 2\nLine 3"
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=ai_prompt,
        )

        assert conn.ai_prompt == ai_prompt
        assert conn.ai_prompt.count("\n") == 2


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
