# mypy: disable-error-code="call-arg,arg-type"
"""Tests for issue models."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from budjira.models.issue import Issue, IssueLink, IssueType, Priority, Status, User, WorkLog
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


class TestIssueLink:
    """Test IssueLink model."""

    def test_create_issue_link(self) -> None:
        """Test issue link creation."""
        link = IssueLink(
            link_id="10001",
            link_type="Relates",
            direction="outward",
            issue_key="PROJ-456",
            issue_summary="Related issue",
        )
        assert link.link_id == "10001"
        assert link.link_type == "Relates"
        assert link.direction == "outward"
        assert link.issue_key == "PROJ-456"
        assert link.issue_summary == "Related issue"

    def test_create_issue_link_without_summary(self) -> None:
        """Test issue link without summary."""
        link = IssueLink(
            link_id="10002",
            link_type="Blocks",
            direction="inward",
            issue_key="PROJ-789",
        )
        assert link.link_id == "10002"
        assert link.issue_summary is None

    def test_issue_link_validation(self) -> None:
        """Test issue link validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            IssueLink(link_id="10001")

        with pytest.raises(ValidationError):
            IssueLink(link_type="Relates", direction="outward")


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

    def test_create_issue_with_id(self) -> None:
        """Test issue creation with internal Jira ID."""
        issue = Issue(
            id=12345,
            key="PROJ-123",
            summary="Test issue with ID",
            issue_type="Bug",
            status="To Do",
            project_key="PROJ",
        )
        assert issue.id == 12345

    def test_create_issue_id_defaults_to_none(self) -> None:
        """Test that issue id defaults to None."""
        issue = Issue(
            key="PROJ-123",
            summary="Test issue",
            issue_type="Bug",
            status="To Do",
            project_key="PROJ",
        )
        assert issue.id is None

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

    def test_from_jira_issue_populates_id(self) -> None:
        """Test that from_jira_issue populates internal Jira ID."""
        jira_issue = MagicMock()
        jira_issue.id = "67890"
        jira_issue.key = "TEST-789"
        jira_issue.fields.summary = "Test"
        jira_issue.fields.issuetype.name = "Task"
        jira_issue.fields.status.name = "Open"
        jira_issue.fields.assignee = None
        jira_issue.fields.reporter = None
        jira_issue.fields.priority = None
        jira_issue.fields.created = None
        jira_issue.fields.updated = None
        jira_issue.fields.labels = []
        jira_issue.fields.components = []
        del jira_issue.fields.description

        issue = Issue.from_jira_issue(jira_issue)
        assert issue.id == 67890

    def test_from_jira_issue_id_none_when_missing(self) -> None:
        """Test that from_jira_issue handles missing id gracefully."""
        jira_issue = MagicMock()
        jira_issue.id = None
        jira_issue.key = "TEST-789"
        jira_issue.fields.summary = "Test"
        jira_issue.fields.issuetype.name = "Task"
        jira_issue.fields.status.name = "Open"
        jira_issue.fields.assignee = None
        jira_issue.fields.reporter = None
        jira_issue.fields.priority = None
        jira_issue.fields.created = None
        jira_issue.fields.updated = None
        jira_issue.fields.labels = []
        jira_issue.fields.components = []
        del jira_issue.fields.description

        issue = Issue.from_jira_issue(jira_issue)
        assert issue.id is None

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

    def test_from_jira_issue_partial_fields_summary_only(self) -> None:
        """A partial fetch (fields=["summary"]) must not crash on absent fields (#89).

        Regression: `issue delete` fetched fields=["summary"], yielding a PropertyHolder
        without issuetype/status. Unguarded access raised
        "'PropertyHolder' object has no attribute 'issuetype'".
        """
        import types

        # SimpleNamespace raises AttributeError on missing attrs, like jira's PropertyHolder.
        fields = types.SimpleNamespace(summary="Only the title")
        jira_issue = types.SimpleNamespace(id="123", key="PROJ-7", fields=fields)

        issue = Issue.from_jira_issue(jira_issue)

        assert issue.key == "PROJ-7"
        assert issue.summary == "Only the title"
        assert issue.issue_type == ""
        assert issue.status == ""
        assert issue.priority is None
        assert issue.assignee is None

    def test_parse_issue_links_outward(self) -> None:
        """Test parsing issue links with outward direction."""
        # Mock Jira API response for outward link
        link_data = MagicMock()
        link_data.id = "10001"
        link_data.type.name = "Relates"
        link_data.type.outward = "relates to"
        link_data.type.inward = "relates to"
        link_data.outwardIssue.key = "PROJ-456"
        link_data.outwardIssue.fields.summary = "Related issue"
        # No inwardIssue
        delattr(link_data, "inwardIssue")

        links = Issue._parse_issue_links([link_data])

        assert len(links) == 1
        assert links[0].link_id == "10001"
        assert links[0].link_type == "Relates"
        assert links[0].direction == "outward"
        assert links[0].issue_key == "PROJ-456"
        assert links[0].issue_summary == "Related issue"

    def test_parse_issue_links_inward(self) -> None:
        """Test parsing issue links with inward direction."""
        # Mock Jira API response for inward link
        link_data = MagicMock()
        link_data.id = "10002"
        link_data.type.name = "Blocks"
        link_data.type.outward = "blocks"
        link_data.type.inward = "is blocked by"
        link_data.inwardIssue.key = "PROJ-789"
        link_data.inwardIssue.fields.summary = "Blocking issue"
        # No outwardIssue
        delattr(link_data, "outwardIssue")

        links = Issue._parse_issue_links([link_data])

        assert len(links) == 1
        assert links[0].link_id == "10002"
        assert links[0].link_type == "Blocks"
        assert links[0].direction == "inward"
        assert links[0].issue_key == "PROJ-789"
        assert links[0].issue_summary == "Blocking issue"

    def test_parse_issue_links_multiple(self) -> None:
        """Test parsing multiple issue links."""
        # Mock outward link
        link1 = MagicMock()
        link1.id = "10001"
        link1.type.name = "Relates"
        link1.outwardIssue.key = "PROJ-100"
        link1.outwardIssue.fields.summary = "First link"
        delattr(link1, "inwardIssue")

        # Mock inward link
        link2 = MagicMock()
        link2.id = "10002"
        link2.type.name = "Blocks"
        link2.inwardIssue.key = "PROJ-200"
        link2.inwardIssue.fields.summary = "Second link"
        delattr(link2, "outwardIssue")

        links = Issue._parse_issue_links([link1, link2])

        assert len(links) == 2
        assert links[0].issue_key == "PROJ-100"
        assert links[1].issue_key == "PROJ-200"

    def test_parse_issue_links_no_links(self) -> None:
        """Test parsing with no issue links."""
        links = Issue._parse_issue_links([])
        assert links == []

    def test_parse_issue_links_no_summary(self) -> None:
        """Test parsing issue links without summary."""
        link_data = MagicMock()
        link_data.id = "10003"
        link_data.type.name = "Relates"
        link_data.outwardIssue.key = "PROJ-999"
        # No summary field
        delattr(link_data.outwardIssue.fields, "summary")
        delattr(link_data, "inwardIssue")

        links = Issue._parse_issue_links([link_data])

        assert len(links) == 1
        assert links[0].issue_summary is None


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
