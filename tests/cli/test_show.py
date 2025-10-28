"""Tests for show command."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from budjira.cli.show import format_time_seconds
from budjira.models.connection import Connection
from budjira.models.issue import Attachment, Comment, Issue
from budjira.utils.errors import (
    AuthenticationError,
    ConnectionError,
    InvalidIssueError,
    PermissionError,
)
from typer.testing import CliRunner

runner = CliRunner()


def test_format_time_seconds_none() -> None:
    """Test formatting None time."""
    assert format_time_seconds(None) == "Not set"


def test_format_time_seconds_zero() -> None:
    """Test formatting zero seconds."""
    assert format_time_seconds(0) == "0m"


def test_format_time_seconds_minutes_only() -> None:
    """Test formatting minutes only."""
    assert format_time_seconds(1800) == "30m"  # 30 minutes


def test_format_time_seconds_hours_only() -> None:
    """Test formatting hours only."""
    assert format_time_seconds(3600) == "1h"  # 1 hour
    assert format_time_seconds(7200) == "2h"  # 2 hours


def test_format_time_seconds_hours_and_minutes() -> None:
    """Test formatting hours and minutes."""
    assert format_time_seconds(5400) == "1h 30m"  # 1.5 hours
    assert format_time_seconds(9000) == "2h 30m"  # 2.5 hours


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_basic(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing basic issue without optional fields."""
    # Mock connection
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    # Mock issue
    issue = Issue(
        key="TEST-123",
        summary="Test Issue",
        description="Test description",
        issue_type="Story",
        status="To Do",
        priority="Medium",
        assignee="John Doe",
        reporter="Jane Smith",
        created=datetime(2025, 1, 10, 10, 0, 0),
        updated=datetime(2025, 1, 11, 15, 30, 0),
        labels=["feature", "backend"],
        components=["API"],
        project_key="TEST",
    )

    # Mock JiraClient
    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-123"])

    assert result.exit_code == 0
    assert "TEST-123" in result.stdout
    assert "Test Issue" in result.stdout
    assert "Story" in result.stdout
    assert "To Do" in result.stdout
    assert "John Doe" in result.stdout
    assert "Test description" in result.stdout
    mock_client.get_issue_details.assert_called_once_with("TEST-123")


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_epic(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with epic information."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    issue = Issue(
        key="TEST-456",
        summary="Story with Epic",
        description="Story description",
        issue_type="Story",
        status="In Progress",
        assignee="Alice",
        reporter="Bob",
        project_key="TEST",
        epic_key="TEST-100",
        epic_name="Test Epic",
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-456"])

    assert result.exit_code == 0
    assert "TEST-456" in result.stdout
    assert "TEST-100" in result.stdout
    assert "Test Epic" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_time_tracking(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with time tracking."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    issue = Issue(
        key="TEST-789",
        summary="Issue with Time Tracking",
        description="Time tracked",
        issue_type="Task",
        status="Done",
        assignee="Charlie",
        reporter="David",
        project_key="TEST",
        time_original_estimate=28800,  # 8 hours
        time_remaining_estimate=14400,  # 4 hours
        time_spent=14400,  # 4 hours
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-789"])

    assert result.exit_code == 0
    assert "TEST-789" in result.stdout
    assert "Time Tracking" in result.stdout
    assert "8h" in result.stdout  # Original estimate
    assert "4h" in result.stdout  # Remaining and spent


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_comments(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with comments."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    comments = [
        Comment(
            author="Alice",
            body="First comment",
            created=datetime(2025, 1, 10, 11, 0, 0),
            updated=datetime(2025, 1, 10, 11, 5, 0),
        ),
        Comment(
            author="Bob",
            body="Second comment",
            created=datetime(2025, 1, 10, 12, 0, 0),
            updated=datetime(2025, 1, 10, 12, 0, 0),
        ),
    ]

    issue = Issue(
        key="TEST-999",
        summary="Issue with Comments",
        description="Has comments",
        issue_type="Bug",
        status="In Review",
        assignee="Eve",
        reporter="Frank",
        project_key="TEST",
        comments=comments,
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-999"])

    assert result.exit_code == 0
    assert "TEST-999" in result.stdout
    assert "Comments (2)" in result.stdout
    assert "Alice" in result.stdout
    assert "First comment" in result.stdout
    assert "Bob" in result.stdout
    assert "Second comment" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_attachments(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with attachments."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    attachments = [
        Attachment(
            filename="screenshot.png",
            size=102400,  # 100 KB
            mime_type="image/png",
            created=datetime(2025, 1, 10, 13, 0, 0),
            author="George",
        ),
        Attachment(
            filename="document.pdf",
            size=2097152,  # 2 MB
            mime_type="application/pdf",
            created=datetime(2025, 1, 10, 14, 0, 0),
            author="Hannah",
        ),
    ]

    issue = Issue(
        key="TEST-111",
        summary="Issue with Attachments",
        description="Has attachments",
        issue_type="Story",
        status="Done",
        assignee="Ivan",
        reporter="Julia",
        project_key="TEST",
        attachments=attachments,
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-111"])

    assert result.exit_code == 0
    assert "TEST-111" in result.stdout
    assert "Attachments (2)" in result.stdout
    assert "screenshot.png" in result.stdout
    assert "document.pdf" in result.stdout
    assert "100.0 KB" in result.stdout
    assert "2.0 MB" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_markdown_description(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with Markdown description."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    markdown_description = """## Context
This is a test issue.

## User Story
As a user
I want to see Markdown
So that it looks nice

## Acceptance Criteria
- [ ] Markdown is rendered
- [ ] Looks good
"""

    issue = Issue(
        key="TEST-222",
        summary="Issue with Markdown",
        description=markdown_description,
        issue_type="Story",
        status="To Do",
        assignee="Kate",
        reporter="Liam",
        project_key="TEST",
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-222"])

    assert result.exit_code == 0
    assert "TEST-222" in result.stdout
    # Description should be rendered (Markdown contains ## and - [)


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_not_found(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing non-existent issue."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    mock_client = MagicMock()
    mock_client.get_issue_details.side_effect = InvalidIssueError("Issue 'TEST-999' not found")
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-999"])

    assert result.exit_code == 1
    assert "Issue not found" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_permission_denied(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue without permission."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    mock_client = MagicMock()
    mock_client.get_issue_details.side_effect = PermissionError("Permission denied")
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-123"])

    assert result.exit_code == 1
    assert "Error" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_connection_error(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with connection error."""
    mock_get_connection.side_effect = ConnectionError("No connection found")

    result = runner.invoke(app, ["show", "TEST-123"])

    assert result.exit_code == 1
    assert "Error" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_authentication_error(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with authentication error."""
    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    mock_jira_client_class.from_connection.side_effect = AuthenticationError("Invalid credentials")

    result = runner.invoke(app, ["show", "TEST-123"])

    assert result.exit_code == 1
    assert "Error" in result.stdout


@patch("budjira.cli.show.get_active_connection")
@patch("budjira.cli.show.JiraClient")
def test_show_issue_with_connection_flag(
    mock_jira_client_class: MagicMock,
    mock_get_connection: MagicMock,
) -> None:
    """Test showing issue with --connection flag."""
    connection = Connection(
        name="my-connection",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@test.com",
        project_key="TEST",
    )
    mock_get_connection.return_value = connection

    issue = Issue(
        key="TEST-555",
        summary="Test Issue",
        description="Test",
        issue_type="Task",
        status="Done",
        assignee="User",
        reporter="Reporter",
        project_key="TEST",
    )

    mock_client = MagicMock()
    mock_client.get_issue_details.return_value = issue
    mock_jira_client_class.from_connection.return_value = mock_client

    result = runner.invoke(app, ["show", "TEST-555", "--connection", "my-connection"])

    assert result.exit_code == 0
    assert "TEST-555" in result.stdout
    mock_get_connection.assert_called_once_with("my-connection")
