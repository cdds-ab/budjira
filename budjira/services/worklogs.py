"""Worklog service for managing time tracking on Jira issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from datetime import datetime


class WorklogService(BaseJiraService):
    """Service for managing work logs on Jira issues."""

    def add(
        self,
        issue_key: str,
        time_spent_minutes: int,
        comment: str | None = None,
        started: datetime | None = None,
    ) -> str:
        """Add work log entry to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            time_spent_minutes: Time spent in minutes
            comment: Work log comment
            started: When work started (default: now)

        Returns:
            The ID of the created worklog

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to log work
            JiraAPIError: If logging fails
        """
        try:
            self._log_operation("Add worklog", issue_key=issue_key, minutes=time_spent_minutes)

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

            worklog = self.client.add_worklog(
                issue=issue_key,
                timeSpent=time_spent,
                comment=comment,
                started=started,
            )
            self._logger.info(f"Successfully logged {time_spent} to {issue_key}")
            return str(worklog.id)

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
                self._handle_jira_error(e, "Add worklog", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding work log: {e}") from e

    def list(self, issue_key: str) -> list[dict[str, Any]]:
        """Get work log entries for an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of worklog dictionaries with keys:
            - id: Worklog ID
            - author: Author display name
            - authorAccountId: Author account ID
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
            self._log_operation("Fetch worklogs", issue_key=issue_key)
            issue = self.client.issue(issue_key)
            worklogs = self.client.worklogs(issue)

            results = []
            for wl in worklogs:
                results.append(self._to_dict(wl))

            self._logger.info(f"Found {len(results)} worklogs for {issue_key}")
            return results

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            else:
                self._handle_jira_error(e, "Fetch worklogs", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching worklogs: {e}") from e

    def delete(self, issue_key: str, worklog_id: str) -> None:
        """Delete a work log entry from an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            worklog_id: Worklog ID to delete

        Raises:
            InvalidIssueError: If issue or worklog not found
            PermissionError: If user lacks permission to delete worklog
            JiraAPIError: If deletion fails
        """
        try:
            self._log_operation("Delete worklog", issue_key=issue_key, worklog_id=worklog_id)

            issue = self.client.issue(issue_key)
            worklogs = self.client.worklogs(issue)

            # Find the worklog to delete
            target = None
            for wl in worklogs:
                if str(wl.id) == str(worklog_id):
                    target = wl
                    break

            if target is None:
                raise InvalidIssueError(
                    f"Worklog '{worklog_id}' not found on issue '{issue_key}'. "
                    f"Use 'budjira worklog list {issue_key}' to see available worklogs."
                )

            target.delete()
            self._logger.info(f"Successfully deleted worklog {worklog_id} from {issue_key}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"Permission denied deleting worklog from issue '{issue_key}'. "
                    f"You may only delete your own worklogs."
                ) from e
            else:
                self._handle_jira_error(e, "Delete worklog", issue_key=issue_key, worklog_id=worklog_id)
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error deleting worklog: {e}") from e

    def get(self, issue_key: str, worklog_id: str) -> dict[str, Any]:
        """Get a single work log entry from an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            worklog_id: Worklog ID

        Returns:
            Worklog dictionary (same keys as list())

        Raises:
            InvalidIssueError: If issue or worklog not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Get worklog", issue_key=issue_key, worklog_id=worklog_id)
            worklog = self.client.worklog(issue_key, worklog_id)
            return self._to_dict(worklog)

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' or worklog '{worklog_id}' not found. "
                    f"Use 'budjira worklog list {issue_key}' to see available worklogs."
                ) from e
            self._handle_jira_error(e, "Get worklog", issue_key=issue_key, worklog_id=worklog_id)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching worklog: {e}") from e

    def update(
        self,
        issue_key: str,
        worklog_id: str,
        time_spent_minutes: int | None = None,
        comment: str | None = None,
        started: datetime | None = None,
    ) -> dict[str, Any]:
        """Update a work log entry on an issue.

        Only provided fields are changed; omitted fields keep their values.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            worklog_id: Worklog ID to update
            time_spent_minutes: New time spent in minutes
            comment: New work log comment
            started: New start datetime

        Returns:
            Updated worklog dictionary (same keys as list())

        Raises:
            InvalidIssueError: If issue or worklog not found
            PermissionError: If user lacks permission to update the worklog
            JiraAPIError: If the update fails
        """
        try:
            self._log_operation("Update worklog", issue_key=issue_key, worklog_id=worklog_id)
            worklog = self.client.worklog(issue_key, worklog_id)

            fields: dict[str, Any] = {}
            if time_spent_minutes is not None:
                hours, minutes = divmod(time_spent_minutes, 60)
                time_spent = f"{hours}h" if hours > 0 else ""
                if minutes > 0:
                    time_spent = f"{time_spent} {minutes}m".strip()
                fields["timeSpent"] = time_spent
            if comment is not None:
                fields["comment"] = comment
            if started is not None:
                # Mirror JIRA.add_worklog: Jira expects e.g. 2026-08-20T10:00:00.000+0000,
                # naive datetimes are treated as UTC
                if started.tzinfo is None:
                    fields["started"] = started.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
                else:
                    fields["started"] = started.strftime("%Y-%m-%dT%H:%M:%S.000%z")

            worklog.update(**fields)
            self._logger.info(f"Successfully updated worklog {worklog_id} on {issue_key}")

            # Re-fetch so the result reflects the stored state regardless of
            # whether the jira library refreshes the resource in place
            return self._to_dict(self.client.worklog(issue_key, worklog_id))

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' or worklog '{worklog_id}' not found. "
                    f"Use 'budjira worklog list {issue_key}' to see available worklogs."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"Permission denied updating worklog '{worklog_id}' on issue '{issue_key}'. "
                    f"You may only update your own worklogs."
                ) from e
            else:
                self._handle_jira_error(e, "Update worklog", issue_key=issue_key, worklog_id=worklog_id)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error updating worklog: {e}") from e

    def _to_dict(self, worklog: Any) -> dict[str, Any]:
        """Convert a jira Worklog resource to a plain dictionary.

        Args:
            worklog: Worklog resource from the jira library

        Returns:
            Dictionary with worklog details (id, author, authorAccountId,
            timeSpent, timeSpentSeconds, started, created, optional comment)
        """
        worklog_data: dict[str, Any] = {
            "id": worklog.id,
            "author": worklog.author.displayName if hasattr(worklog, "author") else "Unknown",
            "authorAccountId": getattr(worklog.author, "accountId", None) if hasattr(worklog, "author") else None,
            "timeSpent": worklog.timeSpent if hasattr(worklog, "timeSpent") else "0m",
            "timeSpentSeconds": worklog.timeSpentSeconds if hasattr(worklog, "timeSpentSeconds") else 0,
            "started": worklog.started if hasattr(worklog, "started") else None,
            "created": worklog.created if hasattr(worklog, "created") else None,
        }

        # Add comment if present
        if hasattr(worklog, "comment") and worklog.comment:
            worklog_data["comment"] = worklog.comment

        return worklog_data
