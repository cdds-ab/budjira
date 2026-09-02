# mypy: disable-error-code="arg-type,call-arg"
"""Tests for Jira client wrapper."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.core.jira_client import JiraClient
from budjira.models.connection import Connection
from budjira.models.issue import Issue
from budjira.utils.errors import (
    AuthenticationError,
    InvalidIssueError,
    JiraAPIError,
    PermissionError,
)
from jira.exceptions import JIRAError


@pytest.fixture
def connection() -> Connection:
    """Create test connection."""
    return Connection(
        name="test-connection",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
    )


@pytest.fixture
def mock_jira_issue() -> MagicMock:
    """Create mock jira issue."""
    issue = MagicMock()
    issue.key = "TEST-123"
    issue.fields.summary = "Test Summary"
    issue.fields.description = "Test Description"
    issue.fields.issuetype.name = "Bug"
    issue.fields.status.name = "In Progress"
    issue.fields.priority.name = "High"
    issue.fields.assignee.displayName = "John Doe"
    issue.fields.reporter.displayName = "Jane Smith"
    issue.fields.created = "2025-01-10T10:00:00.000+0000"
    issue.fields.updated = "2025-01-11T15:30:00.000+0000"
    issue.fields.labels = ["bug", "urgent"]

    # Create proper mock for components
    component_mock = MagicMock()
    component_mock.name = "Frontend"
    issue.fields.components = [component_mock]
    return issue


class TestJiraClientInit:
    """Test JiraClient initialization."""

    @patch("budjira.core.jira_client.JIRA")
    def test_init_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test successful initialization."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")

        assert client.connection == connection
        assert client._client == mock_jira_instance
        # HttpUrl adds trailing slash, so we need to convert to string
        mock_jira_class.assert_called_once_with(
            server=str(connection.url),
            basic_auth=("test@example.com", "test-token"),
            timeout=30,
        )

    @patch("budjira.core.jira_client.JIRA")
    def test_init_authentication_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test authentication failure."""
        jira_error = JIRAError(status_code=401, text="Unauthorized")
        mock_jira_class.side_effect = jira_error

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            JiraClient(connection, "invalid-token")

    @patch("budjira.core.jira_client.JIRA")
    def test_init_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test permission denied during init."""
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_class.side_effect = jira_error

        with pytest.raises(PermissionError, match="Access denied"):
            JiraClient(connection, "test-token")

    @patch("budjira.core.jira_client.JIRA")
    def test_init_api_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test general API error during init."""
        jira_error = JIRAError(status_code=500, text="Internal Server Error")
        mock_jira_class.side_effect = jira_error

        with pytest.raises(JiraAPIError, match="Failed to connect to Jira"):
            JiraClient(connection, "test-token")

    @patch("budjira.core.jira_client.JIRA")
    def test_init_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test unexpected error during init."""
        mock_jira_class.side_effect = ValueError("Unexpected error")

        with pytest.raises(JiraAPIError, match="Unexpected error connecting"):
            JiraClient(connection, "test-token")


class TestJiraClientProperties:
    """Test JiraClient properties."""

    @patch("budjira.core.jira_client.JIRA")
    def test_client_property(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test client property returns JIRA instance."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        assert client.client == mock_jira_instance

    def test_client_property_not_initialized(self, connection: Connection) -> None:
        """Test client property raises error if not initialized."""
        client = JiraClient.__new__(JiraClient)
        client.connection = connection
        client._client = None

        with pytest.raises(JiraAPIError, match="Jira client not initialized"):
            _ = client.client


class TestJiraClientSearchIssues:
    """Test search_issues method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_search_issues_success(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test successful issue search."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.search_issues.return_value = [mock_jira_issue]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issues = client.search_issues("project = TEST", max_results=50)

        assert len(issues) == 1
        assert isinstance(issues[0], Issue)
        assert issues[0].key == "TEST-123"
        mock_jira_instance.search_issues.assert_called_once_with(
            jql_str="project = TEST",
            maxResults=50,
            fields="*all",
        )

    @patch("budjira.core.jira_client.JIRA")
    def test_search_issues_with_fields(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test search with specific fields."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.search_issues.return_value = [mock_jira_issue]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.search_issues("project = TEST", fields=["summary", "status"])

        mock_jira_instance.search_issues.assert_called_once_with(
            jql_str="project = TEST",
            maxResults=50,
            fields=["summary", "status"],
        )

    @patch("budjira.core.jira_client.JIRA")
    def test_search_issues_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test search with permission denied."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.search_issues.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Permission denied while searching"):
            client.search_issues("project = TEST")

    @patch("budjira.core.jira_client.JIRA")
    def test_search_issues_invalid_jql(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test search with invalid JQL."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=400, text="Bad Request")
        mock_jira_instance.search_issues.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Invalid JQL query"):
            client.search_issues("invalid jql")

    @patch("budjira.core.jira_client.JIRA")
    def test_search_issues_api_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test search with API error."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=500, text="Internal Server Error")
        mock_jira_instance.search_issues.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Search issues failed"):
            client.search_issues("project = TEST")


class TestJiraClientGetIssue:
    """Test get_issue method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_success(self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock) -> None:
        """Test successful issue retrieval."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue = client.get_issue("TEST-123")

        assert isinstance(issue, Issue)
        assert issue.key == "TEST-123"
        mock_jira_instance.issue.assert_called_once_with("TEST-123", fields="*all")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_with_fields(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test get issue with specific fields."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.get_issue("TEST-123", fields=["summary", "status"])

        mock_jira_instance.issue.assert_called_once_with("TEST-123", fields="summary,status")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get issue not found."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Fetch issue failed: Resource not found"):
            client.get_issue("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get issue permission denied."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Fetch issue failed: Access denied"):
            client.get_issue("TEST-123")


class TestJiraClientCreateIssue:
    """Test create_issue method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_create_issue_minimal(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test create issue with minimal fields."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.create_issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue = client.create_issue("TEST", "Bug fix", "Bug")

        assert isinstance(issue, Issue)
        assert issue.key == "TEST-123"
        mock_jira_instance.create_issue.assert_called_once()
        call_args = mock_jira_instance.create_issue.call_args[1]
        assert call_args["fields"]["project"]["key"] == "TEST"
        assert call_args["fields"]["summary"] == "Bug fix"
        assert call_args["fields"]["issuetype"]["name"] == "Bug"

    @patch("budjira.core.jira_client.JIRA")
    def test_create_issue_full(self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock) -> None:
        """Test create issue with all fields."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.create_issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue = client.create_issue(
            project_key="TEST",
            summary="Bug fix",
            issue_type="Bug",
            description="Detailed description",
            priority="High",
            assignee="jdoe",
            labels=["urgent", "bug"],
        )

        assert isinstance(issue, Issue)
        call_args = mock_jira_instance.create_issue.call_args[1]
        assert call_args["fields"]["description"] == "Detailed description"
        assert call_args["fields"]["priority"]["name"] == "High"
        assert call_args["fields"]["assignee"]["name"] == "jdoe"
        assert call_args["fields"]["labels"] == ["urgent", "bug"]

    @patch("budjira.core.jira_client.JIRA")
    def test_create_issue_forwards_description_dialect(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """The wrapper must not swallow the dialect the caller resolved."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.create_issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.create_issue(
            project_key="TEST",
            summary="Bug fix",
            issue_type="Bug",
            description="# first\n# second",
            description_dialect="wiki",
        )

        call_args = mock_jira_instance.create_issue.call_args[1]
        assert call_args["fields"]["description"] == "# first\n# second"

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_forwards_description_dialect(
        self, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """The wrapper must not swallow the dialect the caller resolved."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_jira_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", description="# first\n# second", description_dialect="wiki")

        call_args = mock_jira_issue.update.call_args[1]
        assert call_args["fields"]["description"] == "# first\n# second"

    @patch("budjira.core.jira_client.JIRA")
    def test_create_issue_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test create issue permission denied."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.create_issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Permission denied creating issue"):
            client.create_issue("TEST", "Bug fix", "Bug")

    @patch("budjira.core.jira_client.JIRA")
    def test_create_issue_validation_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test create issue with invalid data."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=400, text="Bad Request")
        mock_jira_instance.create_issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Invalid issue data"):
            client.create_issue("TEST", "Bug fix", "InvalidType")


class TestJiraClientAddWorklog:
    """Test add_worklog method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_minimal(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog with minimal fields."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_worklog("TEST-123", 90)

        mock_jira_instance.add_worklog.assert_called_once_with(
            issue="TEST-123",
            timeSpent="1h 30m",
            comment=None,
            started=None,
        )

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_full(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog with all fields."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        started = datetime(2025, 1, 10, 9, 0)
        client = JiraClient(connection, "test-token")
        client.add_worklog("TEST-123", 120, comment="Fixed bug", started=started)

        mock_jira_instance.add_worklog.assert_called_once_with(
            issue="TEST-123",
            timeSpent="2h",
            comment="Fixed bug",
            started=started,
        )

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_minutes_only(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog with only minutes."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_worklog("TEST-123", 45)

        call_args = mock_jira_instance.add_worklog.call_args[1]
        assert call_args["timeSpent"] == "45m"

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_hours_only(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog with exact hours."""
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_worklog("TEST-123", 180)

        call_args = mock_jira_instance.add_worklog.call_args[1]
        assert call_args["timeSpent"] == "3h"

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_issue_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog to non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.add_worklog.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Issue 'TEST-123' not found"):
            client.add_worklog("TEST-123", 60)

    @patch("budjira.core.jira_client.JIRA")
    def test_add_worklog_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test add worklog permission denied."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.add_worklog.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Permission denied logging work"):
            client.add_worklog("TEST-123", 60)

    @patch("budjira.core.jira_client.JIRA")
    def test_get_worklogs_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get worklogs for issue."""
        # Mock worklogs
        mock_worklog1 = MagicMock()
        mock_worklog1.id = "10001"
        mock_worklog1.author.displayName = "John Doe"
        mock_worklog1.timeSpent = "2h 30m"
        mock_worklog1.timeSpentSeconds = 9000
        mock_worklog1.started = "2025-10-24T14:00:00.000+0000"
        mock_worklog1.created = "2025-10-24T16:30:00.000+0000"
        mock_worklog1.comment = "Implemented feature X"

        mock_worklog2 = MagicMock()
        mock_worklog2.id = "10002"
        mock_worklog2.author.displayName = "Jane Smith"
        mock_worklog2.timeSpent = "1h"
        mock_worklog2.timeSpentSeconds = 3600
        mock_worklog2.started = "2025-10-25T09:00:00.000+0000"
        mock_worklog2.created = "2025-10-25T10:00:00.000+0000"
        # No comment on this worklog
        del mock_worklog2.comment

        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_instance.worklogs.return_value = [mock_worklog1, mock_worklog2]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        worklogs = client.get_worklogs("TEST-123")

        assert len(worklogs) == 2

        # Check first worklog
        assert worklogs[0]["id"] == "10001"
        assert worklogs[0]["author"] == "John Doe"
        assert worklogs[0]["timeSpent"] == "2h 30m"
        assert worklogs[0]["timeSpentSeconds"] == 9000
        assert worklogs[0]["started"] == "2025-10-24T14:00:00.000+0000"
        assert worklogs[0]["created"] == "2025-10-24T16:30:00.000+0000"
        assert worklogs[0]["comment"] == "Implemented feature X"

        # Check second worklog (no comment)
        assert worklogs[1]["id"] == "10002"
        assert worklogs[1]["author"] == "Jane Smith"
        assert "comment" not in worklogs[1]

        mock_jira_instance.issue.assert_called_once_with("TEST-123")
        mock_jira_instance.worklogs.assert_called_once_with(mock_issue)

    @patch("budjira.core.jira_client.JIRA")
    def test_get_worklogs_empty(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get worklogs for issue with no worklogs."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_instance.worklogs.return_value = []
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        worklogs = client.get_worklogs("TEST-123")

        assert len(worklogs) == 0
        assert worklogs == []

    @patch("budjira.core.jira_client.JIRA")
    def test_get_worklogs_issue_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get worklogs for non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Issue 'TEST-123' not found"):
            client.get_worklogs("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_worklogs_api_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get worklogs with API error."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=500, text="Internal Server Error")
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Fetch worklogs failed"):
            client.get_worklogs("TEST-123")


class TestJiraClientMetadata:
    """Test metadata retrieval methods."""

    @patch("budjira.core.jira_client.JIRA")
    def test_get_projects(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get projects."""
        mock_project1 = MagicMock()
        mock_project1.key = "PROJ1"
        mock_project1.name = "Project 1"
        mock_project2 = MagicMock()
        mock_project2.key = "PROJ2"
        mock_project2.name = "Project 2"

        mock_jira_instance = MagicMock()
        mock_jira_instance.projects.return_value = [mock_project1, mock_project2]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        projects = client.get_projects()

        assert len(projects) == 2
        assert projects[0] == {"key": "PROJ1", "name": "Project 1"}
        assert projects[1] == {"key": "PROJ2", "name": "Project 2"}

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_types(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get issue types."""
        mock_type1 = MagicMock()
        mock_type1.name = "Bug"
        mock_type2 = MagicMock()
        mock_type2.name = "Task"

        mock_jira_instance = MagicMock()
        mock_jira_instance.issue_types.return_value = [mock_type1, mock_type2]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue_types = client.get_issue_types("TEST")

        assert len(issue_types) == 2
        assert issue_types == ["Bug", "Task"]

    @patch("budjira.core.jira_client.JIRA")
    def test_get_priorities(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get priorities."""
        mock_priority1 = MagicMock()
        mock_priority1.name = "High"
        mock_priority2 = MagicMock()
        mock_priority2.name = "Low"

        mock_jira_instance = MagicMock()
        mock_jira_instance.priorities.return_value = [mock_priority1, mock_priority2]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        priorities = client.get_priorities()

        assert len(priorities) == 2
        assert priorities == ["High", "Low"]


class TestJiraClientFromConnection:
    """Test from_connection factory method."""

    @patch("budjira.core.jira_client.resolve_api_token")
    @patch("budjira.core.jira_client.JIRA")
    def test_from_connection_success(self, mock_jira_class: Mock, mock_resolve: Mock, connection: Connection) -> None:
        """Test creating client from connection."""
        mock_resolve.return_value = "test-token"

        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient.from_connection(connection)

        assert isinstance(client, JiraClient)
        assert client.connection == connection
        mock_resolve.assert_called_once_with(connection)

    @patch("budjira.core.jira_client.resolve_api_token")
    def test_from_connection_no_credentials(self, mock_resolve: Mock, connection: Connection) -> None:
        """Test from_connection without any token source."""
        mock_resolve.return_value = None

        with pytest.raises(AuthenticationError, match="No API token found"):
            JiraClient.from_connection(connection)


class TestJiraClientTransitions:
    """Test get_transitions and transition_issue methods."""

    @patch("budjira.core.jira_client.JIRA")
    def test_get_transitions_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test getting available transitions."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        transitions = client.get_transitions("TEST-123")

        assert len(transitions) == 3
        assert transitions[0] == {"id": "11", "name": "To Do"}
        assert transitions[1] == {"id": "21", "name": "In Progress"}
        assert transitions[2] == {"id": "31", "name": "Done"}
        mock_jira_instance.transitions.assert_called_once_with("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_transitions_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get transitions for non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.transitions.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="not found"):
            client.get_transitions("TEST-999")

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test successful issue transition."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.transition_issue("TEST-123", "In Progress")

        mock_jira_instance.transition_issue.assert_called_once_with("TEST-123", "21", fields=None)

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_case_insensitive(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test transition with case-insensitive matching."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.transition_issue("TEST-123", "in progress")  # lowercase

        mock_jira_instance.transition_issue.assert_called_once_with("TEST-123", "21", fields=None)

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_invalid_transition(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test transition with invalid transition name."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match=r"Invalid transition.*Available transitions"):
            client.transition_issue("TEST-123", "Invalid Status")


class TestJiraClientUpdateIssue:
    """Test update_issue method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_assignee_current_user(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test updating assignee to current user."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_instance.myself.return_value = {"accountId": "12345"}
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", assignee="currentUser()")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert call_args["assignee"] == {"accountId": "12345"}

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_assignee_specific_user(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test updating assignee to specific user."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", assignee="jdoe")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert call_args["assignee"] == {"name": "jdoe"}

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_unassign(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test unassigning issue."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", assignee="")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert call_args["assignee"] is None

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_priority(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test updating priority."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", priority="High")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert call_args["priority"] == {"name": "High"}

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_summary_and_description(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test updating summary and description."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123", summary="New Summary", description="New Description")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert call_args["summary"] == "New Summary"
        assert call_args["description"] == "New Description"

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_no_fields(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test update with no fields specified."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.update_issue("TEST-123")  # No fields

        # Should not call update if no fields
        mock_issue.update.assert_not_called()

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test updating non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.return_value.update.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="not found"):
            client.update_issue("TEST-999", priority="High")


class TestJiraClientLabels:
    """Test add_labels and remove_labels methods."""

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_to_empty(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding labels to issue with no labels."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_labels("TEST-123", ["bug", "urgent"])

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]["labels"]
        assert set(call_args) == {"bug", "urgent"}

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_to_existing(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding labels to issue with existing labels."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["feature"]
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_labels("TEST-123", ["bug", "urgent"])

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]["labels"]
        assert set(call_args) == {"feature", "bug", "urgent"}

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_duplicate(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding duplicate labels (should not duplicate)."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["bug"]
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.add_labels("TEST-123", ["bug", "urgent"])

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]["labels"]
        assert set(call_args) == {"bug", "urgent"}

    @patch("budjira.core.jira_client.JIRA")
    def test_remove_labels(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test removing labels."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["bug", "urgent", "feature"]
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.remove_labels("TEST-123", ["urgent"])

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]["labels"]
        assert call_args == ["bug", "feature"]

    @patch("budjira.core.jira_client.JIRA")
    def test_remove_labels_nonexistent(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test removing labels that don't exist (should not error)."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["bug"]
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.remove_labels("TEST-123", ["nonexistent"])

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]["labels"]
        assert call_args == ["bug"]


class TestJiraClientEpic:
    """Test epic-related methods."""

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_success_modern(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test linking issue to epic using modern parent field (Jira Cloud team-managed)."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.link_to_epic("TEST-123", "TEST-100")

        # Should use parent field (modern approach)
        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args[1]["fields"]
        assert "parent" in call_args
        assert call_args["parent"] == {"key": "TEST-100"}

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_success_legacy(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test linking issue to epic using legacy Epic Link field (fallback)."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue

        # Make parent field fail (to trigger fallback)
        mock_issue.update.side_effect = [
            JIRAError("Parent field not supported", status_code=400),
            None,  # Second call succeeds
        ]

        mock_jira_instance.fields.return_value = [
            {"id": "customfield_10014", "name": "Epic Link"},
            {"id": "customfield_10015", "name": "Sprint"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        client.link_to_epic("TEST-123", "TEST-100")

        # Should have called update twice (parent fails, Epic Link succeeds)
        assert mock_issue.update.call_count == 2
        # Check the second call used Epic Link
        call_args = mock_issue.update.call_args[1]["fields"]
        assert "customfield_10014" in call_args
        assert call_args["customfield_10014"] == "TEST-100"

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_no_epic_field(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test linking when neither parent nor Epic Link field exists."""
        mock_issue = MagicMock()
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue

        # Make parent field fail
        mock_issue.update.side_effect = JIRAError("Parent field not supported", status_code=400)

        # No Epic Link field in fields list
        mock_jira_instance.fields.return_value = [
            {"id": "customfield_10015", "name": "Sprint"},
        ]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(
            JiraAPIError, match=r"Epic linking failed\. Neither 'parent' field nor 'Epic Link' custom field found"
        ):
            client.link_to_epic("TEST-123", "TEST-100")

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test linking to non-existent epic."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.fields.return_value = [
            {"id": "customfield_10014", "name": "Epic Link"},
        ]
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.return_value.update.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Issue or epic not found"):
            client.link_to_epic("TEST-123", "TEST-999")

    @pytest.mark.skip(reason="get_epic_issues method moved to EpicService during refactoring")
    @patch("budjira.core.jira_client.JIRA")
    @patch.object(JiraClient, "search_issues")
    def test_get_epic_issues_modern(
        self, mock_search: Mock, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test getting issues linked to epic using modern parent field."""
        mock_issue_obj = Issue.from_jira_issue(mock_jira_issue)
        mock_search.return_value = [mock_issue_obj]

        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issues = client.get_epic_issues("TEST-100")

        assert len(issues) == 1
        assert issues[0].key == "TEST-123"
        # Should try modern approach first
        mock_search.assert_called_once_with("parent = TEST-100", max_results=100)

    @pytest.mark.skip(reason="get_epic_issues method moved to EpicService during refactoring")
    @patch("budjira.core.jira_client.JIRA")
    @patch.object(JiraClient, "search_issues")
    def test_get_epic_issues_legacy_fallback(
        self, mock_search: Mock, mock_jira_class: Mock, connection: Connection, mock_jira_issue: MagicMock
    ) -> None:
        """Test getting issues linked to epic using legacy Epic Link field (fallback)."""
        mock_issue_obj = Issue.from_jira_issue(mock_jira_issue)
        # First call (modern) returns empty, second call (legacy) returns issues
        mock_search.side_effect = [[], [mock_issue_obj]]

        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issues = client.get_epic_issues("TEST-100")

        assert len(issues) == 1
        assert issues[0].key == "TEST-123"
        # Should have called search_issues twice
        assert mock_search.call_count == 2
        # First with modern, then with legacy
        mock_search.assert_any_call("parent = TEST-100", max_results=100)
        mock_search.assert_any_call('"Epic Link" = TEST-100', max_results=100)


class TestJiraClientEdgeCases:
    """Test edge cases and error paths."""

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_jira_error_404(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test transition with 404 error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [{"id": "21", "name": "Done"}]
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.transition_issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="not found"):
            client.transition_issue("TEST-123", "Done")

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_jira_error_other(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test transition with non-404 Jira error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [{"id": "21", "name": "Done"}]
        jira_error = JIRAError(status_code=400, text="Bad Request")
        mock_jira_instance.transition_issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Transition issue failed"):
            client.transition_issue("TEST-123", "Done")

    @patch("budjira.core.jira_client.JIRA")
    def test_transition_issue_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test transition with unexpected error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.return_value = [{"id": "21", "name": "Done"}]
        mock_jira_instance.transition_issue.side_effect = RuntimeError("Unexpected")
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.transition_issue("TEST-123", "Done")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_transitions_jira_error_other(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get transitions with non-404 error."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.transitions.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Fetch transitions failed: Access denied"):
            client.get_transitions("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_transitions_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get transitions with unexpected error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.transitions.side_effect = RuntimeError("Unexpected")
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.get_transitions("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_bad_request(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test update with 400 bad request error."""
        mock_issue = MagicMock()
        jira_error = JIRAError(status_code=400, text="Invalid field")
        mock_issue.update.side_effect = jira_error
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Invalid field values"):
            client.update_issue("TEST-123", priority="InvalidPriority")

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_other_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test update with other Jira error."""
        mock_issue = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_issue.update.side_effect = jira_error
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Update issue failed: Access denied"):
            client.update_issue("TEST-123", priority="High")

    @patch("budjira.core.jira_client.JIRA")
    def test_update_issue_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test update with unexpected error."""
        mock_issue = MagicMock()
        mock_issue.update.side_effect = RuntimeError("Unexpected")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.update_issue("TEST-123", priority="High")

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding labels to non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.return_value.update.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="not found"):
            client.add_labels("TEST-999", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_jira_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding labels with Jira error."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_issue.update.side_effect = jira_error
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Add labels failed: Access denied"):
            client.add_labels("TEST-123", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_add_labels_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding labels with unexpected error."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = []
        mock_issue.update.side_effect = RuntimeError("Unexpected")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.add_labels("TEST-123", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_remove_labels_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test removing labels from non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.issue.return_value.update.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="not found"):
            client.remove_labels("TEST-999", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_remove_labels_jira_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test removing labels with Jira error."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["bug"]
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_issue.update.side_effect = jira_error
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Remove labels failed: Access denied"):
            client.remove_labels("TEST-123", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_remove_labels_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test removing labels with unexpected error."""
        mock_issue = MagicMock()
        mock_issue.fields.labels = ["bug"]
        mock_issue.update.side_effect = RuntimeError("Unexpected")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.remove_labels("TEST-123", ["bug"])

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_jira_error_other(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test epic linking with non-404 Jira error."""
        mock_issue = MagicMock()
        jira_error = JIRAError(status_code=400, text="Bad Request")
        mock_issue.update.side_effect = jira_error
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_instance.fields.return_value = [{"id": "customfield_10014", "name": "Epic Link"}]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Link to epic failed"):
            client.link_to_epic("TEST-123", "TEST-100")

    @patch("budjira.core.jira_client.JIRA")
    def test_link_to_epic_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test epic linking with unexpected error."""
        mock_issue = MagicMock()
        mock_issue.update.side_effect = RuntimeError("Unexpected")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.return_value = mock_issue
        mock_jira_instance.fields.return_value = [{"id": "customfield_10014", "name": "Epic Link"}]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error"):
            client.link_to_epic("TEST-123", "TEST-100")

    @pytest.mark.skip(reason="get_epic_issues method moved to EpicService during refactoring")
    @patch("budjira.core.jira_client.JIRA")
    def test_get_epic_issues_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test getting epic issues with error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.search_issues.side_effect = RuntimeError("Unexpected")
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Failed to fetch epic issues"):
            client.get_epic_issues("TEST-100")


class TestJiraClientGetIssueDetails:
    """Test get_issue_details method with full details."""

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_details_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test successful retrieval of detailed issue with epic, time tracking, comments, and attachments."""
        # Create comprehensive mock issue
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Test Issue with Full Details"
        mock_issue.fields.description = "## Description\n\nThis is a detailed issue."
        mock_issue.fields.issuetype.name = "Story"
        mock_issue.fields.status.name = "In Progress"
        mock_issue.fields.priority.name = "High"
        mock_issue.fields.assignee.displayName = "John Doe"
        mock_issue.fields.reporter.displayName = "Jane Smith"
        mock_issue.fields.created = "2025-01-10T10:00:00.000+0000"
        mock_issue.fields.updated = "2025-01-11T15:30:00.000+0000"
        mock_issue.fields.labels = ["feature", "urgent"]
        component_mock = MagicMock()
        component_mock.name = "Frontend"
        mock_issue.fields.components = [component_mock]

        # Add time tracking
        mock_issue.fields.timetracking = MagicMock()
        mock_issue.fields.timetracking.originalEstimateSeconds = 28800  # 8 hours
        mock_issue.fields.timetracking.remainingEstimateSeconds = 14400  # 4 hours
        mock_issue.fields.timetracking.timeSpentSeconds = 14400  # 4 hours

        # Add comments
        comment1 = MagicMock()
        comment1.author.displayName = "Alice"
        comment1.body = "First comment"
        comment1.created = "2025-01-10T11:00:00.000+0000"
        comment1.updated = "2025-01-10T11:05:00.000+0000"

        comment2 = MagicMock()
        comment2.author.displayName = "Bob"
        comment2.body = "Second comment"
        comment2.created = "2025-01-10T12:00:00.000+0000"
        comment2.updated = "2025-01-10T12:00:00.000+0000"

        mock_issue.fields.comment = MagicMock()
        mock_issue.fields.comment.comments = [comment1, comment2]

        # Add attachments
        attachment1 = MagicMock()
        attachment1.filename = "screenshot.png"
        attachment1.size = 102400  # 100 KB
        attachment1.mimeType = "image/png"
        attachment1.created = "2025-01-10T13:00:00.000+0000"
        attachment1.author.displayName = "Charlie"

        attachment2 = MagicMock()
        attachment2.filename = "document.pdf"
        attachment2.size = 512000  # 500 KB
        attachment2.mimeType = "application/pdf"
        attachment2.created = "2025-01-10T14:00:00.000+0000"
        attachment2.author.displayName = "David"

        mock_issue.fields.attachment = [attachment1, attachment2]

        # Add parent (epic) field
        mock_parent = MagicMock()
        mock_parent.key = "TEST-100"
        mock_parent.fields.summary = "Test Epic"
        mock_issue.fields.parent = mock_parent

        # Mock epic issue for get_issue_epic call
        mock_epic_issue = MagicMock()
        mock_epic_issue.key = "TEST-100"
        mock_epic_issue.fields.summary = "Test Epic"
        mock_epic_issue.fields.parent = mock_parent

        mock_jira_instance = MagicMock()
        # Return different mocks for different calls
        mock_jira_instance.issue.side_effect = [mock_issue, mock_epic_issue]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue = client.get_issue_details("TEST-123")

        # Verify basic fields
        assert issue.key == "TEST-123"
        assert issue.summary == "Test Issue with Full Details"
        assert issue.description == "## Description\n\nThis is a detailed issue."
        assert issue.issue_type == "Story"
        assert issue.status == "In Progress"
        assert issue.priority == "High"

        # Verify epic info
        assert issue.epic_key == "TEST-100"
        assert issue.epic_name == "Test Epic"

        # Verify time tracking
        assert issue.time_original_estimate == 28800
        assert issue.time_remaining_estimate == 14400
        assert issue.time_spent == 14400

        # Verify comments
        assert len(issue.comments) == 2
        assert issue.comments[0].author == "Alice"
        assert issue.comments[0].body == "First comment"
        assert issue.comments[1].author == "Bob"
        assert issue.comments[1].body == "Second comment"

        # Verify attachments
        assert len(issue.attachments) == 2
        assert issue.attachments[0].filename == "screenshot.png"
        assert issue.attachments[0].size == 102400
        assert issue.attachments[0].mime_type == "image/png"
        assert issue.attachments[1].filename == "document.pdf"
        assert issue.attachments[1].size == 512000

        # Verify API was called (first for issue details, second for epic)
        assert mock_jira_instance.issue.call_count == 2

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_details_without_epic(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test detailed issue without epic link."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-124"
        mock_issue.fields.summary = "Issue without Epic"
        mock_issue.fields.description = "No epic"
        mock_issue.fields.issuetype.name = "Task"
        mock_issue.fields.status.name = "To Do"
        mock_issue.fields.priority = None
        mock_issue.fields.assignee = None
        mock_issue.fields.reporter = None
        mock_issue.fields.created = "2025-01-10T10:00:00.000+0000"
        mock_issue.fields.updated = "2025-01-10T10:00:00.000+0000"
        mock_issue.fields.labels = []
        mock_issue.fields.components = []
        mock_issue.fields.timetracking = None
        mock_issue.fields.comment = None
        mock_issue.fields.attachment = []
        mock_issue.fields.parent = None

        # Mock for get_issue_epic call (will return the same issue, with no parent)
        mock_epic_check = MagicMock()
        mock_epic_check.key = "TEST-124"
        mock_epic_check.fields.parent = None

        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.side_effect = [mock_issue, mock_epic_check]
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        issue = client.get_issue_details("TEST-124")

        assert issue.key == "TEST-124"
        assert issue.epic_key is None
        assert issue.epic_name is None
        assert issue.time_original_estimate is None
        assert issue.time_remaining_estimate is None
        assert issue.time_spent is None
        assert len(issue.comments) == 0
        assert len(issue.attachments) == 0

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_details_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test detailed issue retrieval with 404 error."""
        jira_error = JIRAError(status_code=404, text="Issue not found")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Fetch issue details failed: Resource not found"):
            client.get_issue_details("TEST-999")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_details_permission_denied(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test detailed issue retrieval with permission error."""
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Fetch issue details failed: Access denied"):
            client.get_issue_details("TEST-123")


class TestJiraClientAddComment:
    """Test add_comment method."""

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_success(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding a comment successfully."""
        mock_jira_instance = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = "12345"
        mock_comment.author.displayName = "John Doe"
        mock_comment.body = "This is a test comment"
        mock_comment.created = "2025-11-04T10:00:00.000+0000"
        mock_jira_instance.add_comment.return_value = mock_comment
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        result = client.add_comment("TEST-123", "This is a test comment")

        # Verify API call
        mock_jira_instance.add_comment.assert_called_once_with("TEST-123", "This is a test comment")

        # Verify result
        assert result["id"] == "12345"
        assert result["author"] == "John Doe"
        assert result["body"] == "This is a test comment"
        assert result["created"] == "2025-11-04T10:00:00.000+0000"

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_multiline(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding a multi-line comment."""
        mock_jira_instance = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = "12346"
        mock_comment.author.displayName = "Jane Smith"
        multiline_body = "Line 1\nLine 2\nLine 3"
        mock_comment.body = multiline_body
        mock_comment.created = "2025-11-04T11:00:00.000+0000"
        mock_jira_instance.add_comment.return_value = mock_comment
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        result = client.add_comment("TEST-456", multiline_body)

        # Verify multiline content preserved
        assert result["body"] == multiline_body
        mock_jira_instance.add_comment.assert_called_once_with("TEST-456", multiline_body)

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_markdown(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding a markdown-formatted comment."""
        mock_jira_instance = MagicMock()
        mock_comment = MagicMock()
        mock_comment.id = "12347"
        mock_comment.author.displayName = "Bob Builder"
        markdown_body = "# Heading\n\n* List item 1\n* List item 2\n\n[Link](https://example.com)"
        mock_comment.body = markdown_body
        mock_comment.created = "2025-11-04T12:00:00.000+0000"
        mock_jira_instance.add_comment.return_value = mock_comment
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        result = client.add_comment("TEST-789", markdown_body)

        # Verify markdown content preserved
        assert result["body"] == markdown_body

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_issue_not_found(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding comment to non-existent issue."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=404, text="Not Found")
        mock_jira_instance.add_comment.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(InvalidIssueError, match="Issue 'TEST-999' not found"):
            client.add_comment("TEST-999", "Comment text")

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding comment without permission."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.add_comment.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="You don't have permission to comment"):
            client.add_comment("TEST-123", "Comment text")

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_api_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding comment with API error."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=500, text="Internal Server Error")
        mock_jira_instance.add_comment.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Add comment failed"):
            client.add_comment("TEST-123", "Comment text")

    @patch("budjira.core.jira_client.JIRA")
    def test_add_comment_unexpected_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test adding comment with unexpected error."""
        mock_jira_instance = MagicMock()
        mock_jira_instance.add_comment.side_effect = RuntimeError("Unexpected error")
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(JiraAPIError, match="Unexpected error adding comment"):
            client.add_comment("TEST-123", "Comment text")
