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


class IssueLink(BaseModel):
    """Jira issue link."""

    link_id: str = Field(..., description="Link ID for deletion")
    link_type: str = Field(..., description="Link type name")
    direction: str = Field(..., description="'outward' or 'inward'")
    issue_key: str = Field(..., description="Linked issue key")
    issue_summary: str | None = Field(None, description="Linked issue summary")


class Issue(BaseModel):
    """Jira issue model."""

    id: int | None = Field(default=None, description="Internal Jira issue ID")
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

    # Issue links
    issuelinks: list[IssueLink] = Field(default_factory=list, description="Issue links")

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
    def _parse_basic_fields(cls, jira_issue: Any, fields: Any) -> dict[str, Any]:
        """Extract basic issue fields (key, summary, description, type, status).

        Args:
            jira_issue: Issue object from jira library
            fields: Issue fields object

        Returns:
            Dictionary with basic field values
        """
        issue_id = int(jira_issue.id) if hasattr(jira_issue, "id") and jira_issue.id is not None else None
        # Guard every field access: a partial fetch (e.g. fields=["summary"]) returns a
        # PropertyHolder that only carries the requested fields, so issuetype/status may be
        # absent. Unguarded access raised "'PropertyHolder' object has no attribute ...".
        return {
            "id": issue_id,
            "key": jira_issue.key,
            "summary": getattr(fields, "summary", "") or "",
            "description": fields.description if hasattr(fields, "description") else None,
            "issue_type": fields.issuetype.name if getattr(fields, "issuetype", None) else "",
            "status": fields.status.name if getattr(fields, "status", None) else "",
            "project_key": jira_issue.key.split("-")[0],
        }

    @classmethod
    def _parse_user_fields(cls, fields: Any) -> dict[str, Any]:
        """Extract user-related fields (assignee, reporter).

        Args:
            fields: Issue fields object

        Returns:
            Dictionary with user field values
        """
        assignee = None
        if hasattr(fields, "assignee") and fields.assignee:
            assignee = fields.assignee.displayName

        reporter = None
        if hasattr(fields, "reporter") and fields.reporter:
            reporter = fields.reporter.displayName

        return {"assignee": assignee, "reporter": reporter}

    @classmethod
    def _parse_timestamp_fields(cls, fields: Any) -> dict[str, Any]:
        """Extract timestamp fields (created, updated).

        Args:
            fields: Issue fields object

        Returns:
            Dictionary with timestamp values
        """
        created = None
        if hasattr(fields, "created") and fields.created:
            created = cls._parse_jira_datetime(fields.created)

        updated = None
        if hasattr(fields, "updated") and fields.updated:
            updated = cls._parse_jira_datetime(fields.updated)

        return {"created": created, "updated": updated}

    @classmethod
    def _parse_metadata_fields(cls, fields: Any) -> dict[str, Any]:
        """Extract metadata fields (priority, labels, components).

        Args:
            fields: Issue fields object

        Returns:
            Dictionary with metadata values
        """
        priority = None
        if hasattr(fields, "priority") and fields.priority:
            priority = fields.priority.name

        labels = []
        if hasattr(fields, "labels") and fields.labels:
            labels = list(fields.labels)

        components = []
        if hasattr(fields, "components") and fields.components:
            components = [comp.name for comp in fields.components]

        return {"priority": priority, "labels": labels, "components": components}

    @classmethod
    def _parse_epic_fields(cls, epic_info: tuple[str, str] | None) -> dict[str, Any]:
        """Extract epic information.

        Args:
            epic_info: Optional tuple of (epic_key, epic_name)

        Returns:
            Dictionary with epic values
        """
        epic_key = None
        epic_name = None
        if epic_info:
            epic_key, epic_name = epic_info

        return {"epic_key": epic_key, "epic_name": epic_name}

    @classmethod
    def _parse_time_tracking_fields(cls, fields: Any) -> dict[str, Any]:
        """Extract time tracking fields.

        Args:
            fields: Issue fields object

        Returns:
            Dictionary with time tracking values
        """
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

        return {
            "time_original_estimate": time_original_estimate,
            "time_remaining_estimate": time_remaining_estimate,
            "time_spent": time_spent,
        }

    @classmethod
    def _parse_comments(cls, fields: Any) -> list[Comment]:
        """Extract and parse comments.

        Args:
            fields: Issue fields object

        Returns:
            List of Comment objects
        """
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

        return comments

    @classmethod
    def _parse_attachments(cls, fields: Any) -> list[Attachment]:
        """Extract and parse attachments.

        Args:
            fields: Issue fields object

        Returns:
            List of Attachment objects
        """
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

        return attachments

    @classmethod
    def _parse_issue_links(cls, issue_links: list[Any]) -> list[IssueLink]:
        """Extract and parse issue links.

        Args:
            issue_links: List of issue link objects from Jira API

        Returns:
            List of IssueLink objects
        """
        links = []
        for link in issue_links:
            link_id = link.id if hasattr(link, "id") else ""
            link_type = link.type.name if hasattr(link, "type") and hasattr(link.type, "name") else "Unknown"

            # Check for outward link (this issue -> other issue)
            if hasattr(link, "outwardIssue"):
                issue_key = link.outwardIssue.key
                issue_summary = None
                if hasattr(link.outwardIssue, "fields") and hasattr(link.outwardIssue.fields, "summary"):
                    issue_summary = link.outwardIssue.fields.summary

                links.append(
                    IssueLink(
                        link_id=link_id,
                        link_type=link_type,
                        direction="outward",
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    )
                )

            # Check for inward link (other issue -> this issue)
            if hasattr(link, "inwardIssue"):
                issue_key = link.inwardIssue.key
                issue_summary = None
                if hasattr(link.inwardIssue, "fields") and hasattr(link.inwardIssue.fields, "summary"):
                    issue_summary = link.inwardIssue.fields.summary

                links.append(
                    IssueLink(
                        link_id=link_id,
                        link_type=link_type,
                        direction="inward",
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                    )
                )

        return links

    @classmethod
    def from_jira_issue(cls, jira_issue: Any, epic_info: tuple[str, str] | None = None) -> Issue:
        """Create Issue from jira library Issue object.

        This method orchestrates parsing of all Jira fields by delegating
        to specialized parser methods. Each parser handles a specific domain.

        Args:
            jira_issue: Issue object from jira library
            epic_info: Optional tuple of (epic_key, epic_name)

        Returns:
            Issue model instance
        """
        fields = jira_issue.fields

        # Parse all field groups using specialized parsers
        basic = cls._parse_basic_fields(jira_issue, fields)
        users = cls._parse_user_fields(fields)
        timestamps = cls._parse_timestamp_fields(fields)
        metadata = cls._parse_metadata_fields(fields)
        epic = cls._parse_epic_fields(epic_info)
        time_tracking = cls._parse_time_tracking_fields(fields)
        comments = cls._parse_comments(fields)
        attachments = cls._parse_attachments(fields)

        # Parse issue links
        issue_links = []
        if hasattr(fields, "issuelinks") and fields.issuelinks:
            issue_links = cls._parse_issue_links(fields.issuelinks)

        # Combine all parsed data
        return cls(
            **basic,
            **users,
            **timestamps,
            **metadata,
            **epic,
            **time_tracking,
            comments=comments,
            attachments=attachments,
            issuelinks=issue_links,
        )


class WorkLog(BaseModel):
    """Work log entry for time tracking."""

    issue_key: str = Field(..., description="Issue key")
    time_spent_minutes: int = Field(..., description="Time spent in minutes", gt=0)
    comment: str | None = Field(None, description="Work log comment")
    started: datetime | None = Field(None, description="When work started")
