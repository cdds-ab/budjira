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
        with pytest.raises(JiraAPIError, match="Search failed"):
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
        with pytest.raises(InvalidIssueError, match="Issue 'TEST-123' not found"):
            client.get_issue("TEST-123")

    @patch("budjira.core.jira_client.JIRA")
    def test_get_issue_permission_error(self, mock_jira_class: Mock, connection: Connection) -> None:
        """Test get issue permission denied."""
        mock_jira_instance = MagicMock()
        jira_error = JIRAError(status_code=403, text="Forbidden")
        mock_jira_instance.issue.side_effect = jira_error
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient(connection, "test-token")
        with pytest.raises(PermissionError, match="Permission denied accessing issue"):
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

    @patch("budjira.core.jira_client.CredentialStore")
    @patch("budjira.core.jira_client.JIRA")
    def test_from_connection_success(
        self, mock_jira_class: Mock, mock_cred_store_class: Mock, connection: Connection
    ) -> None:
        """Test creating client from connection."""
        mock_cred_store = MagicMock()
        mock_cred_store.has_credentials.return_value = True
        mock_cred_store.retrieve.return_value = "test-token"
        mock_cred_store_class.return_value = mock_cred_store

        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        client = JiraClient.from_connection(connection)

        assert isinstance(client, JiraClient)
        assert client.connection == connection
        mock_cred_store.has_credentials.assert_called_once_with(connection)
        mock_cred_store.retrieve.assert_called_once_with(connection)

    @patch("budjira.core.jira_client.CredentialStore")
    def test_from_connection_no_credentials(self, mock_cred_store_class: Mock, connection: Connection) -> None:
        """Test from_connection without credentials."""
        mock_cred_store = MagicMock()
        mock_cred_store.has_credentials.return_value = False
        mock_cred_store_class.return_value = mock_cred_store

        with pytest.raises(AuthenticationError, match="No credentials found"):
            JiraClient.from_connection(connection)
