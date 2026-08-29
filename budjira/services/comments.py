"""Comment service for managing issue comments."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from jira.resources import Comment


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

    def add_adf(self, issue_key: str, doc: dict[str, Any]) -> dict[str, Any]:
        """Add a comment whose body is an ADF document (REST API v3).

        Needed for inline media embeds: the v2 endpoint stores wiki markup, which
        cannot render images inside a comment body. The doc is posted verbatim to
        ``/rest/api/3/issue/{key}/comment``.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            doc: ADF document ({"type": "doc", "version": 1, "content": [...]})

        Returns:
            Dictionary with comment details (id, author, created)

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to comment
            JiraAPIError: If comment creation fails
        """
        try:
            self._log_operation("Add ADF comment", issue_key=issue_key)
            # The jira library has no public v3 comment endpoint; build the URL
            # and reuse its authenticated session (private members by necessity).
            url = self.client._get_url(
                f"issue/{issue_key}/comment",
                base="{server}/rest/api/3/{path}",
            )
            response = self.client._session.post(url, json={"body": doc})
            if not response.ok:
                raise JIRAError(
                    text=response.text,
                    status_code=response.status_code,
                    url=url,
                )
            data: dict[str, Any] = response.json()
            return {
                "id": data.get("id"),
                "author": (data.get("author") or {}).get("displayName", "Unknown"),
                "created": data.get("created"),
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
                self._handle_jira_error(e, "Add ADF comment", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error adding ADF comment to '{issue_key}': {e}") from e

    def list(self, issue_key: str) -> list[dict[str, Any]]:
        """List all comments on an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of dictionaries with comment details (id, author, body, created, updated)

        Raises:
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to view the issue
            JiraAPIError: If listing comments fails
        """
        try:
            self._log_operation("List comments", issue_key=issue_key)
            comments = self.client.comments(issue_key)
            return [self._to_dict(comment) for comment in comments]
        except JIRAError as e:
            self._handle_jira_error(e, "List comments", issue_key=issue_key)
            raise  # Ensure type checker knows this path raises
        except Exception as e:
            raise JiraAPIError(f"Unexpected error listing comments on '{issue_key}': {e}") from e

    def get(self, issue_key: str, comment_id: str) -> dict[str, Any]:
        """Get a single comment on an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            comment_id: Comment ID

        Returns:
            Dictionary with comment details (id, author, body, created, updated)

        Raises:
            InvalidIssueError: If issue or comment not found
            PermissionError: If user lacks permission to view the issue
            JiraAPIError: If fetching the comment fails
        """
        try:
            self._log_operation("Get comment", issue_key=issue_key, comment_id=comment_id)
            comment = self.client.comment(issue_key, comment_id)
            return self._to_dict(comment)
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' or comment '{comment_id}' not found. "
                    f"Check that both exist and you have permission to view them. "
                    f"Use 'budjira comment list {issue_key}' to see available comment IDs."
                ) from e
            self._handle_jira_error(e, "Get comment", issue_key=issue_key, comment_id=comment_id)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching comment '{comment_id}' on '{issue_key}': {e}") from e

    def update(self, issue_key: str, comment_id: str, body: str) -> dict[str, Any]:
        """Replace the body of an existing comment.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            comment_id: Comment ID
            body: New comment text (replaces the existing body)

        Returns:
            Dictionary with updated comment details (id, author, body, created, updated)

        Raises:
            InvalidIssueError: If issue or comment not found
            PermissionError: If user lacks permission to edit the comment
            JiraAPIError: If updating the comment fails
        """
        try:
            self._log_operation("Update comment", issue_key=issue_key, comment_id=comment_id)
            comment = self.client.comment(issue_key, comment_id)
            comment.update(body=body)
            return self._to_dict(comment)
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' or comment '{comment_id}' not found. "
                    f"Check that both exist and you have permission to view them. "
                    f"Use 'budjira comment list {issue_key}' to see available comment IDs."
                ) from e
            self._handle_modify_error(e, "Update comment", issue_key, comment_id)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error updating comment '{comment_id}' on '{issue_key}': {e}") from e

    def delete(self, issue_key: str, comment_id: str) -> None:
        """Delete a comment from an issue.

        Note that Jira often forbids deleting comments even for their authors
        (reported as a 400 permission error). Editing via
        'budjira comment update' is the reliable path in that case.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            comment_id: Comment ID

        Raises:
            InvalidIssueError: If issue or comment not found
            PermissionError: If user lacks permission to delete the comment
            JiraAPIError: If deleting the comment fails
        """
        try:
            self._log_operation("Delete comment", issue_key=issue_key, comment_id=comment_id)
            comment = self.client.comment(issue_key, comment_id)
            comment.delete()
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' or comment '{comment_id}' not found. "
                    f"Check that both exist and you have permission to view them. "
                    f"Use 'budjira comment list {issue_key}' to see available comment IDs."
                ) from e
            self._handle_modify_error(e, "Delete comment", issue_key, comment_id)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error deleting comment '{comment_id}' on '{issue_key}': {e}") from e

    def _to_dict(self, comment: Comment) -> dict[str, Any]:
        """Convert a jira Comment resource to a plain dictionary.

        Args:
            comment: Comment resource from the jira library

        Returns:
            Dictionary with comment details (id, author, body, created, updated)
        """
        return {
            "id": comment.id,
            "author": comment.author.displayName if hasattr(comment, "author") else "Unknown",
            "body": comment.body,
            "created": comment.created if hasattr(comment, "created") else None,
            "updated": comment.updated if hasattr(comment, "updated") else None,
        }

    def _handle_modify_error(self, error: JIRAError, operation: str, issue_key: str, comment_id: str) -> None:
        """Handle JIRA errors from comment modifications (update/delete).

        Jira reports missing permission to modify a comment either as 403 or as
        a 400 with a permission message (e.g. "You do not have permission to
        delete comment with id: ..."). Both are mapped to PermissionError with
        an actionable hint; everything else falls back to the base mapping.

        Args:
            error: JIRA API error from jira library
            operation: Human-readable operation description
            issue_key: Issue key the comment belongs to
            comment_id: Comment ID being modified

        Raises:
            PermissionError: When the user lacks permission to modify the comment
            InvalidIssueError: When the resource is not found (404)
            JiraAPIError: For all other API errors
        """
        if error.status_code in (400, 403) and "permission" in (error.text or "").lower():
            self._logger.warning(f"{operation} failed (issue_key={issue_key}, comment_id={comment_id}): {error.text}")
            raise PermissionError(
                f"{operation} failed: {error.text} "
                f"Jira often restricts comment modifications, even for the author. "
                f"Use 'budjira comment update {issue_key} {comment_id}' to revise the body instead."
            ) from error
        self._handle_jira_error(error, operation, issue_key=issue_key, comment_id=comment_id)
