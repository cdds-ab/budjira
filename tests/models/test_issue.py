# mypy: disable-error-code="call-arg,arg-type"
"""Tests for issue models."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from budjira.models.issue import Issue, IssueType, Priority, Status, User, WorkLog
from pydantic import ValidationError


class TestIssueType:
    """Test IssueType enum."""

    def test_issue_types(self) -> None:
        """Test issue type values."""
        assert IssueType.BUG.value == "Bug"
        assert IssueType.TASK.value == "Task"
        assert IssueType.STORY.value == "Story"
        assert IssueType.EPIC.value == "Epic"
        assert IssueType.SUBTASK.value == "Sub-task"


class TestPriority:
    """Test Priority enum."""

    def test_priorities(self) -> None:
        """Test priority values."""
        assert Priority.HIGHEST.value == "Highest"
        assert Priority.HIGH.value == "High"
        assert Priority.MEDIUM.value == "Medium"
        assert Priority.LOW.value == "Low"
        assert Priority.LOWEST.value == "Lowest"


class TestStatus:
    """Test Status model."""

    def test_create_status(self) -> None:
        """Test status creation."""
        status = Status(name="In Progress", category="indeterminate")
        assert status.name == "In Progress"
        assert status.category == "indeterminate"

    def test_create_status_without_category(self) -> None:
        """Test status without category."""
        status = Status(name="Done")
        assert status.name == "Done"
        assert status.category is None


class TestUser:
    """Test User model."""

    def test_create_user(self) -> None:
        """Test user creation."""
        user = User(name="jdoe", display_name="John Doe", email="john.doe@example.com")
        assert user.name == "jdoe"
        assert user.display_name == "John Doe"
        assert user.email == "john.doe@example.com"

    def test_create_user_without_email(self) -> None:
        """Test user without email."""
        user = User(name="jdoe", display_name="John Doe")
        assert user.name == "jdoe"
        assert user.email is None


class TestIssue:
    """Test Issue model."""

    def test_create_issue(self) -> None:
        """Test issue creation."""
        issue = Issue(
            key="PROJ-123",
            summary="Test issue",
            description="Test description",
            issue_type="Bug",
            status="To Do",
            priority="High",
            assignee="John Doe",
            reporter="Jane Smith",
            project_key="PROJ",
        )
        assert issue.key == "PROJ-123"
        assert issue.summary == "Test issue"
        assert issue.issue_type == "Bug"
        assert issue.status == "To Do"
        assert issue.priority == "High"

    def test_create_minimal_issue(self) -> None:
        """Test issue with minimal required fields."""
        issue = Issue(
            key="PROJ-456",
            summary="Minimal issue",
            issue_type="Task",
            status="In Progress",
            project_key="PROJ",
        )
        assert issue.key == "PROJ-456"
        assert issue.description is None
        assert issue.priority is None
        assert issue.assignee is None
        assert issue.labels == []
        assert issue.components == []

    def test_from_jira_issue(self) -> None:
        """Test creating Issue from jira library issue object."""
        # Mock jira issue
        jira_issue = MagicMock()
        jira_issue.key = "TEST-789"
        jira_issue.fields.summary = "Test Summary"
        jira_issue.fields.description = "Test Description"
        jira_issue.fields.issuetype.name = "Bug"
        jira_issue.fields.status.name = "In Progress"
        jira_issue.fields.priority.name = "High"
        jira_issue.fields.assignee.displayName = "John Doe"
        jira_issue.fields.reporter.displayName = "Jane Smith"
        jira_issue.fields.created = "2025-01-10T10:00:00.000+0000"
        jira_issue.fields.updated = "2025-01-11T15:30:00.000+0000"
        jira_issue.fields.labels = ["bug", "urgent"]

        # Create proper mocks for components
        component_frontend = MagicMock()
        component_frontend.name = "Frontend"
        component_backend = MagicMock()
        component_backend.name = "Backend"
        jira_issue.fields.components = [component_frontend, component_backend]

        issue = Issue.from_jira_issue(jira_issue)

        assert issue.key == "TEST-789"
        assert issue.summary == "Test Summary"
        assert issue.description == "Test Description"
        assert issue.issue_type == "Bug"
        assert issue.status == "In Progress"
        assert issue.priority == "High"
        assert issue.assignee == "John Doe"
        assert issue.reporter == "Jane Smith"
        assert issue.labels == ["bug", "urgent"]
        assert issue.components == ["Frontend", "Backend"]
        assert issue.project_key == "TEST"
        assert isinstance(issue.created, datetime)
        assert isinstance(issue.updated, datetime)

    def test_from_jira_issue_minimal(self) -> None:
        """Test creating Issue from minimal jira issue."""
        jira_issue = MagicMock()
        jira_issue.key = "MIN-1"
        jira_issue.fields.summary = "Minimal"
        jira_issue.fields.issuetype.name = "Task"
        jira_issue.fields.status.name = "Open"
        jira_issue.fields.assignee = None
        jira_issue.fields.reporter = None
        jira_issue.fields.priority = None
        jira_issue.fields.created = None
        jira_issue.fields.updated = None
        jira_issue.fields.labels = []
        jira_issue.fields.components = []
        # Remove description attribute to test hasattr check
        del jira_issue.fields.description

        issue = Issue.from_jira_issue(jira_issue)

        assert issue.key == "MIN-1"
        assert issue.summary == "Minimal"
        assert issue.assignee is None
        assert issue.reporter is None
        assert issue.priority is None
        assert issue.created is None
        assert issue.updated is None


class TestWorkLog:
    """Test WorkLog model."""

    def test_create_worklog(self) -> None:
        """Test work log creation."""
        worklog = WorkLog(
            issue_key="PROJ-123",
            time_spent_minutes=120,
            comment="Fixed the bug",
            started=datetime(2025, 1, 10, 9, 0),
        )
        assert worklog.issue_key == "PROJ-123"
        assert worklog.time_spent_minutes == 120
        assert worklog.comment == "Fixed the bug"
        assert isinstance(worklog.started, datetime)

    def test_create_worklog_minimal(self) -> None:
        """Test work log with minimal fields."""
        worklog = WorkLog(issue_key="PROJ-456", time_spent_minutes=30)
        assert worklog.issue_key == "PROJ-456"
        assert worklog.time_spent_minutes == 30
        assert worklog.comment is None
        assert worklog.started is None

    def test_worklog_validation(self) -> None:
        """Test work log validation."""
        # time_spent_minutes must be positive
        with pytest.raises(ValidationError):
            WorkLog(issue_key="PROJ-1", time_spent_minutes=0)

        with pytest.raises(ValidationError):
            WorkLog(issue_key="PROJ-1", time_spent_minutes=-10)
