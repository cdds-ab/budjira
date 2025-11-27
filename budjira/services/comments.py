"""Comment service for managing issue comments."""

from __future__ import annotations

from typing import Any

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError


class CommentService(BaseJiraService):
    """Service for managing Jira issue comments."""

    def add(self, issue_key: str, body: str) -> dict[str, Any]:
        """Add a comment to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            body: Comment text (can be markdown or plain text)

        Returns:
            Dictionary with comment details (id, author, body, created)

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to comment
            JiraAPIError: If comment creation fails
        """
        try:
            self._log_operation("Add comment", issue_key=issue_key)
            comment = self.client.add_comment(issue_key, body)

            # Return comment details
            return {
                "id": comment.id,
                "author": comment.author.displayName if hasattr(comment, "author") else "Unknown",
                "body": comment.body,
                "created": comment.created if hasattr(comment, "created") else None,
            }

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"You don't have permission to comment on '{issue_key}'. "
                    f"Check your Jira permissions or contact your administrator."
                ) from e
            else:
                self._handle_jira_error(e, "Add comment", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding comment: {e}") from e
