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

    @pytest.mark.parametrize("flag", ["--limit", "-n", "--max-results"])
    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_search_with_limit_aliases(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        flag: str,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """Test search with --limit/-n/--max-results spellings of the result cap."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["project = TEST", flag, "5"])

        # Verify
        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST",
            max_results=5,
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


class TestSearchProjectScope:
    """Raw JQL is scoped to the connection's project unless it has its own
    project clause or --all-projects is given (#142)."""

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_raw_jql_without_project_gets_scoped(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["status = 'In Progress'"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST AND (status = 'In Progress')",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_raw_jql_with_project_clause_untouched(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["project in (ABC, DEF) AND status = 'In Progress'"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project in (ABC, DEF) AND status = 'In Progress'",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_all_projects_sends_raw_jql_unchanged(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["status = 'In Progress'", "--all-projects"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "status = 'In Progress'",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_all_projects_omits_project_from_built_jql(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["--status", "In Progress", "--all-projects"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "status = 'In Progress'",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_project_and_all_projects_conflict(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        mock_get_active_connection.return_value = mock_connection

        result = runner.invoke(app, ["--project", "TEST", "--all-projects"])

        assert result.exit_code == 1
        assert "cannot be used together" in result.stdout
        mock_jira_client_class.from_connection.assert_not_called()

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_order_by_stays_outside_the_scoped_parens(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """ORDER BY inside the parenthesised scope is invalid JQL (#142 review)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["status = 'In Progress' ORDER BY created DESC"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST AND (status = 'In Progress') ORDER BY created DESC",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_quoted_literal_cannot_fake_a_project_clause(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """summary ~ \"project in scope\" has no project clause and must be scoped (#142 review)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ['summary ~ "project in scope"'])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            'project = TEST AND (summary ~ "project in scope")',
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_project_was_and_changed_count_as_project_clauses(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """History predicates on project must not get a second scope prepended (#142 review)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        for jql in ["project was ABC", "project was in (ABC, DEF)", "project changed"]:
            result = runner.invoke(app, [jql])
            assert result.exit_code == 0
            mock_client.search_issues.assert_called_with(jql, max_results=50)

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_quoted_project_field_name_counts_as_clause(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """JQL allows quoted field names: "project" = ABC must not be double-scoped (#142 review r2)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ['"project" = ABC'])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with('"project" = ABC', max_results=50)

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_escaped_quote_does_not_end_literal_early(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        r"""An escaped quote inside a literal must not expose \"project = X\" (#142 review r2)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        jql = r'summary ~ "say \"project = X\" now"'
        result = runner.invoke(app, [jql])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            f"project = TEST AND ({jql})",
            max_results=50,
        )

    @patch("budjira.cli.search.JiraClient")
    @patch("budjira.cli.search.get_active_connection")
    def test_order_by_only_jql_gets_no_empty_parens(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_issue: Issue,
    ) -> None:
        """A raw JQL of just ORDER BY scopes to `project = X ORDER BY ...`, no empty parens (#142 review r2)."""
        mock_get_active_connection.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.search_issues.return_value = [mock_issue]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["ORDER BY created DESC"])

        assert result.exit_code == 0
        mock_client.search_issues.assert_called_once_with(
            "project = TEST ORDER BY created DESC",
            max_results=50,
        )
