"""Label service for managing issue labels."""

from __future__ import annotations

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError


class LabelService(BaseJiraService):
    """Service for managing issue labels."""

    def add(self, issue_key: str, labels: list[str]) -> None:
        """Add labels to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            labels: List of labels to add

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            self._log_operation("Add labels", issue_key=issue_key, labels=labels)
            issue = self.client.issue(issue_key)
            current_labels = issue.fields.labels or []
            new_labels = list(set(current_labels + labels))
            issue.update(fields={"labels": new_labels})
            self._logger.info(f"Successfully added labels to {issue_key}")
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                self._handle_jira_error(e, "Add labels", issue_key=issue_key)
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding labels: {e}") from e

    def remove(self, issue_key: str, labels: list[str]) -> None:
        """Remove labels from an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            labels: List of labels to remove

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If update fails
        """
        try:
            self._log_operation("Remove labels", issue_key=issue_key, labels=labels)
            issue = self.client.issue(issue_key)
            current_labels = issue.fields.labels or []
            new_labels = [label for label in current_labels if label not in labels]
            issue.update(fields={"labels": new_labels})
            self._logger.info(f"Successfully removed labels from {issue_key}")
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                self._handle_jira_error(e, "Remove labels", issue_key=issue_key)
        except Exception as e:
            raise JiraAPIError(f"Unexpected error removing labels: {e}") from e
