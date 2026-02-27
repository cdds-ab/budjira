# mypy: disable-error-code="arg-type"
"""Tests for project metadata CLI commands."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.models.project_metadata import (
    FieldMetadata,
    IssueTypeMetadata,
    ProjectMetadata,
)
from typer.testing import CliRunner

runner = CliRunner()


def _make_connection(name: str = "test-conn") -> Connection:
    """Create a test connection."""
    return Connection(
        name=name,
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
        cache_ttl_hours=24,
    )


def _make_metadata() -> ProjectMetadata:
    """Create sample project metadata."""
    return ProjectMetadata(
        project_key="TEST",
        project_name="Test Project",
        issue_types=[
            IssueTypeMetadata(
                id="1",
                name="Bug",
                fields=[
                    FieldMetadata(field_id="summary", name="Summary", required=True),
                    FieldMetadata(field_id="priority", name="Priority", required=True),
                ],
            ),
            IssueTypeMetadata(id="2", name="Story"),
            IssueTypeMetadata(id="3", name="Sub-task", subtask=True),
        ],
        priorities=["High", "Medium", "Low"],
        components=["Backend", "Frontend"],
        fetched_at=datetime.now(tz=timezone.utc),
    )


class TestProjectSync:
    """Test project sync command."""

    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_sync_with_fresh_cache(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
    ) -> None:
        """Test sync skips when cache is fresh."""
        mock_get_conn.return_value = _make_connection()
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = True
        mock_get_cache.return_value = mock_cache

        result = runner.invoke(app, ["-q", "project", "sync"])

        assert result.exit_code == 0
        assert "still fresh" in result.stdout

    @patch("budjira.core.jira_client.JiraClient.from_connection")
    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_sync_force(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
        mock_from_connection: MagicMock,
    ) -> None:
        """Test sync with --force refreshes even with fresh cache."""
        conn = _make_connection()
        mock_get_conn.return_value = conn

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = True
        mock_get_cache.return_value = mock_cache

        metadata = _make_metadata()
        mock_client = MagicMock()
        mock_client.metadata.fetch_project_metadata.return_value = metadata
        mock_from_connection.return_value = mock_client

        result = runner.invoke(app, ["-q", "project", "sync", "--force"])

        assert result.exit_code == 0
        assert "Project metadata synced" in result.stdout
        assert "3 issue types" in result.stdout
        assert "3 priorities" in result.stdout
        assert "2 components" in result.stdout
        mock_cache.save.assert_called_once()

    @patch("budjira.core.jira_client.JiraClient.from_connection")
    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_sync_fetches_when_no_cache(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
        mock_from_connection: MagicMock,
    ) -> None:
        """Test sync fetches when no valid cache exists."""
        conn = _make_connection()
        mock_get_conn.return_value = conn

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_get_cache.return_value = mock_cache

        metadata = _make_metadata()
        mock_client = MagicMock()
        mock_client.metadata.fetch_project_metadata.return_value = metadata
        mock_from_connection.return_value = mock_client

        result = runner.invoke(app, ["-q", "project", "sync"])

        assert result.exit_code == 0
        assert "Project metadata synced" in result.stdout

    @patch("budjira.cli.project.get_active_connection")
    def test_sync_no_connection(self, mock_get_conn: MagicMock) -> None:
        """Test sync without active connection."""
        from budjira.utils.errors import BudjiraError

        mock_get_conn.side_effect = BudjiraError("No active connection")

        result = runner.invoke(app, ["-q", "project", "sync"])
        assert result.exit_code == 1
        assert "No active connection" in result.stdout


class TestProjectShow:
    """Test project show command."""

    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_show_with_cached_metadata(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
    ) -> None:
        """Test show displays cached metadata."""
        conn = _make_connection()
        mock_get_conn.return_value = conn

        mock_cache = MagicMock()
        mock_cache.load.return_value = _make_metadata()
        mock_get_cache.return_value = mock_cache

        result = runner.invoke(app, ["-q", "project", "show"])

        assert result.exit_code == 0
        assert "Test Project" in result.stdout
        assert "Bug" in result.stdout
        assert "Story" in result.stdout
        assert "High" in result.stdout
        assert "Backend" in result.stdout

    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_show_no_cache(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
    ) -> None:
        """Test show when no cache exists."""
        mock_get_conn.return_value = _make_connection()

        mock_cache = MagicMock()
        mock_cache.load.return_value = None
        mock_get_cache.return_value = mock_cache

        result = runner.invoke(app, ["-q", "project", "show"])

        assert result.exit_code == 1
        assert "No cached metadata" in result.stdout


class TestProjectClear:
    """Test project clear command."""

    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_clear_existing(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
    ) -> None:
        """Test clearing existing cache."""
        mock_get_conn.return_value = _make_connection()

        mock_cache = MagicMock()
        mock_cache.clear.return_value = True
        mock_get_cache.return_value = mock_cache

        result = runner.invoke(app, ["-q", "project", "clear"])

        assert result.exit_code == 0
        assert "Cleared metadata cache" in result.stdout

    @patch("budjira.cli.project._get_metadata_cache")
    @patch("budjira.cli.project.get_active_connection")
    def test_clear_nonexistent(
        self,
        mock_get_conn: MagicMock,
        mock_get_cache: MagicMock,
    ) -> None:
        """Test clearing when no cache exists."""
        mock_get_conn.return_value = _make_connection()

        mock_cache = MagicMock()
        mock_cache.clear.return_value = False
        mock_get_cache.return_value = mock_cache

        result = runner.invoke(app, ["-q", "project", "clear"])

        assert result.exit_code == 0
        assert "No cached metadata" in result.stdout
