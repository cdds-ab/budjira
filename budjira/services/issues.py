"""Issue service for CRUD operations on Jira issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from jira.exceptions import JIRAError

from budjira.models.issue import Issue
from budjira.services.base import BaseJiraService
from budjira.utils.description import render_description
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from budjira.models.connection import DescriptionDialect

# Marker for the currentUser() account id in dry-run payloads: the id is only
# resolved (via a read call) when the update is actually applied.
CURRENT_USER_PLACEHOLDER = "<currentUser()>"


def build_create_fields(
    project_key: str,
    summary: str,
    issue_type: str,
    description: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
    description_dialect: DescriptionDialect = "markdown",
    extra_fields: dict[str, Any] | None = None,
    priority_id: str | None = None,
) -> dict[str, Any]:
    """Assemble the exact ``fields`` payload for issue creation.

    Shared by :meth:`IssueService.create` and the CLI ``--dry-run`` preview so
    the preview always shows what the real call would send.

    Args:
        project_key: Project key (e.g., PROJ)
        summary: Issue summary
        issue_type: Issue type name
        description: Issue description (converted according to the dialect)
        priority: Priority name (sent as {"name": ...})
        assignee: Assignee username
        labels: List of labels
        description_dialect: Dialect the description is authored in
        extra_fields: Additional fields (timetracking, parent, custom fields)
        priority_id: Priority as numeric ID (sent as {"id": ...}; wins over
            priority when both are given)

    Returns:
        The ``fields`` dict for the create call
    """
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = render_description(description, description_dialect)
    if priority_id:
        fields["priority"] = {"id": priority_id}
    elif priority:
        fields["priority"] = {"name": priority}
    if assignee:
        fields["assignee"] = {"name": assignee}
    if labels:
        fields["labels"] = labels
    if extra_fields:
        fields.update(extra_fields)
    return fields


def build_update_fields(
    fields: dict[str, Any] | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    description_dialect: DescriptionDialect = "markdown",
    current_user_account_id: str | None = None,
    priority_id: str | None = None,
) -> dict[str, Any]:
    """Assemble the exact ``fields`` payload for an issue update.

    Shared by :meth:`IssueService.update` and the CLI ``--dry-run`` preview.
    For ``assignee="currentUser()"`` the account id must be supplied by the
    caller; without one (a dry run performs no API call) the payload carries
    :data:`CURRENT_USER_PLACEHOLDER` to show where resolution will happen.

    Args:
        fields: Raw field updates to start from (not mutated)
        assignee: Assignee username, "currentUser()", or "" to unassign
        priority: Priority name (sent as {"name": ...})
        summary: New summary
        description: New description (converted according to the dialect)
        description_dialect: Dialect the description is authored in
        current_user_account_id: Resolved account id for "currentUser()"
        priority_id: Priority as numeric ID (sent as {"id": ...}; wins over
            priority when both are given)

    Returns:
        The ``fields`` dict for the update call
    """
    update_fields: dict[str, Any] = dict(fields) if fields else {}
    if assignee is not None:
        if assignee.lower() == "currentuser()":
            update_fields["assignee"] = {"accountId": current_user_account_id or CURRENT_USER_PLACEHOLDER}
        elif assignee == "":
            update_fields["assignee"] = None
        else:
            update_fields["assignee"] = {"name": assignee}
    if priority_id is not None:
        update_fields["priority"] = {"id": priority_id}
    elif priority is not None:
        update_fields["priority"] = {"name": priority}
    if summary is not None:
        update_fields["summary"] = summary
    if description is not None:
        update_fields["description"] = render_description(description, description_dialect)
    return update_fields


class IssueService(BaseJiraService):
    """Service for managing Jira issues (search, get, create, update)."""

    def search(
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
            self._log_operation("Search issues", jql=jql, max_results=max_results)
            jira_issues = self.client.search_issues(
                jql_str=jql,
                maxResults=max_results,
                fields=fields if fields else "*all",
            )
            self._logger.info(f"Found {len(jira_issues)} issues")

            return [Issue.from_jira_issue(issue) for issue in jira_issues]

        except JIRAError as e:
            if e.status_code == 403:
                raise PermissionError(
                    "Permission denied while searching. User may not have access to the specified project."
                ) from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid JQL query: {jql}. Error: {e.text}") from e
            else:
                self._handle_jira_error(e, "Search issues", jql=jql)
                raise  # Ensure type checker knows this path raises
        except (PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error during search: {e}") from e

    def get(self, issue_key: str, fields: list[str] | None = None) -> Issue:
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
            self._log_operation("Fetch issue", issue_key=issue_key)
            jira_issue = self.client.issue(
                issue_key,
                fields=",".join(fields) if fields else "*all",
            )
            return Issue.from_jira_issue(jira_issue)

        except JIRAError as e:
            self._handle_jira_error(e, "Fetch issue", issue_key=issue_key)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching issue: {e}") from e

    def get_details(self, issue_key: str) -> Issue:
        """Get a single issue with full details including epic, time tracking, comments, and attachments.

        This method is more expensive than get() as it fetches all fields and epic information.

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
            self._log_operation("Fetch detailed issue", issue_key=issue_key)

            # Fetch issue with all fields
            jira_issue = self.client.issue(issue_key, fields="*all")

            # Fetch epic information (import here to avoid circular dependency)
            from budjira.services.epics import EpicService

            epic_service = EpicService(self.client)
            epic_info = None
            try:
                epic_info = epic_service.get_issue_epic(issue_key)
            except Exception as e:
                self._logger.debug(f"Could not fetch epic info for {issue_key}: {e}")

            # Create Issue with epic info
            return Issue.from_jira_issue(jira_issue, epic_info=epic_info)

        except JIRAError as e:
            self._handle_jira_error(e, "Fetch issue details", issue_key=issue_key)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching issue details: {e}") from e

    def create(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
        priority: str | None = None,
        priority_id: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        description_dialect: DescriptionDialect = "markdown",
        **extra_fields: Any,
    ) -> Issue:
        """Create a new issue.

        Args:
            project_key: Project key (e.g., PROJ)
            summary: Issue summary
            issue_type: Issue type (Bug, Task, Story, etc.)
            description: Issue description
            priority: Priority name (sent as {"name": ...})
            priority_id: Priority as numeric ID (sent as {"id": ...}, for
                instances that reject names)
            assignee: Assignee username
            labels: List of labels
            description_dialect: Dialect the description is authored in, resolved by the caller
            **extra_fields: Additional custom fields

        Returns:
            Created Issue object

        Raises:
            ValidationError: If required fields are missing
            PermissionError: If user lacks create permission
            JiraAPIError: If creation fails
        """
        try:
            self._log_operation("Create issue", project=project_key, type=issue_type, summary=summary)

            fields = build_create_fields(
                project_key,
                summary,
                issue_type,
                description,
                priority,
                assignee,
                labels,
                description_dialect,
                extra_fields,
                priority_id=priority_id,
            )

            jira_issue = self.client.create_issue(fields=fields)
            self._logger.info(f"Created issue: {jira_issue.key}")

            return Issue.from_jira_issue(jira_issue)

        except JIRAError as e:
            if e.status_code == 403:
                raise PermissionError(f"Permission denied creating issue in project '{project_key}'.") from e
            elif e.status_code == 400:
                hint = self._available_priorities_hint(priority or priority_id)
                raise JiraAPIError(
                    f"Invalid issue data: {e.text}. Check issue type, priority, and field names.{hint}"
                ) from e
            else:
                self._handle_jira_error(e, "Create issue", project=project_key)
                raise  # Ensure type checker knows this path raises
        except (PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error creating issue: {e}") from e

    def delete(self, issue_key: str, delete_subtasks: bool = False) -> None:
        """Delete an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            delete_subtasks: If True, also delete subtasks of the issue

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to delete issue
            JiraAPIError: If deletion fails
        """
        try:
            self._log_operation("Delete issue", issue_key=issue_key, delete_subtasks=delete_subtasks)
            # jira's Resource.delete is inherited untyped (unlike the overridden Issue.update). cast() keeps this
            # clean across mypy environments: with jira installed the call would otherwise raise no-untyped-call,
            # while in the jira-less CI mypy env a type: ignore would be flagged unused.
            cast("Any", self.client.issue(issue_key)).delete(deleteSubtasks=delete_subtasks)
            self._logger.info(f"Deleted issue {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"Permission denied deleting issue '{issue_key}'. You need the 'Delete Issues' permission in Jira."
                ) from e
            else:
                self._handle_jira_error(e, "Delete issue", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error deleting issue: {e}") from e

    def update(
        self,
        issue_key: str,
        fields: dict[str, Any] | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        priority_id: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        description_dialect: DescriptionDialect = "markdown",
    ) -> None:
        """Update issue fields.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: Dict of field updates (raw Jira field format)
            assignee: Assignee username or account ID (or "currentUser()")
            priority: Priority name (sent as {"name": ...})
            priority_id: Priority as numeric ID (sent as {"id": ...}, for
                instances that reject names)
            summary: New summary
            description: New description
            description_dialect: Dialect the description is authored in, resolved by the caller

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            self._log_operation("Update issue", issue_key=issue_key)

            # Resolve currentUser() only when actually used (read call)
            current_user_account_id: str | None = None
            if assignee is not None and assignee.lower() == "currentuser()":
                myself = self.client.myself()
                current_user_account_id = myself["accountId"]

            update_fields = build_update_fields(
                fields,
                assignee,
                priority,
                summary,
                description,
                description_dialect,
                current_user_account_id,
                priority_id=priority_id,
            )

            if update_fields:
                self.client.issue(issue_key).update(fields=update_fields)
                self._logger.info(f"Successfully updated {issue_key}")
            else:
                self._logger.warning(f"No fields to update for {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            elif e.status_code == 400:
                hint = self._available_priorities_hint(priority or priority_id)
                raise JiraAPIError(f"Invalid field values: {e.text}{hint}") from e
            else:
                self._handle_jira_error(e, "Update issue", issue_key=issue_key)
        except Exception as e:
            raise JiraAPIError(f"Unexpected error updating issue: {e}") from e

    def _available_priorities_hint(self, priority_given: str | None) -> str:
        """Best-effort list of the instance's priorities after a rejected one.

        A 400 on create/update names no field; when a priority was involved,
        the values the instance actually offers are the most useful answer.
        A failing read must never mask the original error.

        Args:
            priority_given: The priority name or id the caller supplied

        Returns:
            Sentence listing the available priorities, or empty string
        """
        if not priority_given:
            return ""
        try:
            priorities = self.client.priorities()
        except Exception:
            return ""
        names = ", ".join(p.name for p in priorities)
        return f" Available priorities on this instance: {names}."
