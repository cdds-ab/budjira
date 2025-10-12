"""Data models for Jira issues."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    """Jira issue types."""

    BUG = "Bug"
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"
    SUBTASK = "Sub-task"


class Priority(str, Enum):
    """Jira priority levels."""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class Status(BaseModel):
    """Jira issue status."""

    name: str = Field(..., description="Status name (e.g., 'To Do', 'In Progress')")
    category: str | None = Field(None, description="Status category")


class User(BaseModel):
    """Jira user information."""

    name: str = Field(..., description="Username")
    display_name: str = Field(..., description="Display name")
    email: str | None = Field(None, description="Email address")


class Issue(BaseModel):
    """Jira issue model."""

    key: str = Field(..., description="Issue key (e.g., PROJ-123)")
    summary: str = Field(..., description="Issue summary/title")
    description: str | None = Field(None, description="Issue description")
    issue_type: str = Field(..., description="Issue type")
    status: str = Field(..., description="Current status")
    priority: str | None = Field(None, description="Priority level")
    assignee: str | None = Field(None, description="Assigned user display name")
    reporter: str | None = Field(None, description="Reporter display name")
    created: datetime | None = Field(None, description="Creation timestamp")
    updated: datetime | None = Field(None, description="Last update timestamp")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    components: list[str] = Field(default_factory=list, description="Issue components")
    project_key: str = Field(..., description="Project key")

    @staticmethod
    def _parse_jira_datetime(datetime_str: str) -> datetime:
        """Parse Jira datetime string to datetime object.

        Handles multiple Jira datetime formats:
        - 2025-01-10T10:00:00.000Z
        - 2025-01-10T10:00:00.000+0000 (without colon)
        - 2025-01-10T10:00:00.000+00:00 (with colon)

        Args:
            datetime_str: Datetime string from Jira API

        Returns:
            Parsed datetime object
        """
        # Replace Z with +00:00 for ISO format
        normalized = datetime_str.replace("Z", "+00:00")

        # Fix timezone format: +0000 -> +00:00
        if normalized.endswith("+0000") or normalized.endswith("-0000"):
            normalized = normalized[:-5] + normalized[-5:-2] + ":" + normalized[-2:]

        return datetime.fromisoformat(normalized)

    @classmethod
    def from_jira_issue(cls, jira_issue: Any) -> Issue:
        """Create Issue from jira library Issue object.

        Args:
            jira_issue: Issue object from jira library

        Returns:
            Issue model instance
        """
        fields = jira_issue.fields

        # Parse assignee
        assignee = None
        if hasattr(fields, "assignee") and fields.assignee:
            assignee = fields.assignee.displayName

        # Parse reporter
        reporter = None
        if hasattr(fields, "reporter") and fields.reporter:
            reporter = fields.reporter.displayName

        # Parse timestamps
        created = None
        if hasattr(fields, "created") and fields.created:
            created = cls._parse_jira_datetime(fields.created)

        updated = None
        if hasattr(fields, "updated") and fields.updated:
            updated = cls._parse_jira_datetime(fields.updated)

        # Parse labels
        labels = []
        if hasattr(fields, "labels") and fields.labels:
            labels = list(fields.labels)

        # Parse components
        components = []
        if hasattr(fields, "components") and fields.components:
            components = [comp.name for comp in fields.components]

        # Parse priority
        priority = None
        if hasattr(fields, "priority") and fields.priority:
            priority = fields.priority.name

        return cls(
            key=jira_issue.key,
            summary=fields.summary,
            description=fields.description if hasattr(fields, "description") else None,
            issue_type=fields.issuetype.name,
            status=fields.status.name,
            priority=priority,
            assignee=assignee,
            reporter=reporter,
            created=created,
            updated=updated,
            labels=labels,
            components=components,
            project_key=jira_issue.key.split("-")[0],
        )


class WorkLog(BaseModel):
    """Work log entry for time tracking."""

    issue_key: str = Field(..., description="Issue key")
    time_spent_minutes: int = Field(..., description="Time spent in minutes", gt=0)
    comment: str | None = Field(None, description="Work log comment")
    started: datetime | None = Field(None, description="When work started")
