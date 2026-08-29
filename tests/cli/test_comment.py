"""Tests for comment CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.utils.errors import (
    InvalidIssueError,
    PermissionError,
    ValidationError,
)
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_connection():
    """Create a mock connection."""
    return Connection(
        name="test-conn",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@example.com",
        project_key="TEST",
    )


class TestCommentAddCommand:
    """Tests for 'budjira comment add' command."""

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_success(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding comment successfully."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_comment.return_value = {
            "id": "12345",
            "author": "John Doe",
            "body": "Test comment",
            "created": "2025-11-04T10:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-123", "Test comment"],
        )

        assert result.exit_code == 0
        assert "Comment added to TEST-123" in result.stdout
        assert "Comment ID: 12345" in result.stdout
        assert "Author: John Doe" in result.stdout

        mock_client.add_comment.assert_called_once_with("TEST-123", "Test comment")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_multiline_text(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding multi-line comment via argument."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        multiline_text = "Line 1\nLine 2\nLine 3"
        mock_client.add_comment.return_value = {
            "id": "12346",
            "author": "Jane Smith",
            "body": multiline_text,
            "created": "2025-11-04T11:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-456", multiline_text],
        )

        assert result.exit_code == 0
        assert "Comment added to TEST-456" in result.stdout
        mock_client.add_comment.assert_called_once_with("TEST-456", multiline_text)

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_with_editor_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_open_editor,
        mock_connection,
    ):
        """Test adding comment with --editor flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        editor_text = "Comment from editor\nWith multiple lines"
        mock_open_editor.return_value = editor_text
        mock_client.add_comment.return_value = {
            "id": "12347",
            "author": "Bob Builder",
            "body": editor_text,
            "created": "2025-11-04T12:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-789", "Initial text", "--editor"],
        )

        assert result.exit_code == 0
        assert "Comment added to TEST-789" in result.stdout

        # Editor should be opened with initial text
        mock_open_editor.assert_called_once_with("Initial text", file_extension=".md")
        mock_client.add_comment.assert_called_once_with("TEST-789", editor_text)

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_no_text_opens_editor(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_open_editor,
        mock_connection,
    ):
        """Test that omitting text opens editor."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        editor_text = "Comment from editor"
        mock_open_editor.return_value = editor_text
        mock_client.add_comment.return_value = {
            "id": "12348",
            "author": "Alice",
            "body": editor_text,
            "created": "2025-11-04T13:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-100"],
        )

        assert result.exit_code == 0
        assert "Comment added to TEST-100" in result.stdout

        # Editor should be opened with empty content
        mock_open_editor.assert_called_once_with("", file_extension=".md")
        mock_client.add_comment.assert_called_once_with("TEST-100", editor_text)

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_empty_editor_aborts(
        self,
        mock_get_conn,
        mock_open_editor,
        mock_connection,
    ):
        """Test that empty editor content aborts."""
        mock_get_conn.return_value = mock_connection
        mock_open_editor.return_value = "   "  # Only whitespace

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-200"],
        )

        # Exit code is 1 because typer.Exit(0) is caught by exception handler
        # But the message should still be shown
        assert "No comment text provided. Aborting." in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_with_connection_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding comment with --connection flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_comment.return_value = {
            "id": "12349",
            "author": "Charlie",
            "body": "Test",
            "created": "2025-11-04T14:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-300", "Test", "--connection", "custom-conn"],
        )

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("custom-conn")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_issue_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding comment to non-existent issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_comment.side_effect = InvalidIssueError("Issue 'TEST-999' not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-999", "Comment"],
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "not found" in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_permission_denied(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test adding comment without permission."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.add_comment.side_effect = PermissionError("You don't have permission to comment")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-400", "Comment"],
        )

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "permission" in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_comment_shows_preview(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test that comment preview is shown."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        long_comment = "a" * 150  # Long comment to test truncation
        mock_client.add_comment.return_value = {
            "id": "12350",
            "author": "Dave",
            "body": long_comment,
            "created": "2025-11-04T15:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-500", long_comment],
        )

        assert result.exit_code == 0
        assert "Preview:" in result.stdout
        # Should be truncated to 100 chars + "..." (with potential newline formatting)
        assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in result.stdout
        assert "..." in result.stdout


def _comment_dict(
    comment_id: str = "10234",
    author: str = "John Doe",
    body: str = "Test comment",
    created: str = "2026-08-20T10:00:00.000+0000",
    updated: str = "2026-08-20T10:00:00.000+0000",
):
    """Create a comment dictionary as returned by CommentService."""
    return {
        "id": comment_id,
        "author": author,
        "body": body,
        "created": created,
        "updated": updated,
    }


class TestCommentListCommand:
    """Tests for 'budjira comment list' command."""

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_list_comments_success(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing comments shows a table with id, author and preview."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.list.return_value = [
            _comment_dict("10234", "John Doe", "First comment\nwith second line"),
            _comment_dict("10235", "Jane Smith", "Second comment"),
        ]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "list", "TEST-123"])

        assert result.exit_code == 0
        assert "Comments on TEST-123" in result.stdout
        assert "10234" in result.stdout
        assert "John Doe" in result.stdout
        assert "First comment" in result.stdout
        assert "with second line" not in result.stdout
        assert "Total: 2 comment(s)" in result.stdout

        mock_client.comments.list.assert_called_once_with("TEST-123")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_list_comments_empty(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing comments on an issue without comments."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.list.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "list", "TEST-123"])

        assert result.exit_code == 0
        assert "No comments found on TEST-123" in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_list_comments_json_format(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing comments with --format json."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.list.return_value = [_comment_dict()]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["--format", "json", "comment", "list", "TEST-123"])

        assert result.exit_code == 0
        assert '"issue": "TEST-123"' in result.stdout
        assert '"total": 1' in result.stdout
        assert '"id": "10234"' in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_list_comments_with_connection_flag(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing comments with --connection flag."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.list.return_value = []
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "list", "TEST-123", "--connection", "custom-conn"])

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("custom-conn")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_list_comments_issue_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test listing comments on a non-existent issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.list.side_effect = InvalidIssueError("Issue 'TEST-999' not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "list", "TEST-999"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "not found" in result.stdout


class TestCommentShowCommand:
    """Tests for 'budjira comment show' command."""

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_show_comment_success(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test showing a comment prints the full body."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.get.return_value = _comment_dict(body="Line 1\nLine 2\nLine 3")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "show", "TEST-123", "10234"])

        assert result.exit_code == 0
        assert "Comment 10234 on TEST-123" in result.stdout
        assert "John Doe" in result.stdout
        assert "Line 1" in result.stdout
        assert "Line 2" in result.stdout
        assert "Line 3" in result.stdout

        mock_client.comments.get.assert_called_once_with("TEST-123", "10234")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_show_comment_json_format(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test showing a comment with --format json."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.get.return_value = _comment_dict()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["--format", "json", "comment", "show", "TEST-123", "10234"])

        assert result.exit_code == 0
        assert '"id": "10234"' in result.stdout
        assert '"body": "Test comment"' in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_show_comment_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test showing a non-existent comment."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.get.side_effect = InvalidIssueError("Issue 'TEST-123' or comment '99999' not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "show", "TEST-123", "99999"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "not found" in result.stdout


class TestCommentUpdateCommand:
    """Tests for 'budjira comment update' command."""

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_with_text(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test updating a comment with positional text."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.update.return_value = _comment_dict(
            body="Corrected text", updated="2026-08-23T09:00:00.000+0000"
        )
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "10234", "Corrected text"])

        assert result.exit_code == 0
        assert "Comment 10234 on TEST-123 updated" in result.stdout
        mock_client.comments.update.assert_called_once_with("TEST-123", "10234", "Corrected text")
        # No editor round-trip when text is given
        mock_client.comments.get.assert_not_called()

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_editor_prefilled_with_current_body(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_open_editor,
        mock_connection,
    ):
        """Test that omitting text opens the editor prefilled with the current body."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.get.return_value = _comment_dict(body="Current body")
        mock_open_editor.return_value = "Tightened body"
        mock_client.comments.update.return_value = _comment_dict(body="Tightened body")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "10234"])

        assert result.exit_code == 0
        mock_client.comments.get.assert_called_once_with("TEST-123", "10234")
        mock_open_editor.assert_called_once_with("Current body", file_extension=".md")
        mock_client.comments.update.assert_called_once_with("TEST-123", "10234", "Tightened body")

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_editor_flag_with_text(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_open_editor,
        mock_connection,
    ):
        """Test --editor with text opens the editor with that text (parity with add)."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_open_editor.return_value = "Edited text"
        mock_client.comments.update.return_value = _comment_dict(body="Edited text")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "10234", "Draft text", "--editor"])

        assert result.exit_code == 0
        mock_open_editor.assert_called_once_with("Draft text", file_extension=".md")
        mock_client.comments.get.assert_not_called()
        mock_client.comments.update.assert_called_once_with("TEST-123", "10234", "Edited text")

    @patch("budjira.cli.comment.open_editor")
    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_empty_editor_aborts(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_open_editor,
        mock_connection,
    ):
        """Test that empty editor content aborts without an API call."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.get.return_value = _comment_dict(body="Current body")
        mock_open_editor.return_value = "   "
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "10234"])

        assert result.exit_code == 0
        assert "No comment text provided. Aborting." in result.stdout
        mock_client.comments.update.assert_not_called()

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_permission_denied(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test updating without permission surfaces the error."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.update.side_effect = PermissionError("You do not have permission to edit this comment")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "10234", "New text"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "permission" in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_update_comment_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test updating a non-existent comment."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.update.side_effect = InvalidIssueError("Issue 'TEST-123' or comment '99999' not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "update", "TEST-123", "99999", "New text"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "not found" in result.stdout


class TestCommentDeleteCommand:
    """Tests for 'budjira comment delete' command."""

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_delete_comment_with_confirmation(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting a comment after confirming the prompt."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "delete", "TEST-123", "10234"], input="y\n")

        assert result.exit_code == 0
        assert "Comment 10234 deleted from TEST-123" in result.stdout
        mock_client.comments.delete.assert_called_once_with("TEST-123", "10234")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_delete_comment_cancelled(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test that declining the prompt cancels the deletion."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "delete", "TEST-123", "10234"], input="n\n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.stdout
        mock_client.comments.delete.assert_not_called()

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_delete_comment_force_skips_confirmation(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting a comment with --force skips the prompt."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "delete", "TEST-123", "10234", "--force"])

        assert result.exit_code == 0
        assert "Comment 10234 deleted from TEST-123" in result.stdout
        mock_client.comments.delete.assert_called_once_with("TEST-123", "10234")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_delete_comment_permission_denied_points_to_update(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test that a delete permission error surfaces the update hint (Jira 400 quirk)."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.delete.side_effect = PermissionError(
            "Delete comment failed: You do not have permission to delete comment with id: 10234 "
            "Use 'budjira comment update TEST-123 10234' to revise the body instead."
        )
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "delete", "TEST-123", "10234", "--force"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "permission" in result.stdout
        assert "comment update TEST-123 10234" in result.stdout

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_delete_comment_not_found(
        self,
        mock_get_conn,
        mock_jira_client_class,
        mock_connection,
    ):
        """Test deleting a non-existent comment."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.comments.delete.side_effect = InvalidIssueError("Issue 'TEST-123' or comment '99999' not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["comment", "delete", "TEST-123", "99999", "--force"])

        assert result.exit_code == 1
        assert "Error:" in result.stdout
        assert "not found" in result.stdout


class TestCommentAddAttachHelpers:
    """Unit tests for the attachment reference helpers."""

    def test_is_image(self):
        """Known image extensions are detected case-insensitively."""
        from budjira.cli.comment import _is_image

        assert _is_image("chart.png")
        assert _is_image("PHOTO.JPG")
        assert _is_image("anim.webp")
        assert not _is_image("report.pdf")
        assert not _is_image("archive.zip")

    def test_append_attachment_refs_image(self):
        """Images are referenced with wiki !file! markup."""
        from budjira.cli.comment import _append_attachment_refs

        result = _append_attachment_refs("See below", [{"filename": "chart.png"}])
        assert result == "See below\n!chart.png!"

    def test_append_attachment_refs_file(self):
        """Non-image files are referenced with wiki [^file] markup."""
        from budjira.cli.comment import _append_attachment_refs

        result = _append_attachment_refs("Details", [{"filename": "report.pdf"}])
        assert result == "Details\n[^report.pdf]"

    def test_append_attachment_refs_empty_text(self):
        """Without text the references stand alone."""
        from budjira.cli.comment import _append_attachment_refs

        result = _append_attachment_refs("", [{"filename": "chart.png"}])
        assert result == "!chart.png!"

    def test_build_adf_comment_text_and_media(self):
        """ADF doc has paragraphs first, then one mediaSingle per embedded file."""
        from budjira.cli.comment import _build_adf_comment

        doc = _build_adf_comment(
            "Before/after:\nsecond line",
            [{"id": "10001", "filename": "chart.png"}],
            [{"id": "10002", "filename": "report.pdf"}],
        )

        assert doc["type"] == "doc"
        assert doc["version"] == 1
        paragraphs = [node for node in doc["content"] if node["type"] == "paragraph"]
        media = [node for node in doc["content"] if node["type"] == "mediaSingle"]
        assert [p["content"][0]["text"] for p in paragraphs] == ["Before/after:", "second line", "Attached: report.pdf"]
        assert len(media) == 1
        assert media[0]["content"][0]["type"] == "media"
        assert media[0]["content"][0]["attrs"] == {"id": "10001", "type": "file"}

    def test_build_adf_comment_media_only(self):
        """An ADF doc without text is valid when it carries media nodes."""
        from budjira.cli.comment import _build_adf_comment

        doc = _build_adf_comment("", [{"id": "10001", "filename": "chart.png"}], [])

        assert len(doc["content"]) == 1
        assert doc["content"][0]["type"] == "mediaSingle"


class TestCommentAddAttachments:
    """Tests for 'budjira comment add --attach/--embed' (#115)."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a non-empty image file."""
        file = tmp_path / "chart.png"
        file.write_bytes(b"\x89PNG fake image data")
        return file

    def _wire_client(
        self, mock_jira_client_class: MagicMock, *, filename: str = "chart.png", attachment_id: str = "10001"
    ) -> MagicMock:
        """Wire a JiraClient mock with attachment upload and comment creation."""
        mock_client = MagicMock()
        mock_client.attachments.add.return_value = {
            "id": attachment_id,
            "filename": filename,
            "size": 100,
            "mime_type": "image/png",
            "content": f"https://test.atlassian.net/attachments/content/{attachment_id}",
        }
        mock_client.add_comment.return_value = {
            "id": "20001",
            "author": "John Doe",
            "created": "2026-08-20T10:00:00.000+0000",
        }
        mock_client.comments.add_adf.return_value = {
            "id": "20002",
            "author": "John Doe",
            "created": "2026-08-20T10:00:00.000+0000",
        }
        mock_jira_client_class.from_connection.return_value = mock_client
        return mock_client

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_with_attach_image(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_file):
        """--attach uploads the file and references it via wiki markup."""
        mock_get_conn.return_value = mock_connection
        mock_client = self._wire_client(mock_jira_client_class)

        result = runner.invoke(app, ["comment", "add", "TEST-123", "See the chart", "--attach", str(sample_file)])

        assert result.exit_code == 0
        assert "Attached: chart.png" in result.stdout
        mock_client.attachments.add.assert_called_once_with("TEST-123", sample_file)
        mock_client.add_comment.assert_called_once_with("TEST-123", "See the chart\n!chart.png!")
        mock_client.comments.add_adf.assert_not_called()

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_with_attach_no_text_skips_editor(
        self, mock_get_conn, mock_jira_client_class, mock_connection, sample_file
    ):
        """Files alone carry the comment; the editor does not open."""
        mock_get_conn.return_value = mock_connection
        mock_client = self._wire_client(mock_jira_client_class)

        with patch("budjira.cli.comment.open_editor") as mock_editor:
            result = runner.invoke(app, ["comment", "add", "TEST-123", "--attach", str(sample_file)])

        assert result.exit_code == 0
        mock_editor.assert_not_called()
        mock_client.add_comment.assert_called_once_with("TEST-123", "!chart.png!")

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_with_embed_uses_adf(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_file):
        """--embed uploads and posts an ADF comment with a mediaSingle node."""
        mock_get_conn.return_value = mock_connection
        mock_client = self._wire_client(mock_jira_client_class)

        result = runner.invoke(app, ["comment", "add", "TEST-123", "Before/after:", "--embed", str(sample_file)])

        assert result.exit_code == 0
        assert "Embedded: chart.png" in result.stdout
        mock_client.attachments.add.assert_called_once_with("TEST-123", sample_file)
        mock_client.add_comment.assert_not_called()
        mock_client.comments.add_adf.assert_called_once()
        issue_key, doc = mock_client.comments.add_adf.call_args.args
        assert issue_key == "TEST-123"
        assert doc["type"] == "doc"
        media = [node for node in doc["content"] if node["type"] == "mediaSingle"]
        assert media[0]["content"][0]["attrs"]["id"] == "10001"

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_with_attach_and_embed(
        self, mock_get_conn, mock_jira_client_class, mock_connection, sample_file, tmp_path
    ):
        """--attach and --embed combine into one ADF comment."""
        report = tmp_path / "report.pdf"
        report.write_bytes(b"%PDF fake report")
        mock_get_conn.return_value = mock_connection
        mock_client = self._wire_client(mock_jira_client_class)
        mock_client.attachments.add.side_effect = [
            {"id": "10001", "filename": "chart.png", "size": 100, "mime_type": "image/png", "content": ""},
            {"id": "10002", "filename": "report.pdf", "size": 100, "mime_type": "application/pdf", "content": ""},
        ]

        result = runner.invoke(
            app,
            ["comment", "add", "TEST-123", "Results", "--embed", str(sample_file), "--attach", str(report)],
        )

        assert result.exit_code == 0
        assert mock_client.attachments.add.call_count == 2
        mock_client.add_comment.assert_not_called()
        doc = mock_client.comments.add_adf.call_args.args[1]
        texts = [
            node["content"][0]["text"] for node in doc["content"] if node["type"] == "paragraph" and node.get("content")
        ]
        assert "Attached: report.pdf" in texts

    @patch("budjira.cli.comment.JiraClient")
    @patch("budjira.cli.comment.get_active_connection")
    def test_add_attach_upload_fails(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_file):
        """A failed upload aborts before the comment is posted."""
        mock_get_conn.return_value = mock_connection
        mock_client = self._wire_client(mock_jira_client_class)
        mock_client.attachments.add.side_effect = ValidationError("File is empty: 'chart.png'")

        result = runner.invoke(app, ["comment", "add", "TEST-123", "text", "--attach", str(sample_file)])

        assert result.exit_code == 1
        assert "File is empty" in result.stdout
        mock_client.add_comment.assert_not_called()
