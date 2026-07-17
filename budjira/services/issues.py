"""Issue service for CRUD operations on Jira issues."""

from __future__ import annotations

from typing import Any, cast

from jira.exceptions import JIRAError

from budjira.models.issue import Issue
from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError
from budjira.utils.markdown_to_jira import markdown_to_wiki


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
            self._log_operation("Create issue", project=project_key, type=issue_type, summary=summary)

            fields: dict[str, Any] = {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }

            if description:
                # Jira REST v2 renders descriptions as wiki markup; convert from Markdown (issue #95).
                fields["description"] = markdown_to_wiki(description)
            if priority:
                fields["priority"] = {"name": priority}
            if assignee:
                fields["assignee"] = {"name": assignee}
            if labels:
                fields["labels"] = labels

            # Add any extra fields
            fields.update(extra_fields)

            jira_issue = self.client.create_issue(fields=fields)
            self._logger.info(f"Created issue: {jira_issue.key}")

            return Issue.from_jira_issue(jira_issue)

        except JIRAError as e:
            if e.status_code == 403:
                raise PermissionError(f"Permission denied creating issue in project '{project_key}'.") from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid issue data: {e.text}. Check issue type, priority, and field names.") from e
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
            self._log_operation("Update issue", issue_key=issue_key)

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
                # Jira REST v2 renders descriptions as wiki markup; convert from Markdown (issue #95).
                update_fields["description"] = markdown_to_wiki(description)

            if update_fields:
                self.client.issue(issue_key).update(fields=update_fields)
                self._logger.info(f"Successfully updated {issue_key}")
            else:
                self._logger.warning(f"No fields to update for {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            elif e.status_code == 400:
                raise JiraAPIError(f"Invalid field values: {e.text}") from e
            else:
                self._handle_jira_error(e, "Update issue", issue_key=issue_key)
        except Exception as e:
            raise JiraAPIError(f"Unexpected error updating issue: {e}") from e
