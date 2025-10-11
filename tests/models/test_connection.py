"""Tests for connection models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from budjira.models.connection import Connection, ConnectionList


class TestConnection:
    """Test Connection model."""

    def test_create_valid_connection(self, tmp_path: Path) -> None:
        """Test creating a valid connection."""
        conn = Connection(
            name="Test Connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=tmp_path,
        )

        assert conn.name == "Test Connection"
        assert str(conn.url) == "https://test.atlassian.net/"
        assert conn.email == "test@example.com"
        assert conn.project_key == "TEST"
        assert conn.project_root == tmp_path
        assert conn.is_active is True
        assert conn.cache_enabled is False
        assert conn.cache_ttl_hours == 24

    def test_project_root_must_exist(self) -> None:
        """Test that project root must exist."""
        with pytest.raises(ValidationError, match="Project root does not exist"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
                project_root="/nonexistent/path",
            )

    def test_project_root_must_be_directory(self, tmp_path: Path) -> None:
        """Test that project root must be a directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(ValidationError, match="must be a directory"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
                project_root=file_path,
            )

    def test_project_key_must_be_uppercase(self, tmp_path: Path) -> None:
        """Test that project key must be uppercase."""
        with pytest.raises(ValidationError, match="must be uppercase"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="test",
                project_root=tmp_path,
            )

    def test_project_key_alphanumeric(self, tmp_path: Path) -> None:
        """Test that project key must be alphanumeric."""
        with pytest.raises(ValidationError, match="must contain only alphanumeric"):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST-123",
                project_root=tmp_path,
            )

    def test_invalid_email(self, tmp_path: Path) -> None:
        """Test that email must be valid."""
        with pytest.raises(ValidationError):
            Connection(
                name="Test",
                url="https://test.atlassian.net",
                email="not-an-email",
                project_key="TEST",
                project_root=tmp_path,
            )

    def test_get_credential_key(self, tmp_path: Path) -> None:
        """Test credential key generation."""
        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=tmp_path,
        )

        key = conn.get_credential_key()
        assert key.startswith("budjira_")
        assert "_" in key  # Should contain path separators converted to underscores


class TestConnectionList:
    """Test ConnectionList model."""

    def test_find_by_root(self, tmp_path: Path) -> None:
        """Test finding connection by project root."""
        root1 = tmp_path / "project1"
        root1.mkdir()
        root2 = tmp_path / "project2"
        root2.mkdir()

        conn1 = Connection(
            name="Conn1",
            url="https://test1.atlassian.net",
            email="test1@example.com",
            project_key="TEST1",
            project_root=root1,
        )
        conn2 = Connection(
            name="Conn2",
            url="https://test2.atlassian.net",
            email="test2@example.com",
            project_key="TEST2",
            project_root=root2,
        )

        conn_list = ConnectionList(connections=[conn1, conn2])

        found = conn_list.find_by_root(root1)
        assert found is not None
        assert found.name == "Conn1"

        not_found = conn_list.find_by_root(tmp_path / "nonexistent")
        assert not_found is None

    def test_find_by_name(self, tmp_path: Path) -> None:
        """Test finding connection by name."""
        root = tmp_path / "project"
        root.mkdir()

        conn = Connection(
            name="My Connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=root,
        )

        conn_list = ConnectionList(connections=[conn])

        found = conn_list.find_by_name("My Connection")
        assert found is not None
        assert found.project_key == "TEST"

        not_found = conn_list.find_by_name("Other")
        assert not_found is None

    def test_add_connection(self, tmp_path: Path) -> None:
        """Test adding a connection."""
        root = tmp_path / "project"
        root.mkdir()

        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=root,
        )

        conn_list = ConnectionList()
        conn_list.add(conn)

        assert len(conn_list.connections) == 1
        assert conn_list.connections[0].name == "Test"

    def test_add_duplicate_raises_error(self, tmp_path: Path) -> None:
        """Test that adding duplicate connection raises error."""
        root = tmp_path / "project"
        root.mkdir()

        conn1 = Connection(
            name="Conn1",
            url="https://test1.atlassian.net",
            email="test1@example.com",
            project_key="TEST1",
            project_root=root,
        )
        conn2 = Connection(
            name="Conn2",
            url="https://test2.atlassian.net",
            email="test2@example.com",
            project_key="TEST2",
            project_root=root,  # Same root!
        )

        conn_list = ConnectionList()
        conn_list.add(conn1)

        with pytest.raises(ValueError, match="already exists"):
            conn_list.add(conn2)

    def test_remove_connection(self, tmp_path: Path) -> None:
        """Test removing a connection."""
        root = tmp_path / "project"
        root.mkdir()

        conn = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=root,
        )

        conn_list = ConnectionList(connections=[conn])
        assert len(conn_list.connections) == 1

        removed = conn_list.remove(root)
        assert removed is True
        assert len(conn_list.connections) == 0

        # Try to remove again
        removed = conn_list.remove(root)
        assert removed is False

    def test_update_connection(self, tmp_path: Path) -> None:
        """Test updating a connection."""
        root = tmp_path / "project"
        root.mkdir()

        conn = Connection(
            name="Original",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=root,
        )

        conn_list = ConnectionList(connections=[conn])

        # Update connection
        updated_conn = Connection(
            name="Updated",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=root,
        )

        success = conn_list.update(updated_conn)
        assert success is True
        assert conn_list.connections[0].name == "Updated"

        # Try to update non-existent
        other_root = tmp_path / "other"
        other_root.mkdir()
        other_conn = Connection(
            name="Other",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            project_root=other_root,
        )

        success = conn_list.update(other_conn)
        assert success is False
