"""Metadata service for fetching Jira instance metadata (projects, issue types, etc.)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from budjira.models.project_metadata import (
    FieldMetadata,
    IssueTypeMetadata,
    ProjectMetadata,
)
from budjira.services.base import BaseJiraService
from budjira.utils.errors import JiraAPIError


class MetadataService(BaseJiraService):
    """Service for fetching Jira instance metadata."""

    def get_projects(self) -> list[dict[str, str]]:
        """Get list of accessible projects.

        Returns:
            List of project dictionaries with 'key' and 'name'

        Raises:
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch projects")
            projects = self.client.projects()
            return [{"key": p.key, "name": p.name} for p in projects]
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch projects: {e}") from e

    def get_issue_types(self, project_key: str | None = None) -> list[str]:
        """Get available issue types for a project.

        Args:
            project_key: Project key (optional, if None returns all issue types)

        Returns:
            List of issue type names

        Raises:
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch issue types", project_key=project_key or "all")
            issue_types = self.client.issue_types()
            return [it.name for it in issue_types]
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch issue types: {e}") from e

    def get_priorities(self) -> list[str]:
        """Get available priority levels.

        Returns:
            List of priority names

        Raises:
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch priorities")
            priorities = self.client.priorities()
            return [p.name for p in priorities]
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch priorities: {e}") from e

    def get_users(self, query: str) -> list[dict[str, str]]:
        """Search for users by name or email.

        Args:
            query: Search query (name or email fragment)

        Returns:
            List of user dictionaries with 'accountId', 'displayName', 'emailAddress'

        Raises:
            JiraAPIError: If search fails
        """
        try:
            self._log_operation("Search users", query=query)
            users = self.client.search_users(query)
            return [
                {
                    "accountId": u.accountId if hasattr(u, "accountId") else "",
                    "displayName": u.displayName if hasattr(u, "displayName") else "Unknown",
                    "emailAddress": u.emailAddress if hasattr(u, "emailAddress") else "",
                }
                for u in users
            ]
        except Exception as e:
            raise JiraAPIError(f"Failed to search users: {e}") from e

    def fetch_project_metadata(self, project_key: str) -> ProjectMetadata:
        """Fetch comprehensive project metadata from Jira API.

        Combines data from createmeta, priorities, and project endpoints
        into a single ProjectMetadata model.

        Args:
            project_key: Jira project key (e.g., 'PROJ')

        Returns:
            ProjectMetadata with issue types, priorities, and components

        Raises:
            JiraAPIError: If fetching fails
        """
        try:
            self._log_operation("Fetch project metadata", project_key=project_key)

            # Fetch issue types with fields via createmeta
            issue_types = self._fetch_createmeta(project_key)

            # Fetch priorities
            priorities = self.get_priorities()

            # Fetch project info (name, components)
            project_name, components = self._fetch_project_info(project_key)

            return ProjectMetadata(
                project_key=project_key,
                project_name=project_name,
                issue_types=issue_types,
                priorities=priorities,
                components=components,
                fetched_at=datetime.now(tz=timezone.utc),
            )
        except JiraAPIError:
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch project metadata for '{project_key}': {e}") from e

    def _fetch_createmeta(self, project_key: str) -> list[IssueTypeMetadata]:
        """Fetch issue types and their fields via createmeta endpoint.

        Args:
            project_key: Jira project key

        Returns:
            List of IssueTypeMetadata with field information
        """
        try:
            meta = self.client.createmeta(
                projectKeys=project_key,
                expand="projects.issuetypes.fields",
            )
        except Exception as e:
            self._logger.warning(f"createmeta failed for {project_key}: {e}")
            return []

        issue_types: list[IssueTypeMetadata] = []
        projects = meta.get("projects", []) if isinstance(meta, dict) else []

        for project in projects:
            for it in project.get("issuetypes", []):
                fields = self._parse_createmeta_fields(it.get("fields", {}))
                issue_types.append(
                    IssueTypeMetadata(
                        id=str(it.get("id", "")),
                        name=it.get("name", ""),
                        description=it.get("description", ""),
                        subtask=it.get("subtask", False),
                        fields=fields,
                    )
                )

        return issue_types

    def _parse_createmeta_fields(self, fields_dict: dict[str, Any]) -> list[FieldMetadata]:
        """Parse createmeta fields into FieldMetadata objects.

        Args:
            fields_dict: Fields dictionary from createmeta response

        Returns:
            List of FieldMetadata objects
        """
        result: list[FieldMetadata] = []
        for field_id, field_data in fields_dict.items():
            if not isinstance(field_data, dict):
                continue

            allowed_values: list[str] = []
            for av in field_data.get("allowedValues", []):
                if isinstance(av, dict):
                    name = av.get("name") or av.get("value") or ""
                    if name:
                        allowed_values.append(str(name))

            schema = field_data.get("schema", {})
            schema_type = schema.get("type", "string") if isinstance(schema, dict) else "string"

            result.append(
                FieldMetadata(
                    field_id=field_id,
                    name=field_data.get("name", field_id),
                    required=field_data.get("required", False),
                    schema_type=str(schema_type),
                    allowed_values=allowed_values,
                )
            )
        return result

    def _fetch_project_info(self, project_key: str) -> tuple[str, list[str]]:
        """Fetch project name and components.

        Args:
            project_key: Jira project key

        Returns:
            Tuple of (project_name, component_names)
        """
        try:
            project = self.client.project(project_key)
            project_name = getattr(project, "name", project_key)
            components: list[str] = []
            if hasattr(project, "components"):
                components = [getattr(c, "name", "") for c in project.components if getattr(c, "name", "")]
            return str(project_name), components
        except Exception as e:
            self._logger.warning(f"Failed to fetch project info for {project_key}: {e}")
            return project_key, []
