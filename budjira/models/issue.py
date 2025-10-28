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


class Comment(BaseModel):
    """Jira issue comment."""

    author: str = Field(..., description="Comment author display name")
    body: str = Field(..., description="Comment body/text")
    created: datetime | None = Field(None, description="Comment creation timestamp")
    updated: datetime | None = Field(None, description="Comment update timestamp")


class Attachment(BaseModel):
    """Jira issue attachment."""

    filename: str = Field(..., description="Attachment filename")
    size: int = Field(..., description="File size in bytes")
    mime_type: str | None = Field(None, description="MIME type")
    created: datetime | None = Field(None, description="Upload timestamp")
    author: str | None = Field(None, description="Uploader display name")


class Issue(BaseModel):
    """Jira issue model."""

    key: str = Field(..., description="Issue key (e.g., PROJ-123)")
    summary: str = Field(..., description="Issue summary/title")
    description: str | None = Field(default=None, description="Issue description")
    issue_type: str = Field(..., description="Issue type")
    status: str = Field(..., description="Current status")
    priority: str | None = Field(default=None, description="Priority level")
    assignee: str | None = Field(default=None, description="Assigned user display name")
    reporter: str | None = Field(default=None, description="Reporter display name")
    created: datetime | None = Field(default=None, description="Creation timestamp")
    updated: datetime | None = Field(default=None, description="Last update timestamp")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    components: list[str] = Field(default_factory=list, description="Issue components")
    project_key: str = Field(..., description="Project key")

    # Epic information
    epic_key: str | None = Field(default=None, description="Parent epic key")
    epic_name: str | None = Field(default=None, description="Parent epic name")

    # Time tracking (all in seconds)
    time_original_estimate: int | None = Field(default=None, description="Original time estimate in seconds")
    time_remaining_estimate: int | None = Field(default=None, description="Remaining time estimate in seconds")
    time_spent: int | None = Field(default=None, description="Time spent in seconds")

    # Comments and attachments
    comments: list[Comment] = Field(default_factory=list, description="Issue comments")
    attachments: list[Attachment] = Field(default_factory=list, description="Issue attachments")

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
    def from_jira_issue(cls, jira_issue: Any, epic_info: tuple[str, str] | None = None) -> Issue:
        """Create Issue from jira library Issue object.

        Args:
            jira_issue: Issue object from jira library
            epic_info: Optional tuple of (epic_key, epic_name)

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

        # Parse epic info
        epic_key = None
        epic_name = None
        if epic_info:
            epic_key, epic_name = epic_info

        # Parse time tracking
        time_original_estimate = None
        time_remaining_estimate = None
        time_spent = None
        if hasattr(fields, "timetracking") and fields.timetracking:
            if hasattr(fields.timetracking, "originalEstimateSeconds"):
                time_original_estimate = fields.timetracking.originalEstimateSeconds
            if hasattr(fields.timetracking, "remainingEstimateSeconds"):
                time_remaining_estimate = fields.timetracking.remainingEstimateSeconds
            if hasattr(fields.timetracking, "timeSpentSeconds"):
                time_spent = fields.timetracking.timeSpentSeconds

        # Parse comments
        comments = []
        if hasattr(fields, "comment") and fields.comment and hasattr(fields.comment, "comments"):
            for c in fields.comment.comments:
                comment_created = None
                if hasattr(c, "created") and c.created:
                    comment_created = cls._parse_jira_datetime(c.created)

                comment_updated = None
                if hasattr(c, "updated") and c.updated:
                    comment_updated = cls._parse_jira_datetime(c.updated)

                comments.append(
                    Comment(
                        author=c.author.displayName if hasattr(c, "author") and c.author else "Unknown",
                        body=c.body if hasattr(c, "body") else "",
                        created=comment_created,
                        updated=comment_updated,
                    )
                )

        # Parse attachments
        attachments = []
        if hasattr(fields, "attachment") and fields.attachment:
            for att in fields.attachment:
                att_created = None
                if hasattr(att, "created") and att.created:
                    att_created = cls._parse_jira_datetime(att.created)

                attachments.append(
                    Attachment(
                        filename=att.filename if hasattr(att, "filename") else "unknown",
                        size=att.size if hasattr(att, "size") else 0,
                        mime_type=att.mimeType if hasattr(att, "mimeType") else None,
                        created=att_created,
                        author=att.author.displayName if hasattr(att, "author") and att.author else None,
                    )
                )

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
            epic_key=epic_key,
            epic_name=epic_name,
            time_original_estimate=time_original_estimate,
            time_remaining_estimate=time_remaining_estimate,
            time_spent=time_spent,
            comments=comments,
            attachments=attachments,
        )


class WorkLog(BaseModel):
    """Work log entry for time tracking."""

    issue_key: str = Field(..., description="Issue key")
    time_spent_minutes: int = Field(..., description="Time spent in minutes", gt=0)
    comment: str | None = Field(None, description="Work log comment")
    started: datetime | None = Field(None, description="When work started")
