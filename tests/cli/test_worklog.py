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


def _tempo_worklog(
    *,
    worklog_id: int = 10001,
    account_id: str = "557058:real-person",
    display_name: str | None = "Real Person",
    seconds: int = 9000,
    description: str | None = "Fixed bug",
):
    """Build a TempoWorklog for list tests."""
    from datetime import date, datetime

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    return TempoWorklog(
        self=f"https://api.tempo.io/worklogs/{worklog_id}",
        tempoWorklogId=worklog_id,
        issue=TempoIssue(self="https://api.tempo.io/issues/12345", key="TEST-123", id=12345),
        timeSpentSeconds=seconds,
        startDate=date(2025, 10, 24),
        startTime="14:00:00",
        description=description,
        createdAt=datetime(2025, 10, 24, 16, 30),
        updatedAt=datetime(2025, 10, 24, 16, 30),
        author=TempoAuthor(
            self=f"https://api.tempo.io/users/{account_id}",
            accountId=account_id,
            displayName=display_name,
        ),
    )


class TestWorklogListTempoAttribution:
    """Tests for 'budjira worklog list' on Tempo-enabled connections (#92)."""

    @pytest.fixture
    def tempo_connection(self, mock_connection):
        mock_connection.tempo_enabled = True
        return mock_connection

    def _wire_jira(self, mock_jira_class: MagicMock, *, account_id: str = "557058:me") -> MagicMock:
        """Wire JiraClient mock for issue_id resolution and myself()."""
        jira = MagicMock()
        issue = MagicMock()
        issue.id = "12345"
        issue.key = "TEST-123"
        jira.client.issue.return_value = issue
        jira.client.myself.return_value = {"accountId": account_id, "displayName": "Me"}
        mock_jira_class.from_connection.return_value = jira
        return jira

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_tempo_connection_shows_real_author_displayname(
        self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection
    ):
        """On a Tempo connection the real author displayName is shown, not the sync account."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = [_tempo_worklog(display_name="Real Person")]
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        assert "Real Person" in result.stdout
        # Resolved numeric issue id must be passed to the Tempo client
        assert tempo.get_worklogs.call_args.kwargs["issue_id"] == 12345

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_format_json_emits_expected_fields(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """--format json emits structured records with author accountId + displayName."""
        import json

        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = [
            _tempo_worklog(worklog_id=777, account_id="557058:x", display_name="Real Person", seconds=1800)
        ]
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["--format", "json", "worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        record = payload["worklogs"][0]
        assert record["id"] == 777
        assert record["author"]["accountId"] == "557058:x"
        assert record["author"]["displayName"] == "Real Person"
        assert record["timeSpentSeconds"] == 1800
        assert record["startDate"] == "2025-10-24"

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_mine_filters_by_current_user_account_id(
        self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection
    ):
        """--mine resolves the current user and passes their accountId to the client."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class, account_id="557058:me")
        tempo = MagicMock()
        tempo.get_worklogs.return_value = []
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--mine"])

        assert result.exit_code == 0
        assert tempo.get_worklogs.call_args.kwargs["account_id"] == "557058:me"

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_author_filters_by_account_id(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """--author passes the given accountId to the client."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = []
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--author", "557058:colleague"])

        assert result.exit_code == 0
        assert tempo.get_worklogs.call_args.kwargs["account_id"] == "557058:colleague"

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_from_and_to_passed_to_client(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """--from/--to are parsed and passed as date filters to the client."""
        from datetime import date

        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = []
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--from", "2025-10-01", "--to", "2025-10-31"])

        assert result.exit_code == 0
        kwargs = tempo.get_worklogs.call_args.kwargs
        assert kwargs["from_date"] == date(2025, 10, 1)
        assert kwargs["to_date"] == date(2025, 10, 31)

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_mine_and_author_are_mutually_exclusive(
        self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection
    ):
        """--mine and --author together is a usage error."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        mock_get_tempo.return_value = MagicMock()

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--mine", "--author", "557058:x"])

        assert result.exit_code == 1
        assert "mine" in result.stdout.lower() and "author" in result.stdout.lower()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_invalid_from_date_is_usage_error(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """An unparseable --from date is a clean usage error, not a traceback."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        mock_get_tempo.return_value = MagicMock()

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--from", "2025-13-01"])

        assert result.exit_code == 1
        assert "invalid date" in result.stdout.lower()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_truncation_hint_when_limit_reached(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """Exactly limit results means more may exist: table output carries a hint."""
        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = [_tempo_worklog(worklog_id=i) for i in range(1000)]
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        assert "truncated" in result.stdout.lower()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_json_truncated_flag(self, mock_get_conn, mock_jira_class, mock_get_tempo, tempo_connection):
        """JSON output exposes whether the result hit the fetch limit."""
        import json

        mock_get_conn.return_value = tempo_connection
        self._wire_jira(mock_jira_class)
        tempo = MagicMock()
        tempo.get_worklogs.return_value = [_tempo_worklog()]
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["--format", "json", "worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["truncated"] is False


class TestWorklogListNonTempo:
    """Non-Tempo (Jira fallback) behaviour for 'budjira worklog list' (#92)."""

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_non_tempo_json_output(self, mock_get_conn, mock_jira_class, mock_connection):
        """--format json works on the Jira fallback path too."""
        import json

        mock_get_conn.return_value = mock_connection  # tempo_enabled defaults to False
        client = MagicMock()
        client.get_worklogs.return_value = [
            {
                "id": "10001",
                "author": "John Doe",
                "timeSpent": "2h 30m",
                "timeSpentSeconds": 9000,
                "started": "2025-10-24T14:00:00.000+0000",
                "comment": "Fixed bug",
            }
        ]
        mock_jira_class.from_connection.return_value = client

        result = runner.invoke(app, ["--format", "json", "worklog", "list", "TEST-123"])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        record = payload["worklogs"][0]
        assert record["id"] == "10001"
        assert record["author"]["displayName"] == "John Doe"
        # Same schema as the Tempo path: startDate is a date, startTime a separate field.
        assert record["startDate"] == "2025-10-24"
        assert record["startTime"] == "14:00:00"

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_filter_flag_on_non_tempo_warns(self, mock_get_conn, mock_jira_class, mock_connection):
        """Author/date filters require a Tempo connection; using them on Jira warns instead of silently ignoring."""
        mock_get_conn.return_value = mock_connection  # tempo_enabled=False
        client = MagicMock()
        client.get_worklogs.return_value = []
        mock_jira_class.from_connection.return_value = client

        result = runner.invoke(app, ["worklog", "list", "TEST-123", "--mine"])

        assert result.exit_code == 1
        assert "tempo" in result.stdout.lower()


class TestWorklogUpdateCommand:
    """Tests for 'budjira worklog update' command (#116)."""

    def _native_worklog(self, *, account_id: str = "557058:me") -> dict[str, object]:
        """Build a native Jira worklog dict as returned by WorklogService._to_dict."""
        return {
            "id": "10001",
            "author": "Me",
            "authorAccountId": account_id,
            "timeSpent": "4h",
            "timeSpentSeconds": 14400,
            "started": "2025-10-24T09:00:00.000+0000",
            "comment": "Original comment",
        }

    def _wire_native(self, mock_jira_class: MagicMock, *, account_id: str = "557058:me") -> MagicMock:
        """Wire JiraClient mock for the native update path."""
        client = MagicMock()
        client.worklogs.get.return_value = self._native_worklog()
        client.worklogs.update.return_value = self._native_worklog()
        client.client.myself.return_value = {"accountId": account_id, "displayName": "Me"}
        mock_jira_class.from_connection.return_value = client
        return client

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_force(self, mock_get_conn, mock_jira_class, mock_connection):
        """Update a native worklog with --force skips the confirmation prompt."""
        mock_get_conn.return_value = mock_connection  # tempo_enabled=False
        client = self._wire_native(mock_jira_class)

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "10001", "--time-spent", "6h", "--comment", "Fixed", "--force"],
        )

        assert result.exit_code == 0
        assert "Updated worklog 10001 on TEST-123" in result.stdout
        client.worklogs.update.assert_called_once_with(
            "TEST-123",
            "10001",
            time_spent_minutes=360,
            comment="Fixed",
            started=None,
        )

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_preview_confirm(self, mock_get_conn, mock_jira_class, mock_connection):
        """Without --force a preview is shown and confirmed interactively."""
        mock_get_conn.return_value = mock_connection
        client = self._wire_native(mock_jira_class)

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "10001", "--time-spent", "6h"],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "Worklog Update Preview" in result.stdout
        assert "4.00h" in result.stdout  # before
        assert "6.00h" in result.stdout  # after
        client.worklogs.update.assert_called_once()

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_preview_abort(self, mock_get_conn, mock_jira_class, mock_connection):
        """Declining the confirmation leaves the worklog untouched."""
        mock_get_conn.return_value = mock_connection
        client = self._wire_native(mock_jira_class)

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "10001", "--time-spent", "6h"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Update cancelled" in result.stdout
        client.worklogs.update.assert_not_called()

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_started_parsed(self, mock_get_conn, mock_jira_class, mock_connection):
        """--started is parsed into a datetime for the service call."""
        mock_get_conn.return_value = mock_connection
        client = self._wire_native(mock_jira_class)

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "10001", "--started", "2025-10-28 14:30", "--force"],
        )

        assert result.exit_code == 0
        call_kwargs = client.worklogs.update.call_args.kwargs
        assert call_kwargs["started"] == datetime(2025, 10, 28, 14, 30)
        assert call_kwargs["time_spent_minutes"] is None
        assert call_kwargs["comment"] is None

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_no_fields_specified(self, mock_get_conn, mock_jira_class, mock_connection):
        """At least one of --time-spent/--started/--comment is required."""
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(app, ["worklog", "update", "TEST-123", "10001"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stdout
        mock_jira_class.from_connection.assert_not_called()

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_refuses_foreign_worklog(self, mock_get_conn, mock_jira_class, mock_connection):
        """Updating someone else's worklog is refused with a clear message."""
        mock_get_conn.return_value = mock_connection
        client = self._wire_native(mock_jira_class, account_id="557058:me")
        client.worklogs.get.return_value = self._native_worklog(account_id="557058:someone-else")

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "10001", "--time-spent", "6h", "--force"],
        )

        assert result.exit_code == 1
        assert "You may only update your own" in result.stdout
        client.worklogs.update.assert_not_called()

    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_native_worklog_not_found(self, mock_get_conn, mock_jira_class, mock_connection):
        """A missing worklog surfaces the service's InvalidIssueError."""
        mock_get_conn.return_value = mock_connection
        client = self._wire_native(mock_jira_class)
        client.worklogs.get.side_effect = InvalidIssueError(
            "Worklog '99999' not found on issue 'TEST-123'. Use 'budjira worklog list TEST-123' to find worklog IDs."
        )

        result = runner.invoke(app, ["worklog", "update", "TEST-123", "99999", "--time-spent", "1h", "--force"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_tempo_force(self, mock_get_conn, mock_jira_class, mock_get_tempo, mock_connection):
        """On Tempo connections the Tempo API is used and unchanged fields are preserved."""
        mock_connection.tempo_enabled = True
        mock_get_conn.return_value = mock_connection
        jira = MagicMock()
        jira.client.myself.return_value = {"accountId": "557058:me", "displayName": "Me"}
        mock_jira_class.from_connection.return_value = jira
        tempo = MagicMock()
        tempo.get_worklog.return_value = _tempo_worklog(
            worklog_id=642, account_id="557058:me", seconds=14400, description="Original"
        )
        tempo.update_worklog.return_value = _tempo_worklog(
            worklog_id=642, account_id="557058:me", seconds=21600, description="Original"
        )
        mock_get_tempo.return_value = tempo

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "642", "--time-spent", "6h", "--force"],
        )

        assert result.exit_code == 0
        assert "Updated worklog 642 on TEST-123" in result.stdout
        tempo.update_worklog.assert_called_once()
        call_kwargs = tempo.update_worklog.call_args.kwargs
        assert call_kwargs["worklog_id"] == 642
        assert call_kwargs["issue_id"] == 12345
        assert call_kwargs["author_account_id"] == "557058:me"
        assert call_kwargs["time_spent_seconds"] == 21600
        # Unchanged fields preserved from the current worklog
        assert call_kwargs["start_date"] == "2025-10-24"
        assert call_kwargs["start_time"] == "14:00:00"
        assert call_kwargs["description"] == "Original"

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_tempo_refuses_foreign_worklog(
        self, mock_get_conn, mock_jira_class, mock_get_tempo, mock_connection
    ):
        """Tempo path: ownership is checked against the real Tempo author, not the sync account."""
        mock_connection.tempo_enabled = True
        mock_get_conn.return_value = mock_connection
        jira = MagicMock()
        jira.client.myself.return_value = {"accountId": "557058:me", "displayName": "Me"}
        mock_jira_class.from_connection.return_value = jira
        tempo = MagicMock()
        tempo.get_worklog.return_value = _tempo_worklog(
            worklog_id=642, account_id="557058:someone-else", display_name="Someone Else"
        )
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "update", "TEST-123", "642", "--time-spent", "6h", "--force"])

        assert result.exit_code == 1
        assert "Someone Else" in result.stdout
        assert "only update your" in result.stdout
        tempo.update_worklog.assert_not_called()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_tempo_invalid_worklog_id(self, mock_get_conn, mock_jira_class, mock_get_tempo, mock_connection):
        """Non-numeric IDs cannot address a Tempo worklog."""
        mock_connection.tempo_enabled = True
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(app, ["worklog", "update", "TEST-123", "abc", "--time-spent", "6h"])

        assert result.exit_code == 1
        assert "Invalid Tempo worklog ID" in result.stdout
        mock_get_tempo.assert_not_called()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_tempo_issue_key_mismatch(self, mock_get_conn, mock_jira_class, mock_get_tempo, mock_connection):
        """A worklog that belongs to another issue is refused before any update."""
        mock_connection.tempo_enabled = True
        mock_get_conn.return_value = mock_connection
        tempo = MagicMock()
        tempo.get_worklog.return_value = _tempo_worklog(worklog_id=642)  # issue key TEST-123
        mock_get_tempo.return_value = tempo

        result = runner.invoke(app, ["worklog", "update", "OTHER-99", "642", "--time-spent", "6h", "--force"])

        assert result.exit_code == 1
        assert "belongs to TEST-123" in result.stdout
        tempo.update_worklog.assert_not_called()

    @patch("budjira.cli.worklog.get_tempo_client")
    @patch("budjira.cli.worklog.JiraClient")
    @patch("budjira.cli.worklog.get_active_connection")
    def test_update_tempo_preview_abort(self, mock_get_conn, mock_jira_class, mock_get_tempo, mock_connection):
        """Tempo path: declining the confirmation leaves the worklog untouched."""
        mock_connection.tempo_enabled = True
        mock_get_conn.return_value = mock_connection
        jira = MagicMock()
        jira.client.myself.return_value = {"accountId": "557058:me", "displayName": "Me"}
        mock_jira_class.from_connection.return_value = jira
        tempo = MagicMock()
        tempo.get_worklog.return_value = _tempo_worklog(worklog_id=642, account_id="557058:me")
        mock_get_tempo.return_value = tempo

        result = runner.invoke(
            app,
            ["worklog", "update", "TEST-123", "642", "--started", "2025-10-28"],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Update cancelled" in result.stdout
        tempo.update_worklog.assert_not_called()
