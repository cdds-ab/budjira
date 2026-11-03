# mypy: disable-error-code="arg-type"
"""Tests for project metadata CLI commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.models.project import ProjectSummary, ReferenceProject
from budjira.models.project_metadata import (
    FieldMetadata,
    IssueTypeMetadata,
    ProjectMetadata,
)
from budjira.utils.errors import AuthenticationError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
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


# ---------------------------------------------------------------------------
# project list / project create --like (#151)
# ---------------------------------------------------------------------------


def _reference_project() -> ReferenceProject:
    return ReferenceProject(
        key="CDDSINT",
        id="10000",
        project_type_key="software",
        issue_type_scheme="10603",
        issue_type_screen_scheme="10236",
        workflow_scheme=10237,
    )


def _admin_client() -> MagicMock:
    """Client mock whose project service answers like a healthy instance."""
    client = MagicMock()
    client.projects.project_exists.return_value = False
    client.projects.get_reference.return_value = _reference_project()
    client.projects.current_account_id.return_value = "acc-1"
    client.projects.create_project.return_value = {"id": "10400", "key": "APX"}
    client.projects.create_filter.return_value = 10500
    client.projects.create_board.return_value = 300
    return client


CREATE = ["project", "create", "APX", "--name", "Apodeixis", "--like", "CDDSINT"]


@patch("budjira.core.jira_client.JiraClient.from_connection")
@patch("budjira.cli.project.get_active_connection")
class TestProjectList:
    """Test project list command."""

    def test_table(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = MagicMock()
        client.projects.list_projects.return_value = [
            ProjectSummary(key="CDDSINT", name="CDDS intern", id="10000", style="classic", lead="Fred Thiele"),
            ProjectSummary(key="PEX", name="Pallet", id="10100", style="next-gen", lead=None),
        ]
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", "project", "list"])

        assert result.exit_code == 0, result.stdout
        assert "CDDSINT" in result.stdout
        assert "company-managed" in result.stdout
        assert "team-managed" in result.stdout
        assert "Fred Thiele" in result.stdout
        assert "2 projects" in result.stdout

    def test_json(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = MagicMock()
        client.projects.list_projects.return_value = [
            ProjectSummary(key="PEX", name="Pallet", id="10100", style="next-gen", lead=None),
        ]
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", "--format", "json", "project", "list"])

        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data == {
            "total": 1,
            "projects": [
                {
                    "key": "PEX",
                    "name": "Pallet",
                    "id": "10100",
                    "style": "next-gen",
                    "management": "team-managed",
                    "lead": None,
                }
            ],
        }

    def test_error_exits_nonzero(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = MagicMock()
        client.projects.list_projects.side_effect = AuthenticationError("Jira rejected the credentials (HTTP 401)")
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", "project", "list"])

        assert result.exit_code == 1
        assert "HTTP 401" in result.stdout


@patch("budjira.core.jira_client.JiraClient.from_connection")
@patch("budjira.cli.project.get_active_connection")
class TestProjectCreate:
    """Test project create --like command."""

    def test_creates_project_filter_and_board(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE])

        assert result.exit_code == 0, result.stdout
        client.projects.get_reference.assert_called_once_with("CDDSINT")
        payload = client.projects.create_project.call_args.args[0]
        assert payload["key"] == "APX"
        assert payload["name"] == "Apodeixis"
        assert payload["leadAccountId"] == "acc-1"
        assert payload["issueTypeScheme"] == 10603
        assert payload["workflowScheme"] == 10237
        filter_payload = client.projects.create_filter.call_args.args[0]
        assert filter_payload["sharePermissions"] == [{"type": "project", "project": {"id": "10400"}}]
        board_payload = client.projects.create_board.call_args.args[0]
        assert board_payload["filterId"] == 10500
        assert board_payload["type"] == "kanban"
        assert "APX" in result.stdout
        assert "300" in result.stdout

    def test_lowercase_key_is_normalized(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", "project", "create", "apx", "--name", "A", "--like", "cddsint"])

        assert result.exit_code == 0, result.stdout
        client.projects.get_reference.assert_called_once_with("CDDSINT")
        assert client.projects.create_project.call_args.args[0]["key"] == "APX"

    def test_invalid_key_makes_no_api_call(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()

        result = runner.invoke(app, ["-q", "project", "create", "1AB", "--name", "A", "--like", "CDDSINT"])

        assert result.exit_code == 1
        assert "Invalid project key" in result.stdout
        mock_from_connection.assert_not_called()

    def test_existing_key_stops_before_any_write(
        self, mock_get_conn: MagicMock, mock_from_connection: MagicMock
    ) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        client.projects.project_exists.return_value = True
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE])

        assert result.exit_code == 1
        assert "already exists" in result.stdout
        client.projects.create_project.assert_not_called()

    def test_dry_run_reads_but_never_writes(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE, "--dry-run"])

        assert result.exit_code == 0, result.stdout
        client.projects.create_project.assert_not_called()
        client.projects.create_filter.assert_not_called()
        client.projects.create_board.assert_not_called()
        assert "Dry run" in result.stdout
        assert '"issueTypeScheme": 10603' in result.stdout
        assert "project = APX ORDER BY Rank ASC" in result.stdout

    def test_dry_run_json(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", "--format", "json", *CREATE, "--dry-run"])

        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        assert data["project"]["issueTypeScreenScheme"] == 10236
        assert data["filter"]["jql"] == "project = APX ORDER BY Rank ASC"
        assert data["board"]["type"] == "kanban"
        client.projects.create_project.assert_not_called()

    def test_board_none_skips_filter_and_board(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE, "--board", "none"])

        assert result.exit_code == 0, result.stdout
        client.projects.create_project.assert_called_once()
        client.projects.create_filter.assert_not_called()
        client.projects.create_board.assert_not_called()

    def test_board_failure_reports_the_created_project(
        self, mock_get_conn: MagicMock, mock_from_connection: MagicMock
    ) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        client.projects.create_board.side_effect = JiraAPIError("Create board failed: nope")
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE])

        assert result.exit_code == 1
        assert "Project APX was created" in result.stdout
        assert "nope" in result.stdout

    def test_create_error_is_shown(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        client = _admin_client()
        client.projects.create_project.side_effect = BudjiraPermissionError("needs the 'Administer Jira' permission")
        mock_from_connection.return_value = client

        result = runner.invoke(app, ["-q", *CREATE])

        assert result.exit_code == 1
        assert "Administer Jira" in result.stdout
        client.projects.create_filter.assert_not_called()

    def test_json_result(self, mock_get_conn: MagicMock, mock_from_connection: MagicMock) -> None:
        mock_get_conn.return_value = _make_connection()
        mock_from_connection.return_value = _admin_client()

        result = runner.invoke(app, ["-q", "--format", "json", *CREATE])

        assert result.exit_code == 0, result.stdout
        data = json.loads(result.stdout)
        assert data["project"] == {"id": "10400", "key": "APX"}
        assert data["like"] == "CDDSINT"
        assert data["filter_id"] == 10500
        assert data["board_id"] == 300
