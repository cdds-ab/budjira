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

    def get_issue_details(self, issue_key: str) -> Issue:
        """Get a single issue with full details including epic, time tracking, comments, and attachments.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            Issue object with all details populated

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to view issue
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching detailed issue: {issue_key}")

            # Fetch issue with all fields
            jira_issue = self.client.issue(issue_key, fields="*all")

            # Fetch epic information
            epic_info = None
            try:
                epic_info = self.get_issue_epic(issue_key)
            except Exception as e:
                logger.debug(f"Could not fetch epic info for {issue_key}: {e}")

            # Create Issue with epic info
            return Issue.from_jira_issue(jira_issue, epic_info=epic_info)

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(f"Permission denied accessing issue '{issue_key}'.") from e
            else:
                raise JiraAPIError(f"Failed to fetch issue '{issue_key}': {e.text}") from e
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching issue details: {e}") from e

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

    def get_worklogs(self, issue_key: str) -> list[dict[str, Any]]:
        """Get work log entries for an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of worklog dictionaries with keys:
            - id: Worklog ID
            - author: Author display name
            - timeSpent: Time spent (formatted, e.g., "2h 30m")
            - timeSpentSeconds: Time spent in seconds
            - comment: Work log comment (if any)
            - started: When work started (datetime string)
            - created: When worklog was created (datetime string)

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching worklogs for {issue_key}")
            issue = self.client.issue(issue_key)
            worklogs = self.client.worklogs(issue)

            results = []
            for wl in worklogs:
                worklog_data = {
                    "id": wl.id,
                    "author": wl.author.displayName if hasattr(wl, "author") else "Unknown",
                    "timeSpent": wl.timeSpent if hasattr(wl, "timeSpent") else "0m",
                    "timeSpentSeconds": wl.timeSpentSeconds if hasattr(wl, "timeSpentSeconds") else 0,
                    "started": wl.started if hasattr(wl, "started") else None,
                    "created": wl.created if hasattr(wl, "created") else None,
                }

                # Add comment if present
                if hasattr(wl, "comment") and wl.comment:
                    worklog_data["comment"] = wl.comment

                results.append(worklog_data)

            logger.info(f"Found {len(results)} worklogs for {issue_key}")
            return results

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            else:
                raise JiraAPIError(f"Failed to fetch worklogs: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching worklogs: {e}") from e

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

    def get_transitions(self, issue_key: str) -> list[dict[str, str]]:
        """Get available transitions for an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of dicts with 'id' and 'name' keys

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching transitions for {issue_key}")
            transitions = self.client.transitions(issue_key)
            return [{"id": t["id"], "name": t["name"]} for t in transitions]
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                raise JiraAPIError(f"Failed to fetch transitions: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching transitions: {e}") from e

    def transition_issue(self, issue_key: str, transition_name: str) -> None:
        """Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            transition_name: Name of the transition (e.g., "In Progress", "Done")

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If transition fails or is invalid
        """
        try:
            logger.info(f"Transitioning {issue_key} to '{transition_name}'")

            # Get available transitions
            transitions = self.get_transitions(issue_key)

            # Find matching transition (case-insensitive)
            transition_id = None
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = ", ".join([t["name"] for t in transitions])
                raise JiraAPIError(
                    f"Invalid transition '{transition_name}' for {issue_key}. Available transitions: {available}"
                )

            self.client.transition_issue(issue_key, transition_id)
            logger.info(f"Successfully transitioned {issue_key} to '{transition_name}'")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                raise JiraAPIError(f"Failed to transition issue: {e.text}") from e
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error transitioning issue: {e}") from e

    def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        summary: str | None = None,
        description: str | None = None,
    ) -> None:
        """Update issue fields.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: Dict of field updates (raw Jira field format)
            assignee: Assignee username or account ID (or "currentUser()")
            priority: Priority name
            summary: New summary
            description: New description

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            logger.info(f"Updating issue {issue_key}")

            update_fields: dict[str, Any] = fields or {}

            # Handle assignee
            if assignee is not None:
                if assignee.lower() == "currentuser()":
                    # Get current user's account ID
                    myself = self.client.myself()
                    update_fields["assignee"] = {"accountId": myself["accountId"]}
                elif assignee == "":
                    # Unassign
                    update_fields["assignee"] = None
                else:
                    # Assign to specific user
                    update_fields["assignee"] = {"name": assignee}

            # Handle priority
            if priority is not None:
                update_fields["priority"] = {"name": priority}

            # Handle summary
            if summary is not None:
                update_fields["summary"] = summary

            # Handle description
            if description is not None:
                update_fields["description"] = description

            if update_fields:
                self.client.issue(issue_key).update(fields=update_fields)
                logger.info(f"Successfully updated {issue_key}")
            else:
                logger.warning(f"No fields to update for {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid field values: {e.text}") from e
            else:
                raise JiraAPIError(f"Failed to update issue: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error updating issue: {e}") from e

    def add_labels(self, issue_key: str, labels: list[str]) -> None:
        """Add labels to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            labels: List of labels to add

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            logger.info(f"Adding labels to {issue_key}: {labels}")
            issue = self.client.issue(issue_key)
            current_labels = issue.fields.labels or []
            new_labels = list(set(current_labels + labels))
            issue.update(fields={"labels": new_labels})
            logger.info(f"Successfully added labels to {issue_key}")
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                raise JiraAPIError(f"Failed to add labels: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding labels: {e}") from e

    def remove_labels(self, issue_key: str, labels: list[str]) -> None:
        """Remove labels from an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            labels: List of labels to remove

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            logger.info(f"Removing labels from {issue_key}: {labels}")
            issue = self.client.issue(issue_key)
            current_labels = issue.fields.labels or []
            new_labels = [label for label in current_labels if label not in labels]
            issue.update(fields={"labels": new_labels})
            logger.info(f"Successfully removed labels from {issue_key}")
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                raise JiraAPIError(f"Failed to remove labels: {e.text}") from e
        except Exception as e:
            raise JiraAPIError(f"Unexpected error removing labels: {e}") from e

    def link_to_epic(self, issue_key: str, epic_key: str) -> None:
        """Link an issue to an epic.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            epic_key: Epic key (e.g., PROJ-100)

        Raises:
            InvalidIssueError: If issue or epic not found
            JiraAPIError: If linking fails
        """
        try:
            logger.info(f"Linking {issue_key} to epic {epic_key}")

            issue = self.client.issue(issue_key)

            # Try modern approach first (parent field - used in Jira Cloud team-managed projects)
            try:
                issue.update(fields={"parent": {"key": epic_key}})
                logger.info(f"Successfully linked {issue_key} to epic {epic_key} using parent field")
                return
            except JIRAError as e:
                # If parent field fails, try legacy Epic Link field
                logger.debug(f"Parent field failed, trying legacy Epic Link: {e}")

            # Fallback to legacy Epic Link custom field (company-managed projects)
            # Epic Link is usually customfield_10014, but can vary
            epic_link_field = None
            fields = self.client.fields()
            for field in fields:
                if field["name"].lower() == "epic link":
                    epic_link_field = field["id"]
                    break

            if not epic_link_field:
                raise JiraAPIError(
                    "Epic linking failed. Neither 'parent' field nor 'Epic Link' custom field found. "
                    "Your Jira instance may not have epics enabled, or you may lack permission."
                )

            issue.update(fields={epic_link_field: epic_key})
            logger.info(f"Successfully linked {issue_key} to epic {epic_key} using Epic Link field")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError("Issue or epic not found") from e
            else:
                raise JiraAPIError(f"Failed to link to epic: {e.text}") from e
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error linking to epic: {e}") from e

    def get_epic_issues(self, epic_key: str) -> list[Issue]:
        """Get all issues linked to an epic.

        Args:
            epic_key: Epic key (e.g., PROJ-100)

        Returns:
            List of Issue objects

        Raises:
            InvalidIssueError: If epic not found
            JiraAPIError: If retrieval fails
        """
        try:
            logger.info(f"Fetching issues for epic {epic_key}")

            # Try modern approach first (parent field - Jira Cloud team-managed projects)
            try:
                jql_modern = f"parent = {epic_key}"
                issues = self.search_issues(jql_modern, max_results=100)
                if issues:
                    logger.debug(f"Found {len(issues)} issues using parent field")
                    return issues
            except Exception as e:
                logger.debug(f"Modern parent query failed, trying legacy: {e}")

            # Fallback to legacy Epic Link custom field (company-managed projects)
            jql_legacy = f'"Epic Link" = {epic_key}'
            issues = self.search_issues(jql_legacy, max_results=100)
            logger.debug(f"Found {len(issues)} issues using Epic Link field")
            return issues

        except Exception as e:
            raise JiraAPIError(f"Failed to fetch epic issues: {e}") from e

    def get_issue_epic(self, issue_key: str) -> tuple[str, str] | None:
        """Get epic information for an issue.

        Fetches the parent epic key and name for a given issue.
        Supports both modern (parent field) and legacy (Epic Link) approaches.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            Tuple of (epic_key, epic_name) if issue has an epic, None otherwise

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            logger.debug(f"Fetching epic for issue {issue_key}")

            # Get issue with parent and epic link fields
            jira_issue = self.client.issue(issue_key, fields="parent,customfield_*,summary")

            # Try modern approach first (parent field)
            if hasattr(jira_issue.fields, "parent") and jira_issue.fields.parent:
                parent = jira_issue.fields.parent
                epic_key = parent.key
                epic_name = parent.fields.summary if hasattr(parent.fields, "summary") else epic_key
                logger.debug(f"Found epic via parent field: {epic_key}")
                return (epic_key, epic_name)

            # Try legacy Epic Link custom field
            for field_name in dir(jira_issue.fields):
                if "epic" in field_name.lower() and "link" in field_name.lower():
                    epic_key = getattr(jira_issue.fields, field_name, None)
                    if epic_key:
                        # Fetch epic details for name
                        try:
                            epic_issue = self.client.issue(epic_key, fields="summary")
                            epic_name = epic_issue.fields.summary
                        except Exception:
                            epic_name = epic_key  # Fallback to key if fetch fails
                        logger.debug(f"Found epic via Epic Link field: {epic_key}")
                        return (epic_key, epic_name)

            # No epic found
            logger.debug(f"No epic found for issue {issue_key}")
            return None

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            raise JiraAPIError(f"Failed to fetch epic for issue {issue_key}: {e}") from e
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch epic for issue {issue_key}: {e}") from e

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
