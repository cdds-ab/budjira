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

            self.client.add_worklog(
                issue=issue_key,
                timeSpent=time_spent,
                comment=comment,
                started=started,
            )
            self._logger.info(f"Successfully logged {time_spent} to {issue_key}")

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
