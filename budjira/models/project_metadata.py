"""Data models for Jira project metadata (issue types, priorities, components)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class FieldMetadata(BaseModel):
    """Metadata for a single Jira field within an issue type."""

    field_id: str = Field(..., description="Jira field ID (e.g., 'customfield_10001')")
    name: str = Field(..., description="Human-readable field name (e.g., 'Story Points')")
    required: bool = Field(default=False, description="Whether the field is required for issue creation")
    schema_type: str = Field(default="string", description="Field schema type (e.g., 'string', 'number', 'option')")
    allowed_values: list[str] = Field(default_factory=list, description="Allowed values for select/option fields")


class IssueTypeMetadata(BaseModel):
    """Metadata for a single Jira issue type."""

    id: str = Field(..., description="Issue type ID")
    name: str = Field(..., description="Issue type name (e.g., 'Change Request')")
    description: str = Field(default="", description="Issue type description")
    subtask: bool = Field(default=False, description="Whether this is a subtask type")
    fields: list[FieldMetadata] = Field(default_factory=list, description="Fields available for this issue type")


class ProjectMetadata(BaseModel):
    """Cached metadata for a Jira project."""

    project_key: str = Field(..., description="Jira project key (e.g., 'PROJ')")
    project_name: str = Field(..., description="Jira project name")
    issue_types: list[IssueTypeMetadata] = Field(default_factory=list, description="Available issue types")
    priorities: list[str] = Field(default_factory=list, description="Available priority names")
    components: list[str] = Field(default_factory=list, description="Available component names")
    fetched_at: datetime = Field(..., description="Timestamp when metadata was fetched")

    def get_issue_type_names(self) -> list[str]:
        """Get list of issue type names.

        Returns:
            List of issue type name strings
        """
        return [it.name for it in self.issue_types]

    def get_required_fields(self, issue_type: str) -> list[FieldMetadata]:
        """Get required fields for a specific issue type.

        Args:
            issue_type: Name of the issue type

        Returns:
            List of required FieldMetadata objects, empty if issue type not found
        """
        for it in self.issue_types:
            if it.name == issue_type:
                return [f for f in it.fields if f.required]
        return []

    def is_stale(self, ttl_hours: int) -> bool:
        """Check if metadata is older than the given TTL.

        Args:
            ttl_hours: Time-to-live in hours

        Returns:
            True if metadata is stale and should be refreshed
        """
        now = datetime.now(tz=timezone.utc)
        fetched = self.fetched_at.replace(tzinfo=timezone.utc) if self.fetched_at.tzinfo is None else self.fetched_at
        age_hours = (now - fetched).total_seconds() / 3600
        return age_hours > ttl_hours
