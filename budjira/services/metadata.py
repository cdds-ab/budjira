"""Metadata service for fetching Jira instance metadata (projects, issue types, etc.)."""

from __future__ import annotations

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
