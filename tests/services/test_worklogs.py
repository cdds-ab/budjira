# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for worklog service."""

from unittest.mock import MagicMock

import pytest
from budjira.services.worklogs import WorklogService
from budjira.utils.errors import InvalidIssueError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


class TestDeleteWorklog:
    """Test delete method."""

    def test_delete_success(self) -> None:
        """Test deleting a worklog successfully."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.id = "10001"
        mock_client.issue.return_value = mock_issue
        mock_client.worklogs.return_value = [mock_worklog]

        service = WorklogService(mock_client)
        service.delete("PROJ-123", "10001")

        mock_client.issue.assert_called_once_with("PROJ-123")
        mock_worklog.delete.assert_called_once()

    def test_delete_worklog_not_found(self) -> None:
        """Test deleting a non-existent worklog raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        mock_client.worklogs.return_value = []

        service = WorklogService(mock_client)

        with pytest.raises(InvalidIssueError, match="Worklog '99999' not found"):
            service.delete("PROJ-123", "99999")

    def test_delete_issue_not_found(self) -> None:
        """Test deleting worklog from non-existent issue raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = WorklogService(mock_client)

        with pytest.raises(InvalidIssueError, match="Issue 'PROJ-999' not found"):
            service.delete("PROJ-999", "10001")

    def test_delete_permission_denied(self) -> None:
        """Test deleting worklog without permission raises PermissionError."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.id = "10001"
        mock_worklog.delete.side_effect = JIRAError(status_code=403, text="Permission denied")
        mock_client.issue.return_value = mock_issue
        mock_client.worklogs.return_value = [mock_worklog]

        service = WorklogService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="Permission denied"):
            service.delete("PROJ-123", "10001")

    def test_delete_api_error(self) -> None:
        """Test deleting worklog with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=500, text="Server error")

        service = WorklogService(mock_client)

        with pytest.raises(JiraAPIError):
            service.delete("PROJ-123", "10001")

    def test_delete_finds_correct_worklog(self) -> None:
        """Test that delete finds the correct worklog among multiple."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        wl1 = MagicMock()
        wl1.id = "10001"
        wl2 = MagicMock()
        wl2.id = "10002"
        wl3 = MagicMock()
        wl3.id = "10003"
        mock_client.issue.return_value = mock_issue
        mock_client.worklogs.return_value = [wl1, wl2, wl3]

        service = WorklogService(mock_client)
        service.delete("PROJ-123", "10002")

        wl1.delete.assert_not_called()
        wl2.delete.assert_called_once()
        wl3.delete.assert_not_called()
