"""Jira client facade delegating to focused services.

This module provides a backward-compatible facade over the service layer.
All business logic has been moved to domain-specific services in budjira.services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from jira import JIRA
from jira.exceptions import JIRAError

from budjira.config.credentials import CredentialStore
from budjira.services import (
    CommentService,
    EpicService,
    IssueService,
    LabelService,
    LinkService,
    MetadataService,
    SprintService,
    TransitionService,
    WorklogService,
)
from budjira.utils.errors import (
    AuthenticationError,
    JiraAPIError,
    PermissionError,
)

if TYPE_CHECKING:
    from datetime import datetime

    from budjira.models.connection import Connection, DescriptionDialect
    from budjira.models.issue import Issue

logger = logging.getLogger(__name__)


class JiraClient:
    """Facade for Jira operations delegating to domain services.

    This class maintains backward compatibility while delegating all operations
    to focused service classes. Each service handles a single responsibility:
    - IssueService: CRUD operations on issues
    - WorklogService: Time tracking
    - EpicService: Epic management
    - TransitionService: Status workflows
    - LabelService: Label management
    - CommentService: Comments
    - MetadataService: Projects, issue types, priorities, users
    """

    def __init__(self, connection: Connection, api_token: str) -> None:
        """Initialize Jira client and all services.

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

        # Initialize all domain services
        self.issues = IssueService(self._client)
        self.worklogs = WorklogService(self._client)
        self.epics = EpicService(self._client)
        self.transitions = TransitionService(self._client)
        self.labels = LabelService(self._client)
        self.comments = CommentService(self._client)
        self.metadata = MetadataService(self._client)
        self.links = LinkService(self._client)
        self.sprints = SprintService(self._client)

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

    @property
    def client(self) -> JIRA:
        """Get underlying JIRA client (for tempo.py compatibility).

        Returns:
            JIRA client instance

        Raises:
            JiraAPIError: If client is not initialized
        """
        if self._client is None:
            raise JiraAPIError("Jira client not initialized")
        return self._client

    # ==================== Issue Operations (delegate to IssueService) ====================

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: list[str] | None = None,
    ) -> list[Issue]:
        """Search for issues using JQL.

        DEPRECATED: Use client.issues.search() instead.
        """
        return self.issues.search(jql, max_results, fields)

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> Issue:
        """Get a single issue by key.

        DEPRECATED: Use client.issues.get() instead.
        """
        return self.issues.get(issue_key, fields)

    def get_issue_details(self, issue_key: str) -> Issue:
        """Get issue with full details including epic, time tracking, comments, and attachments.

        DEPRECATED: Use client.issues.get_details() instead.
        """
        return self.issues.get_details(issue_key)

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        description_dialect: DescriptionDialect = "markdown",
        **extra_fields: Any,
    ) -> Issue:
        """Create a new issue.

        DEPRECATED: Use client.issues.create() instead.
        """
        return self.issues.create(
            project_key,
            summary,
            issue_type,
            description,
            priority,
            assignee,
            labels,
            description_dialect,
            **extra_fields,
        )

    def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        description_dialect: DescriptionDialect = "markdown",
    ) -> None:
        """Update issue fields.

        DEPRECATED: Use client.issues.update() instead.
        """
        self.issues.update(issue_key, fields, assignee, priority, summary, description, description_dialect)

    # ==================== Worklog Operations (delegate to WorklogService) ====================

    def add_worklog(
        self,
        issue_key: str,
        time_spent_minutes: int,
        comment: str | None = None,
        started: datetime | None = None,
    ) -> None:
        """Add work log entry to an issue.

        DEPRECATED: Use client.worklogs.add() instead.
        """
        self.worklogs.add(issue_key, time_spent_minutes, comment, started)

    def get_worklogs(self, issue_key: str) -> list[dict[str, Any]]:
        """Get work log entries for an issue.

        DEPRECATED: Use client.worklogs.list() instead.
        """
        return self.worklogs.list(issue_key)

    def delete_worklog(self, issue_key: str, worklog_id: str) -> None:
        """Delete a work log entry from an issue.

        DEPRECATED: Use client.worklogs.delete() instead.
        """
        self.worklogs.delete(issue_key, worklog_id)

    # ==================== Epic Operations (delegate to EpicService) ====================

    def get_epic_issues(self, epic_key: str) -> list[Issue]:
        """Get all issues linked to an epic.

        DEPRECATED: Use client.epics.get_epic_issues() instead.
        """
        return self.epics.get_epic_issues(epic_key)

    def get_issue_epic(self, issue_key: str) -> tuple[str, str] | None:
        """Get epic information for an issue.

        DEPRECATED: Use client.epics.get_issue_epic() instead.
        """
        return self.epics.get_issue_epic(issue_key)

    def link_to_epic(self, issue_key: str, epic_key: str) -> None:
        """Link an issue to an epic.

        DEPRECATED: Use client.epics.link_to_epic() instead.
        """
        self.epics.link_to_epic(issue_key, epic_key)

    # ==================== Transition Operations (delegate to TransitionService) ====================

    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue.

        DEPRECATED: Use client.transitions.get_transitions() instead.
        """
        return self.transitions.get_transitions(issue_key)

    def transition_issue(self, issue_key: str, transition_name: str) -> None:
        """Transition an issue to a new status.

        DEPRECATED: Use client.transitions.transition() instead.
        """
        self.transitions.transition(issue_key, transition_name)

    # ==================== Label Operations (delegate to LabelService) ====================

    def add_labels(self, issue_key: str, labels: list[str]) -> None:
        """Add labels to an issue.

        DEPRECATED: Use client.labels.add() instead.
        """
        self.labels.add(issue_key, labels)

    def remove_labels(self, issue_key: str, labels: list[str]) -> None:
        """Remove labels from an issue.

        DEPRECATED: Use client.labels.remove() instead.
        """
        self.labels.remove(issue_key, labels)

    # ==================== Comment Operations (delegate to CommentService) ====================

    def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        """Add a comment to an issue.

        DEPRECATED: Use client.comments.add() instead.
        """
        return self.comments.add(issue_key, body)

    # ==================== Metadata Operations (delegate to MetadataService) ====================

    def get_projects(self) -> list[dict[str, Any]]:
        """Get list of accessible projects.

        DEPRECATED: Use client.metadata.get_projects() instead.
        """
        return self.metadata.get_projects()

    def get_issue_types(self, project_key: str) -> list[str]:
        """Get available issue types for a project.

        DEPRECATED: Use client.metadata.get_issue_types() instead.
        """
        return self.metadata.get_issue_types(project_key)

    def get_priorities(self) -> list[str]:
        """Get available priority levels.

        DEPRECATED: Use client.metadata.get_priorities() instead.
        """
        return self.metadata.get_priorities()

    def get_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users by name or email.

        DEPRECATED: Use client.metadata.get_users() instead.
        """
        return self.metadata.get_users(query)
