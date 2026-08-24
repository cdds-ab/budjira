# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for comment service."""

from unittest.mock import MagicMock

import pytest
from budjira.services.comments import CommentService
from budjira.utils.errors import InvalidIssueError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


def _make_comment(
    comment_id: str = "10234",
    author: str = "John Doe",
    body: str = "Test comment",
    created: str = "2026-08-20T10:00:00.000+0000",
    updated: str = "2026-08-20T10:00:00.000+0000",
) -> MagicMock:
    """Create a mock jira Comment resource."""
    comment = MagicMock()
    comment.id = comment_id
    comment.author.displayName = author
    comment.body = body
    comment.created = created
    comment.updated = updated
    return comment


class TestListComments:
    """Test list method."""

    def test_list_success(self) -> None:
        """Test listing comments returns dictionaries with all fields."""
        mock_client = MagicMock()
        mock_client.comments.return_value = [_make_comment("10234"), _make_comment("10235", author="Jane")]

        service = CommentService(mock_client)
        result = service.list("PROJ-123")

        mock_client.comments.assert_called_once_with("PROJ-123")
        assert len(result) == 2
        assert result[0] == {
            "id": "10234",
            "author": "John Doe",
            "body": "Test comment",
            "created": "2026-08-20T10:00:00.000+0000",
            "updated": "2026-08-20T10:00:00.000+0000",
        }
        assert result[1]["author"] == "Jane"

    def test_list_empty(self) -> None:
        """Test listing comments on an issue without comments."""
        mock_client = MagicMock()
        mock_client.comments.return_value = []

        service = CommentService(mock_client)
        assert service.list("PROJ-123") == []

    def test_list_issue_not_found(self) -> None:
        """Test listing comments on a non-existent issue raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.comments.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = CommentService(mock_client)

        with pytest.raises(InvalidIssueError, match="List comments failed"):
            service.list("PROJ-999")

    def test_list_permission_denied(self) -> None:
        """Test listing comments without permission raises PermissionError."""
        mock_client = MagicMock()
        mock_client.comments.side_effect = JIRAError(status_code=403, text="Forbidden")

        service = CommentService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="Access denied"):
            service.list("PROJ-123")

    def test_list_api_error(self) -> None:
        """Test listing comments with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.comments.side_effect = JIRAError(status_code=500, text="Server error")

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.list("PROJ-123")

    def test_list_unexpected_error(self) -> None:
        """Test listing comments with an unexpected error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.comments.side_effect = ValueError("boom")

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Unexpected error listing comments"):
            service.list("PROJ-123")


class TestGetComment:
    """Test get method."""

    def test_get_success(self) -> None:
        """Test getting a single comment."""
        mock_client = MagicMock()
        mock_client.comment.return_value = _make_comment()

        service = CommentService(mock_client)
        result = service.get("PROJ-123", "10234")

        mock_client.comment.assert_called_once_with("PROJ-123", "10234")
        assert result["id"] == "10234"
        assert result["body"] == "Test comment"

    def test_get_comment_not_found(self) -> None:
        """Test getting a non-existent comment raises InvalidIssueError with a list hint."""
        mock_client = MagicMock()
        mock_client.comment.side_effect = JIRAError(status_code=404, text="Not found")

        service = CommentService(mock_client)

        with pytest.raises(InvalidIssueError, match="comment list PROJ-123"):
            service.get("PROJ-123", "99999")

    def test_get_api_error(self) -> None:
        """Test getting a comment with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.comment.side_effect = JIRAError(status_code=500, text="Server error")

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.get("PROJ-123", "10234")

    def test_get_unexpected_error(self) -> None:
        """Test getting a comment with an unexpected error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_client.comment.side_effect = ValueError("boom")

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Unexpected error fetching comment"):
            service.get("PROJ-123", "10234")


class TestUpdateComment:
    """Test update method."""

    def test_update_success(self) -> None:
        """Test updating a comment body."""
        mock_client = MagicMock()
        mock_comment = _make_comment(body="New body", updated="2026-08-23T09:00:00.000+0000")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)
        result = service.update("PROJ-123", "10234", "New body")

        mock_client.comment.assert_called_once_with("PROJ-123", "10234")
        mock_comment.update.assert_called_once_with(body="New body")
        assert result["id"] == "10234"
        assert result["body"] == "New body"
        assert result["updated"] == "2026-08-23T09:00:00.000+0000"

    def test_update_comment_not_found(self) -> None:
        """Test updating a non-existent comment raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.comment.side_effect = JIRAError(status_code=404, text="Not found")

        service = CommentService(mock_client)

        with pytest.raises(InvalidIssueError, match="comment '99999'"):
            service.update("PROJ-123", "99999", "New body")

    def test_update_permission_denied_403(self) -> None:
        """Test updating without permission (403) raises PermissionError with update hint."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.update.side_effect = JIRAError(
            status_code=403, text="You do not have permission to edit this comment"
        )
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="comment update PROJ-123 10234"):
            service.update("PROJ-123", "10234", "New body")

    def test_update_permission_denied_400(self) -> None:
        """Test Jira's 400 permission quirk on edit raises PermissionError."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.update.side_effect = JIRAError(
            status_code=400, text="You do not have the permission to edit this comment"
        )
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="permission"):
            service.update("PROJ-123", "10234", "New body")

    def test_update_api_error(self) -> None:
        """Test updating a comment with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.update.side_effect = JIRAError(status_code=500, text="Server error")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.update("PROJ-123", "10234", "New body")

    def test_update_unexpected_error(self) -> None:
        """Test updating a comment with an unexpected error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.update.side_effect = ValueError("boom")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Unexpected error updating comment"):
            service.update("PROJ-123", "10234", "New body")


class TestDeleteComment:
    """Test delete method."""

    def test_delete_success(self) -> None:
        """Test deleting a comment."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)
        service.delete("PROJ-123", "10234")

        mock_client.comment.assert_called_once_with("PROJ-123", "10234")
        mock_comment.delete.assert_called_once_with()

    def test_delete_comment_not_found(self) -> None:
        """Test deleting a non-existent comment raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.comment.side_effect = JIRAError(status_code=404, text="Not found")

        service = CommentService(mock_client)

        with pytest.raises(InvalidIssueError, match="comment '99999'"):
            service.delete("PROJ-123", "99999")

    def test_delete_permission_denied_400(self) -> None:
        """Test Jira's 400 permission quirk on delete raises PermissionError pointing at update."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.delete.side_effect = JIRAError(
            status_code=400, text="You do not have permission to delete comment with id: 10234"
        )
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="comment update PROJ-123 10234"):
            service.delete("PROJ-123", "10234")

    def test_delete_forbidden_403(self) -> None:
        """Test plain 403 on delete raises PermissionError via the base mapping."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.delete.side_effect = JIRAError(status_code=403, text="Forbidden")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="Access denied"):
            service.delete("PROJ-123", "10234")

    def test_delete_api_error(self) -> None:
        """Test deleting a comment with API error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.delete.side_effect = JIRAError(status_code=500, text="Server error")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Server error"):
            service.delete("PROJ-123", "10234")

    def test_delete_unexpected_error(self) -> None:
        """Test deleting a comment with an unexpected error raises JiraAPIError."""
        mock_client = MagicMock()
        mock_comment = _make_comment()
        mock_comment.delete.side_effect = ValueError("boom")
        mock_client.comment.return_value = mock_comment

        service = CommentService(mock_client)

        with pytest.raises(JiraAPIError, match="Unexpected error deleting comment"):
            service.delete("PROJ-123", "10234")
