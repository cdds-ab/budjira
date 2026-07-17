# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for issue service."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.services.issues import IssueService
from budjira.utils.errors import InvalidIssueError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


class TestDeleteIssue:
    """Test delete method."""

    def test_delete_success(self) -> None:
        """Test deleting an issue successfully."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue

        service = IssueService(mock_client)
        service.delete("PROJ-123")

        mock_client.issue.assert_called_once_with("PROJ-123")
        mock_issue.delete.assert_called_once_with(deleteSubtasks=False)

    def test_delete_with_subtasks(self) -> None:
        """Test deleting an issue with subtasks."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue

        service = IssueService(mock_client)
        service.delete("PROJ-123", delete_subtasks=True)

        mock_client.issue.assert_called_once_with("PROJ-123")
        mock_issue.delete.assert_called_once_with(deleteSubtasks=True)

    def test_delete_issue_not_found(self) -> None:
        """Test deleting a non-existent issue raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = IssueService(mock_client)

        with pytest.raises(InvalidIssueError, match="Issue 'PROJ-999' not found"):
            service.delete("PROJ-999")

    def test_delete_permission_denied(self) -> None:
        """Test deleting without permission raises PermissionError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=403, text="Permission denied")

        service = IssueService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="Permission denied deleting issue"):
            service.delete("PROJ-123")

    def test_delete_api_error(self) -> None:
        """Test deleting with unexpected API error."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=500, text="Server error")

        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError):
            service.delete("PROJ-123")


class TestDescriptionConversion:
    """Markdown descriptions must be converted to Jira wiki markup on upload."""

    def test_create_converts_markdown_description(self) -> None:
        """create() sends wiki markup, not raw Markdown (issue #95)."""
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create("PROJ", "summary", "Task", description="## Title\n- [ ] todo")

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["description"] == "h2. Title\n* (x) todo"

    def test_update_converts_markdown_description(self) -> None:
        """update() sends wiki markup, not raw Markdown (issue #95)."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        service = IssueService(mock_client)

        service.update("PROJ-1", description="## Title\n- [ ] todo")

        fields = mock_issue.update.call_args.kwargs["fields"]
        assert fields["description"] == "h2. Title\n* (x) todo"
