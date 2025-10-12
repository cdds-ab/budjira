"""Jira client wrapper around jira library."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from jira import JIRA
from jira.exceptions import JIRAError

from budjira.config.credentials import CredentialStore
from budjira.models.issue import Issue
from budjira.utils.errors import (
    AuthenticationError,
    InvalidIssueError,
    JiraAPIError,
    PermissionError,
)

if TYPE_CHECKING:
    from datetime import datetime

    from budjira.models.connection import Connection

logger = logging.getLogger(__name__)


class JiraClient:
    """Wrapper around jira library with error handling and logging."""

    def __init__(self, connection: Connection, api_token: str) -> None:
        """Initialize Jira client.

        Args:
            connection: Connection configuration
            api_token: Jira API token

        Raises:
            AuthenticationError: If authentication fails
            JiraAPIError: If connection fails
        """
        self.connection = connection
        self._client: JIRA | None = None

        try:
            logger.info(f"Connecting to Jira at {connection.url}")
            self._client = JIRA(
                server=str(connection.url),
                basic_auth=(connection.email, api_token),
                timeout=30,
            )
            logger.info("Successfully connected to Jira")
        except JIRAError as e:
            if e.status_code == 401:
                raise AuthenticationError(
                    f"Authentication failed for {connection.email}. "
                    f"Check your API token at https://id.atlassian.com/manage-profile/security/api-tokens"
                ) from e
            elif e.status_code == 403:
                raise PermissionError(f"Access denied. User {connection.email} lacks required permissions.") from e
            else:
                raise JiraAPIError(
                    f"Failed to connect to Jira: {e.text}. Check your URL and network connection."
                ) from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error connecting to Jira: {e}") from e

    @property
    def client(self) -> JIRA:
        """Get underlying JIRA client.

        Returns:
            JIRA client instance

        Raises:
            JiraAPIError: If client is not initialized
        """
        if self._client is None:
            raise JiraAPIError("Jira client not initialized")
        return self._client

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: list[str] | None = None,
    ) -> list[Issue]:
        """Search for issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fields: List of fields to retrieve (None = all fields)

        Returns:
            List of Issue objects

        Raises:
            JiraAPIError: If search fails
            PermissionError: If user lacks search permission
        """
        try:
            logger.info(f"Searching issues with JQL: {jql}")
            jira_issues = self.client.search_issues(
                jql_str=jql,
                maxResults=max_results,
                fields=fields if fields else "*all",
            )
            logger.info(f"Found {len(jira_issues)} issues")

            return [Issue.from_jira_issue(issue) for issue in jira_issues]

        except JIRAError as e:
            if e.status_code == 403:
                raise PermissionError(
                    f"Permission denied while searching. "
                    f"User {self.connection.email} may not have access to the specified project."
                ) from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid JQL query: {jql}. Error: {e.text}") from e
            else:
                raise JiraAPIError(f"Search failed: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error during search: {e}") from e

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> Issue:
        """Get a single issue by key.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: List of fields to retrieve (None = all fields)

        Returns:
            Issue object

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to view issue
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching issue: {issue_key}")
            jira_issue = self.client.issue(
                issue_key,
                fields=",".join(fields) if fields else "*all",
            )
            return Issue.from_jira_issue(jira_issue)

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(f"Permission denied accessing issue '{issue_key}'.") from e
            else:
                raise JiraAPIError(f"Failed to fetch issue '{issue_key}': {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching issue: {e}") from e

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        **extra_fields: Any,
    ) -> Issue:
        """Create a new issue.

        Args:
            project_key: Project key (e.g., PROJ)
            summary: Issue summary
            issue_type: Issue type (Bug, Task, Story, etc.)
            description: Issue description
            priority: Priority level
            assignee: Assignee username
            labels: List of labels
            **extra_fields: Additional custom fields

        Returns:
            Created Issue object

        Raises:
            ValidationError: If required fields are missing
            PermissionError: If user lacks create permission
            JiraAPIError: If creation fails
        """
        try:
            logger.info(f"Creating issue in project {project_key}: {summary}")

            fields: dict[str, Any] = {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }

            if description:
                fields["description"] = description
            if priority:
                fields["priority"] = {"name": priority}
            if assignee:
                fields["assignee"] = {"name": assignee}
            if labels:
                fields["labels"] = labels

            # Add any extra fields
            fields.update(extra_fields)

            jira_issue = self.client.create_issue(fields=fields)
            logger.info(f"Created issue: {jira_issue.key}")

            return Issue.from_jira_issue(jira_issue)

        except JIRAError as e:
            if e.status_code == 403:
                raise PermissionError(f"Permission denied creating issue in project '{project_key}'.") from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid issue data: {e.text}. Check issue type, priority, and field names.") from e
            else:
                raise JiraAPIError(f"Failed to create issue: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error creating issue: {e}") from e

    def add_worklog(
        self,
        issue_key: str,
        time_spent_minutes: int,
        comment: str | None = None,
        started: datetime | None = None,
    ) -> None:
        """Add work log entry to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            time_spent_minutes: Time spent in minutes
            comment: Work log comment
            started: When work started (default: now)

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to log work
            JiraAPIError: If logging fails
        """
        try:
            logger.info(f"Adding work log to {issue_key}: {time_spent_minutes}m")

            # Convert minutes to Jira time format (e.g., "2h 30m")
            hours = time_spent_minutes // 60
            minutes = time_spent_minutes % 60
            time_spent = ""
            if hours > 0:
                time_spent += f"{hours}h"
            if minutes > 0:
                if time_spent:
                    time_spent += " "
                time_spent += f"{minutes}m"

            self.client.add_worklog(
                issue=issue_key,
                timeSpent=time_spent,
                comment=comment,
                started=started,
            )
            logger.info(f"Successfully logged {time_spent} to {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"Permission denied logging work to issue '{issue_key}'. You may not have work log permissions."
                ) from e
            else:
                raise JiraAPIError(f"Failed to add work log: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding work log: {e}") from e

    def get_projects(self) -> list[dict[str, str]]:
        """Get list of accessible projects.

        Returns:
            List of project dictionaries with 'key' and 'name'

        Raises:
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info("Fetching accessible projects")
            projects = self.client.projects()
            return [{"key": p.key, "name": p.name} for p in projects]
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch projects: {e}") from e

    def get_issue_types(self, project_key: str) -> list[str]:
        """Get available issue types for a project.

        Args:
            project_key: Project key

        Returns:
            List of issue type names

        Raises:
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching issue types for project {project_key}")
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
            logger.info("Fetching priorities")
            priorities = self.client.priorities()
            return [p.name for p in priorities]
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch priorities: {e}") from e

    @classmethod
    def from_connection(cls, connection: Connection) -> JiraClient:
        """Create JiraClient from connection configuration.

        Args:
            connection: Connection configuration

        Returns:
            JiraClient instance

        Raises:
            AuthenticationError: If credentials not found
            JiraAPIError: If connection fails
        """
        credential_store = CredentialStore()

        if not credential_store.has_credentials(connection):
            raise AuthenticationError(
                f"No credentials found for connection '{connection.name}'. Run 'budjira connect' to set up credentials."
            )

        api_token = credential_store.retrieve(connection)
        if not api_token:
            raise AuthenticationError(f"Failed to retrieve credentials for connection '{connection.name}'.")
        return cls(connection, api_token)
