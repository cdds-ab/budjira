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


class TestAddWorklog:
    """Test add method."""

    def test_add_returns_worklog_id(self) -> None:
        """Test adding a worklog returns the created worklog ID."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.id = "67890"
        mock_client.add_worklog.return_value = mock_worklog

        service = WorklogService(mock_client)
        result = service.add("PROJ-123", 150, "Development work")

        assert result == "67890"
        mock_client.add_worklog.assert_called_once_with(
            issue="PROJ-123",
            timeSpent="2h 30m",
            comment="Development work",
            started=None,
        )

    def test_add_formats_minutes_only(self) -> None:
        """Test adding a sub-hour worklog formats only minutes."""
        mock_client = MagicMock()
        mock_client.add_worklog.return_value = MagicMock(id="1")

        service = WorklogService(mock_client)
        service.add("PROJ-123", 45)

        assert mock_client.add_worklog.call_args[1]["timeSpent"] == "45m"


class TestListWorklogs:
    """Test list method additions."""

    def test_list_includes_author_account_id(self) -> None:
        """Test listing worklogs includes the author account ID (#113)."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.id = "67890"
        mock_worklog.author.displayName = "John Doe"
        mock_worklog.author.accountId = "557058:abc123"
        mock_worklog.timeSpent = "2h"
        mock_worklog.timeSpentSeconds = 7200
        mock_worklog.started = "2026-08-20T10:00:00.000+0000"
        mock_worklog.created = "2026-08-20T10:00:00.000+0000"
        mock_worklog.comment = "Work"
        mock_client.worklogs.return_value = [mock_worklog]

        service = WorklogService(mock_client)
        result = service.list("PROJ-123")

        assert result[0]["authorAccountId"] == "557058:abc123"
        assert result[0]["author"] == "John Doe"


class TestGetWorklog:
    """Test get method."""

    def test_get_success(self) -> None:
        """Test getting a single worklog."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.id = "67890"
        mock_worklog.author.displayName = "John Doe"
        mock_worklog.author.accountId = "557058:abc123"
        mock_worklog.timeSpent = "2h"
        mock_worklog.timeSpentSeconds = 7200
        mock_worklog.started = "2026-08-20T10:00:00.000+0000"
        mock_worklog.created = "2026-08-20T10:00:00.000+0000"
        mock_worklog.comment = "Work"
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)
        result = service.get("PROJ-123", "67890")

        mock_client.worklog.assert_called_once_with("PROJ-123", "67890")
        assert result["id"] == "67890"
        assert result["timeSpentSeconds"] == 7200
        assert result["comment"] == "Work"

    def test_get_not_found(self) -> None:
        """Test getting a non-existent worklog raises InvalidIssueError with a list hint."""
        mock_client = MagicMock()
        mock_client.worklog.side_effect = JIRAError(status_code=404, text="Not found")

        service = WorklogService(mock_client)

        with pytest.raises(InvalidIssueError, match="worklog list PROJ-123"):
            service.get("PROJ-123", "99999")

    def test_get_api_error(self) -> None:
        """Test getting a worklog with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.worklog.side_effect = JIRAError(status_code=500, text="Server error")

        service = WorklogService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.get("PROJ-123", "67890")


class TestUpdateWorklog:
    """Test update method."""

    def test_update_success_only_given_fields(self) -> None:
        """Test updating a worklog sends only the given fields."""
        from datetime import datetime

        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)
        service.update(
            "PROJ-123",
            "67890",
            time_spent_minutes=180,
            comment="Revised",
            started=datetime(2026, 8, 21, 9, 30),
        )

        mock_worklog.update.assert_called_once_with(
            timeSpent="3h",
            comment="Revised",
            started="2026-08-21T09:30:00.000+0000",
        )

    def test_update_single_field(self) -> None:
        """Test updating only the comment leaves other fields untouched."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)
        service.update("PROJ-123", "67890", comment="Only comment")

        mock_worklog.update.assert_called_once_with(comment="Only comment")

    def test_update_returns_refetched_state(self) -> None:
        """Test update returns the re-fetched worklog state."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)
        result = service.update("PROJ-123", "67890", time_spent_minutes=60)

        assert mock_client.worklog.call_count == 2
        assert result["id"] == mock_worklog.id

    def test_update_not_found(self) -> None:
        """Test updating a non-existent worklog raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.worklog.side_effect = JIRAError(status_code=404, text="Not found")

        service = WorklogService(mock_client)

        with pytest.raises(InvalidIssueError, match="worklog '99999'"):
            service.update("PROJ-123", "99999", comment="x")

    def test_update_permission_denied(self) -> None:
        """Test updating without permission raises PermissionError."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.update.side_effect = JIRAError(status_code=403, text="Forbidden")
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="only update your own worklogs"):
            service.update("PROJ-123", "67890", comment="x")

    def test_update_api_error(self) -> None:
        """Test updating a worklog with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_worklog = MagicMock()
        mock_worklog.update.side_effect = JIRAError(status_code=500, text="Server error")
        mock_client.worklog.return_value = mock_worklog

        service = WorklogService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.update("PROJ-123", "67890", comment="x")
