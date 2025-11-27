"""Test epic CLI commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.issue import Issue
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_jira_client():
    """Mock JiraClient for epic tests."""
    with patch("budjira.cli.epic.JiraClient") as mock:
        yield mock


@pytest.fixture
def mock_get_active_connection(mock_connection):
    """Mock get_active_connection."""
    with patch("budjira.cli.epic.get_active_connection", return_value=mock_connection):
        yield mock_connection


def test_epic_help() -> None:
    """Test epic subcommand help."""
    result = runner.invoke(app, ["epic", "--help"])
    assert result.exit_code == 0
    assert "epic" in result.stdout.lower()
    assert "show" in result.stdout.lower()


def test_epic_show_help() -> None:
    """Test epic show command help."""
    result = runner.invoke(app, ["epic", "show", "--help"])
    assert result.exit_code == 0
    assert "show" in result.stdout.lower()
    assert "epic" in result.stdout.lower()


def test_epic_show_requires_argument() -> None:
    """Test that epic show requires epic key argument."""
    result = runner.invoke(app, ["-q", "epic", "show"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


def test_epic_show_json_output_with_timetracking(mock_get_active_connection, mock_jira_client):
    """Test epic show with JSON output format including time tracking."""
    # Mock epic issue with time tracking
    epic_issue = Issue(
        key="EPIC-1",
        summary="Test Epic",
        status="In Progress",
        issue_type="Epic",
        project_key="TEST",
        assignee="John Doe",
        priority="High",
        time_original_estimate=7200,  # 2h
        time_remaining_estimate=3600,  # 1h
        time_spent=3600,  # 1h
    )

    # Mock child issues with time tracking
    child_issues = [
        Issue(
            key="STORY-1",
            summary="Story 1",
            status="Done",
            issue_type="Story",
            project_key="TEST",
            assignee="Jane Smith",
            priority="Medium",
            time_original_estimate=3600,  # 1h
            time_remaining_estimate=0,
            time_spent=3600,  # 1h
        ),
        Issue(
            key="STORY-2",
            summary="Story 2",
            status="In Progress",
            issue_type="Story",
            project_key="TEST",
            assignee="John Doe",
            priority="High",
            time_original_estimate=5400,  # 1h 30m
            time_remaining_estimate=1800,  # 30m
            time_spent=3600,  # 1h
        ),
    ]

    # Setup mocks
    mock_client_instance = MagicMock()
    mock_client_instance.search_issues.return_value = [epic_issue]
    mock_client_instance.get_epic_issues.return_value = child_issues
    mock_jira_client.from_connection.return_value = mock_client_instance

    # Run command with --format json
    result = runner.invoke(app, ["--format", "json", "epic", "show", "EPIC-1"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    # Check epic data
    assert output["epic"]["key"] == "EPIC-1"
    assert output["epic"]["summary"] == "Test Epic"
    assert output["epic"]["status"] == "In Progress"
    assert output["epic"]["assignee"] == "John Doe"
    assert output["epic"]["priority"] == "High"
    assert output["epic"]["url"] == "https://test.atlassian.net/browse/EPIC-1"

    # Check epic time tracking
    assert "timetracking" in output["epic"]
    assert output["epic"]["timetracking"]["originalEstimateSeconds"] == 7200
    assert output["epic"]["timetracking"]["remainingEstimateSeconds"] == 3600
    assert output["epic"]["timetracking"]["timeSpentSeconds"] == 3600
    assert output["epic"]["timetracking"]["originalEstimate"] == "2h"
    assert output["epic"]["timetracking"]["remainingEstimate"] == "1h"
    assert output["epic"]["timetracking"]["timeSpent"] == "1h"

    # Check stories
    assert len(output["stories"]) == 2

    # Check first story
    story1 = output["stories"][0]
    assert story1["key"] == "STORY-1"
    assert story1["summary"] == "Story 1"
    assert story1["status"] == "Done"
    assert story1["timetracking"]["originalEstimate"] == "1h"
    assert story1["timetracking"]["timeSpent"] == "1h"

    # Check second story (with mixed hours and minutes)
    story2 = output["stories"][1]
    assert story2["key"] == "STORY-2"
    assert story2["timetracking"]["originalEstimate"] == "1h 30m"
    assert story2["timetracking"]["remainingEstimate"] == "30m"

    # Check progress data
    assert output["progress"]["total_issues"] == 2
    assert output["progress"]["done_issues"] == 1
    assert output["progress"]["in_progress_issues"] == 1
    assert output["progress"]["todo_issues"] == 1
    assert output["progress"]["progress_percent"] == 50


def test_epic_show_json_output_without_timetracking(mock_get_active_connection, mock_jira_client):
    """Test epic show JSON output without time tracking data."""
    # Mock epic without time tracking
    epic_issue = Issue(
        key="EPIC-2",
        summary="Epic without time tracking",
        status="To Do",
        issue_type="Epic",
        project_key="TEST",
        assignee=None,
        priority="Low",
    )

    # Mock child issues without time tracking
    child_issues = [
        Issue(
            key="TASK-1",
            summary="Task 1",
            status="To Do",
            issue_type="Task",
            project_key="TEST",
            assignee=None,
            priority="Low",
        ),
    ]

    # Setup mocks
    mock_client_instance = MagicMock()
    mock_client_instance.search_issues.return_value = [epic_issue]
    mock_client_instance.get_epic_issues.return_value = child_issues
    mock_jira_client.from_connection.return_value = mock_client_instance

    # Run command
    result = runner.invoke(app, ["--format", "json", "epic", "show", "EPIC-2"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    # Check epic data (no timetracking field when no time tracking data)
    assert output["epic"]["key"] == "EPIC-2"
    assert "timetracking" not in output["epic"]

    # Check story (no timetracking field)
    assert len(output["stories"]) == 1
    assert output["stories"][0]["key"] == "TASK-1"
    assert "timetracking" not in output["stories"][0]


def test_epic_show_json_empty_stories(mock_get_active_connection, mock_jira_client):
    """Test epic show JSON output with no child stories."""
    # Mock epic with no children
    epic_issue = Issue(
        key="EPIC-3",
        summary="Empty Epic",
        status="To Do",
        issue_type="Epic",
        project_key="TEST",
    )

    # Setup mocks
    mock_client_instance = MagicMock()
    mock_client_instance.search_issues.return_value = [epic_issue]
    mock_client_instance.get_epic_issues.return_value = []
    mock_jira_client.from_connection.return_value = mock_client_instance

    # Run command
    result = runner.invoke(app, ["--format", "json", "epic", "show", "EPIC-3"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)

    # Check epic data
    assert output["epic"]["key"] == "EPIC-3"

    # Check empty stories array
    assert output["stories"] == []

    # Check progress data
    assert output["progress"]["total_issues"] == 0
    assert output["progress"]["done_issues"] == 0
    assert output["progress"]["progress_percent"] == 0


def test_epic_show_json_epic_not_found(mock_get_active_connection, mock_jira_client):
    """Test epic show JSON output when epic is not found."""
    # Setup mocks - return empty list (epic not found)
    mock_client_instance = MagicMock()
    mock_client_instance.search_issues.return_value = []
    mock_jira_client.from_connection.return_value = mock_client_instance

    # Run command
    result = runner.invoke(app, ["--format", "json", "epic", "show", "NOTFOUND-1"])

    assert result.exit_code == 1

    # Parse JSON output (should show error)
    output = json.loads(result.stdout)
    assert "error" in output
    assert output["error"] == "Epic not found"
    assert output["epic_key"] == "NOTFOUND-1"


def test_epic_show_table_output_regression(mock_get_active_connection, mock_jira_client):
    """Test that table output still works (regression test)."""
    # Mock epic and child issues
    epic_issue = Issue(
        key="EPIC-4",
        summary="Test Epic for Table",
        status="In Progress",
        issue_type="Epic",
        project_key="TEST",
    )

    child_issues = [
        Issue(
            key="STORY-3",
            summary="Story 3",
            status="Done",
            issue_type="Story",
            project_key="TEST",
            assignee="Test User",
        ),
    ]

    # Setup mocks
    mock_client_instance = MagicMock()
    mock_client_instance.search_issues.return_value = [epic_issue]
    mock_client_instance.get_epic_issues.return_value = child_issues
    mock_jira_client.from_connection.return_value = mock_client_instance

    # Run command WITHOUT --format json (default table output)
    result = runner.invoke(app, ["-q", "epic", "show", "EPIC-4"])

    assert result.exit_code == 0

    # Check table output contains key elements
    assert "EPIC-4" in result.stdout
    assert "Test Epic for Table" in result.stdout
    assert "STORY-3" in result.stdout
    assert "Story 3" in result.stdout
    assert "Status:" in result.stdout or "status" in result.stdout.lower()
    assert "Progress:" in result.stdout or "progress" in result.stdout.lower()


def test_epic_show_time_formatting():
    """Test time formatting helper function."""
    from budjira.cli.epic import _format_time_seconds

    # Test various time formats
    assert _format_time_seconds(None) is None
    assert _format_time_seconds(0) == "0m"
    assert _format_time_seconds(60) == "1m"
    assert _format_time_seconds(3600) == "1h"
    assert _format_time_seconds(3660) == "1h 1m"
    assert _format_time_seconds(7200) == "2h"
    assert _format_time_seconds(5400) == "1h 30m"
    assert _format_time_seconds(90) == "1m"  # 1.5 minutes rounds down to 1m
