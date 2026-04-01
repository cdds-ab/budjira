"""Tests for worklog CLI commands."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.utils.errors import (
    InvalidIssueError,
    PermissionError,
)
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_connection():
    """Create a mock connection."""
    return Connection(
        name="test-conn",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@example.com",
        project_key="TEST",
    )


class TestWorklogAddCommand:
    """Tests for 'budjira worklog add' command."""

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_success(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog successfully."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "add", "TEST-123", "2h", "--comment", "Fixed bug"],
        )

        assert result.exit_code == 0
        assert "Logged 2h to TEST-123" in result.stdout
        assert "Comment: Fixed bug" in result.stdout

        mock_client.add_worklog.assert_called_once()
        call_args = mock_client.add_worklog.call_args
        assert call_args.kwargs["issue_key"] == "TEST-123"
        assert call_args.kwargs["time_spent_minutes"] == 120  # 2h = 120m
        assert call_args.kwargs["comment"] == "Fixed bug"
        assert call_args.kwargs["started"] is None

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_without_comment(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog without comment."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["worklog", "add", "TEST-456", "30m"])

        assert result.exit_code == 0
        assert "Logged 30m to TEST-456" in result.stdout
        assert "Comment" not in result.stdout

        mock_client.add_worklog.assert_called_once()
        call_args = mock_client.add_worklog.call_args
        assert call_args.kwargs["time_spent_minutes"] == 30
        assert call_args.kwargs["comment"] is None

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_with_started_datetime(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog with started datetime."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "worklog",
                "add",
                "TEST-789",
                "1h30m",
                "--started",
                "2025-10-24 14:00",
            ],
        )

        assert result.exit_code == 0
        assert "Logged 1h30m to TEST-789" in result.stdout
        assert "Started: 2025-10-24 14:00" in result.stdout

        mock_client.add_worklog.assert_called_once()
        call_args = mock_client.add_worklog.call_args
        assert call_args.kwargs["time_spent_minutes"] == 90
        assert isinstance(call_args.kwargs["started"], datetime)
        assert call_args.kwargs["started"].year == 2025
        assert call_args.kwargs["started"].month == 10
        assert call_args.kwargs["started"].day == 24

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_with_relative_started(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog with relative started time."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "worklog",
                "add",
                "TEST-111",
                "2h",
                "--started",
                "yesterday",
                "--comment",
                "Worked yesterday",
            ],
        )

        assert result.exit_code == 0
        assert "Logged 2h to TEST-111" in result.stdout

        mock_client.add_worklog.assert_called_once()
        call_args = mock_client.add_worklog.call_args
        assert isinstance(call_args.kwargs["started"], datetime)

    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_invalid_time_format(
        self,
        mock_get_conn,
        mock_connection,
    ):
        """Test adding worklog with invalid time format."""
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(
            app,
            ["worklog", "add", "TEST-123", "invalid-time"],
        )

        assert result.exit_code == 1
        assert "Validation Error" in result.stdout

    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_invalid_datetime_format(
        self,
        mock_get_conn,
        mock_connection,
    ):
        """Test adding worklog with invalid datetime format."""
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(
            app,
            ["worklog", "add", "TEST-123", "2h", "--started", "invalid-date"],
        )

        assert result.exit_code == 1
        assert "Validation Error" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_issue_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog to non-existent issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_worklog.side_effect = InvalidIssueError("Issue not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "add", "NOTFOUND-999", "1h"],
        )

        assert result.exit_code == 1
        assert "Invalid Issue" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_permission_denied(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog with permission denied."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_worklog.side_effect = PermissionError("Permission denied")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "add", "TEST-123", "2h"],
        )

        assert result.exit_code == 1
        assert "Permission Denied" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_add_worklog_with_connection_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding worklog with --connection flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "worklog",
                "add",
                "TEST-123",
                "1h",
                "--connection",
                "my-connection",
            ],
        )

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("my-connection")


class TestWorklogDeleteCommand:
    """Tests for 'budjira worklog delete' command."""

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_with_force(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting worklog with --force flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "TEST-123", "10001", "--force"],
        )

        assert result.exit_code == 0
        assert "Deleted worklog 10001 from TEST-123" in result.stdout
        mock_client.delete_worklog.assert_called_once_with("TEST-123", "10001")

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_with_confirmation(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting worklog with confirmation prompt."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.get_worklogs.return_value = [
            {
                "id": "10001",
                "author": "John Doe",
                "timeSpent": "2h",
                "comment": "Test work",
            },
        ]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "TEST-123", "10001"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "Deleted worklog 10001 from TEST-123" in result.stdout
        mock_client.delete_worklog.assert_called_once_with("TEST-123", "10001")

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_cancelled(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test cancelling worklog deletion."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.get_worklogs.return_value = [
            {"id": "10001", "author": "John Doe", "timeSpent": "2h"},
        ]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "TEST-123", "10001"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.stdout
        mock_client.delete_worklog.assert_not_called()

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_issue_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting worklog from non-existent issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.delete_worklog.side_effect = InvalidIssueError("Issue not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "NOTFOUND-999", "10001", "--force"],
        )

        assert result.exit_code == 1
        assert "Invalid Issue" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_permission_denied(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting worklog with permission denied."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.delete_worklog.side_effect = PermissionError("Permission denied")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "TEST-123", "10001", "--force"],
        )

        assert result.exit_code == 1
        assert "Permission Denied" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_delete_worklog_with_connection_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting worklog with --connection flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "delete", "TEST-123", "10001", "--force", "--connection", "my-conn"],
        )

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("my-conn")


class TestWorklogListCommand:
    """Tests for 'budjira worklog list' command."""

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_list_worklogs_success(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing worklogs successfully."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()

        mock_worklogs = [
            {
                "id": "10001",
                "author": "John Doe",
                "timeSpent": "2h 30m",
                "timeSpentSeconds": 9000,
                "started": "2025-10-24T14:00:00.000+0000",
                "created": "2025-10-24T16:30:00.000+0000",
                "comment": "Fixed bug",
            },
            {
                "id": "10002",
                "author": "Jane Smith",
                "timeSpent": "1h",
                "timeSpentSeconds": 3600,
                "started": "2025-10-25T09:00:00.000+0000",
                "created": "2025-10-25T10:00:00.000+0000",
            },
        ]

        mock_client.get_worklogs.return_value = mock_worklogs
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        assert "Work Logs for TEST-123" in result.stdout
        assert "John Doe" in result.stdout
        assert "2h 30m" in result.stdout
        assert "Jane Smith" in result.stdout
        assert "1h" in result.stdout
        assert "Total: 2 work log(s)" in result.stdout

        mock_client.get_worklogs.assert_called_once_with("TEST-123")

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_list_worklogs_empty(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing worklogs for issue with no worklogs."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.get_worklogs.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["worklog", "list", "TEST-456"])

        assert result.exit_code == 0
        assert "No work logs found" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_list_worklogs_issue_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing worklogs for non-existent issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.get_worklogs.side_effect = InvalidIssueError("Issue not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["worklog", "list", "NOTFOUND-999"])

        assert result.exit_code == 1
        assert "Invalid Issue" in result.stdout

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_list_worklogs_with_connection_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing worklogs with --connection flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.get_worklogs.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["worklog", "list", "TEST-123", "--connection", "my-connection"],
        )

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("my-connection")
