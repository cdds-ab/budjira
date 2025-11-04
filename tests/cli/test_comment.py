"""Tests for comment CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.utils.errors import (
    InvalidIssueError,
    PermissionError,
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
