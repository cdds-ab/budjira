"""Test issue CLI commands."""

from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_issue_help() -> None:
    """Test issue subcommand help."""
    result = runner.invoke(app, ["issue", "--help"])
    assert result.exit_code == 0
    assert "issue" in result.stdout.lower()
    assert "update" in result.stdout.lower()
    assert "transitions" in result.stdout.lower()


def test_issue_update_help() -> None:
    """Test issue update command help."""
    result = runner.invoke(app, ["issue", "update", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout.lower()
    assert "assignee" in result.stdout.lower()
    assert "priority" in result.stdout.lower()
    assert "label" in result.stdout.lower()
    assert "epic" in result.stdout.lower()


def test_issue_update_requires_argument() -> None:
    """Test that issue update requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "update"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


def test_issue_update_requires_options() -> None:
    """Test that issue update requires at least one update option."""
    result = runner.invoke(app, ["-q", "issue", "update", "PROJ-123"])
    assert result.exit_code != 0
    # Should warn about no updates specified
    assert "no updates" in result.stdout.lower() or "Error" in result.stdout


def test_issue_transitions_help() -> None:
    """Test issue transitions command help."""
    result = runner.invoke(app, ["issue", "transitions", "--help"])
    assert result.exit_code == 0
    assert "transitions" in result.stdout.lower()
    assert "workflow" in result.stdout.lower()


def test_issue_transitions_requires_argument() -> None:
    """Test that issue transitions requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "transitions"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


class TestIssueUpdateTimeTracking:
    """Tests for issue update time tracking functionality."""

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_original_estimate(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with original estimate."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--original-estimate", "4h"],
        )

        assert result.exit_code == 0
        mock_client.update_issue.assert_called()
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert "fields" in call_kwargs
        assert "timetracking" in call_kwargs["fields"]
        assert call_kwargs["fields"]["timetracking"]["originalEstimate"] == "4h"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_remaining_estimate(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with remaining estimate."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--remaining-estimate", "2h30m"],
        )

        assert result.exit_code == 0
        mock_client.update_issue.assert_called()
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert call_kwargs["fields"]["timetracking"]["remainingEstimate"] == "2h30m"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_both_estimates(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with both estimates."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "-q",
                "issue",
                "update",
                "TEST-123",
                "--original-estimate",
                "8h",
                "--remaining-estimate",
                "5h",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert call_kwargs["fields"]["timetracking"]["originalEstimate"] == "8h"
        assert call_kwargs["fields"]["timetracking"]["remainingEstimate"] == "5h"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_log_work(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with log work."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--log-work", "3h"],
        )

        assert result.exit_code == 0
        mock_client.add_worklog.assert_called_once()
        call_kwargs = mock_client.add_worklog.call_args.kwargs
        assert call_kwargs["issue_key"] == "TEST-123"
        assert call_kwargs["time_spent_minutes"] == 180  # 3h = 180m

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_log_work_and_comment(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with log work and comment."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "-q",
                "issue",
                "update",
                "TEST-123",
                "--log-work",
                "2h",
                "--work-comment",
                "Implemented feature",
            ],
        )

        assert result.exit_code == 0
        mock_client.add_worklog.assert_called_once()
        call_kwargs = mock_client.add_worklog.call_args.kwargs
        assert call_kwargs["time_spent_minutes"] == 120
        assert call_kwargs["comment"] == "Implemented feature"

    @patch("budjira.cli.issue.get_active_connection")
    def test_update_work_comment_without_log_work(self, mock_get_conn):
        """Test that --work-comment requires --log-work."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--work-comment", "Should fail"],
        )

        assert result.exit_code == 1
        assert "--work-comment requires --log-work" in result.stdout
