# mypy: disable-error-code="arg-type,call-arg"
"""Tests for search command."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.cli.search import app
from budjira.models.connection import Connection
from budjira.models.issue import Issue
from budjira.utils.errors import JiraAPIError, PermissionError
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_connection() -> Connection:
    """Create mock connection."""
    return Connection(
        name="test-connection",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
    )


@pytest.fixture
def mock_issue() -> Issue:
    """Create mock issue."""
    return Issue(
        key="TEST-123",
        summary="Test issue summary",
        issue_type="Bug",
        status="In Progress",
        priority="High",
        assignee="John Doe",
        project_key="TEST",
    )


class TestSearchCommand:
    """Test search command."""

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_jql(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with raw JQL query."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST AND status = 'In Progress'"])

        # Verify
        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST AND status = 'In Progress'",
            max_results=50,
        )
        assert "TEST-123" in result.stdout
        assert "Test issue summary" in result.stdout

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_filters(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with filter options."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command with filters
        result = runner.invoke(
            app,
            [
                "--status",
                "In Progress",
                "--assignee",
                "jdoe",
                "--type",
                "Bug",
            ],
        )

        # Verify
        assert result.exit_code == 0
        # Should build JQL from filters
        call_args = mock_client.search_issues.call_args[0]
        jql = call_args[0]
        assert "project = TEST" in jql
        assert "status = 'In Progress'" in jql
        assert "assignee = 'jdoe'" in jql
        assert "type = 'Bug'" in jql

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_current_user(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with currentUser() function."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["--assignee", "currentUser()"])

        # Verify
        assert result.exit_code == 0
        call_args = mock_client.search_issues.call_args[0]
        jql = call_args[0]
        # currentUser() should not be quoted
        assert "assignee = currentUser()" in jql
        assert "assignee = 'currentUser()'" not in jql

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_project_override(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with project override."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command with project override
        result = runner.invoke(app, ["--project", "OTHER", "--status", "Done"])

        # Verify
        assert result.exit_code == 0
        call_args = mock_client.search_issues.call_args[0]
        jql = call_args[0]
        assert "project = OTHER" in jql

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_max_results(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with custom max results."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST", "--max", "100"])

        # Verify
        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST",
            max_results=100,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_no_results(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test search with no results."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 0
        assert "No issues found" in result.stdout

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_multiple_results(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test search with multiple results."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        issues = [
            Issue(
                key=f"TEST-{i}",
                summary=f"Issue {i}",
                issue_type="Bug",
                status="In Progress",
                project_key="TEST",
            )
            for i in range(1, 4)
        ]

        mock_client = MagicMock()
        mock_client.search_issues.return_value = issues
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 0
        assert "3 issues" in result.stdout
        assert "TEST-1" in result.stdout
        assert "TEST-2" in result.stdout
        assert "TEST-3" in result.stdout

    @patch("budjira.cli.search.get_active_connection")
    def test_search_no_connection(
        self,
        mock_get_active_connection: Mock,
    ) -> None:
        """Test search without connection configured."""
        # Setup mocks
        from budjira.utils.errors import BudjiraError

        mock_get_active_connection.side_effect = BudjiraError("No active connection configured")

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 1
        assert "No active connection" in result.stdout

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_default_project(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test search with no arguments uses default project."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command without arguments - should use default project from connection
        result = runner.invoke(app, [])

        # Should succeed and use default project
        assert result.exit_code == 0
        # Should search with default project
        call_args = mock_client.search_issues.call_args[0]
        jql = call_args[0]
        assert "project = TEST" in jql

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_api_error(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test search with API error."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.side_effect = JiraAPIError("API error occurred")
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 1
        assert "API error occurred" in result.stdout

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_permission_error(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test search with permission error."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.side_effect = PermissionError("Access denied")
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 1
        assert "Access denied" in result.stdout

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_long_summary_truncated(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test that long summaries are truncated in output."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        long_summary = "A" * 100  # 100 character summary
        issue = Issue(
            key="TEST-123",
            summary=long_summary,
            issue_type="Bug",
            status="In Progress",
            project_key="TEST",
        )

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST"])

        # Verify
        assert result.exit_code == 0
        # Summary should be truncated with ellipsis (Rich uses Unicode ellipsis)
        assert "…" in result.stdout or "..." in result.stdout
        # Full summary should not appear
        assert long_summary not in result.stdout
