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
            created = datetime.fromisoformat(fields.created.replace("Z", "+00:00"))

        updated = None
        if hasattr(fields, "updated") and fields.updated:
            updated = datetime.fromisoformat(fields.updated.replace("Z", "+00:00"))

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
