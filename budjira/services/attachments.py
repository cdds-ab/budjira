"""Attachment service for uploading files to issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError, ValidationError

if TYPE_CHECKING:
    from pathlib import Path


class AttachmentService(BaseJiraService):
    """Service for uploading file attachments to Jira issues.

    Uploads go through the jira library's ``add_attachment``, which posts
    multipart to ``/rest/api/2/issue/{key}/attachments`` with the required
    ``X-Atlassian-Token: no-check`` header.
    """

    def add(self, issue_key: str, file_path: Path) -> dict[str, Any]:
        """Upload a file as an attachment to an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            file_path: Path to the local file to upload

        Returns:
            Dictionary with attachment details (id, filename, size, mime_type, content URL)

        Raises:
            ValidationError: If the file does not exist or is empty
            InvalidIssueError: If issue not found
            PermissionError: If user lacks permission to add attachments
            JiraAPIError: If the upload fails
        """
        if not file_path.is_file():
            raise ValidationError(f"File not found: '{file_path}'. Check the path and try again.")
        if file_path.stat().st_size == 0:
            raise ValidationError(f"File is empty: '{file_path}'. Jira rejects empty attachments.")

        try:
            self._log_operation("Add attachment", issue_key=issue_key, filename=file_path.name)
            with file_path.open("rb") as file_handle:
                attachment = self.client.add_attachment(
                    issue=issue_key,
                    attachment=file_handle,
                    filename=file_path.name,
                )

            return {
                "id": attachment.id,
                "filename": attachment.filename,
                "size": attachment.size,
                "mime_type": getattr(attachment, "mimeType", None),
                "content": getattr(attachment, "content", None),
            }

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            elif e.status_code == 403:
                raise PermissionError(
                    f"You don't have permission to add attachments to '{issue_key}'. "
                    f"Check your Jira permissions or contact your administrator."
                ) from e
            else:
                self._handle_jira_error(e, "Add attachment", issue_key=issue_key, filename=file_path.name)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error attaching '{file_path.name}' to '{issue_key}': {e}") from e
