"""Test editor utilities."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from budjira.utils.editor import open_editor, open_editor_with_validation
from budjira.utils.errors import BudjiraError


class TestOpenEditor:
    """Test open_editor function."""

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_success(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test successful editor workflow."""
        # Setup temp file mock
        temp_path = Path("/tmp/test_editor.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        # Setup subprocess mock (editor succeeds)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Setup file reading
        test_content = "# Test Content\n\nEdited by user"
        with patch.object(Path, "read_text", return_value=test_content):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink") as mock_unlink:
                    # Execute
                    result = open_editor(initial_content="# Test Content\n\n", editor="vim")

        # Verify
        assert result == test_content
        mock_file.write.assert_called_once_with("# Test Content\n\n")
        mock_subprocess.assert_called_once_with(["vim", str(temp_path)], check=False)
        mock_unlink.assert_called_once()

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_with_default_editor(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test editor defaults to $EDITOR or vim."""
        # Setup
        temp_path = Path("/tmp/test.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test with EDITOR env var
        with patch.object(Path, "read_text", return_value="content"):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink"):
                    with patch.dict(os.environ, {"EDITOR": "nano"}):
                        open_editor()

        # Verify nano was used
        mock_subprocess.assert_called_with(["nano", str(temp_path)], check=False)

        # Test without EDITOR env var (should default to vim)
        mock_subprocess.reset_mock()
        with patch.object(Path, "read_text", return_value="content"):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink"):
                    with patch.dict(os.environ, {}, clear=True):
                        open_editor()

        # Verify vim was used as default
        mock_subprocess.assert_called_with(["vim", str(temp_path)], check=False)

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_with_custom_extension(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test editor with custom file extension."""
        # Setup
        temp_path = Path("/tmp/test.py")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Execute
        with patch.object(Path, "read_text", return_value="content"):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink"):
                    open_editor(file_extension=".py", editor="vim")

        # Verify
        mock_tempfile.assert_called_once()
        call_kwargs = mock_tempfile.call_args[1]
        assert call_kwargs["suffix"] == ".py"

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_failure(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test editor failure handling."""
        # Setup
        temp_path = Path("/tmp/test.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        # Editor exits with error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        # Execute and verify exception
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "unlink") as mock_unlink:
                with pytest.raises(BudjiraError, match="Editor exited with code 1"):
                    open_editor(editor="vim")

                # Verify temp file was cleaned up
                mock_unlink.assert_called_once()

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_unchanged_content(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test editor with unchanged content (user canceled)."""
        # Setup
        temp_path = Path("/tmp/test.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        initial = "# Initial Content\n\n"

        # Execute - content unchanged
        with patch.object(Path, "read_text", return_value=initial):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink"):
                    result = open_editor(initial_content=initial)

        # Verify - should still return content (user might just review)
        assert result == initial

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_temp_file_cleanup(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test temporary file is always cleaned up."""
        # Setup
        temp_path = Path("/tmp/test.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Test successful case
        with patch.object(Path, "read_text", return_value="content"):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "unlink") as mock_unlink:
                    open_editor()
                    mock_unlink.assert_called_once()

        # Test failure case
        mock_result.returncode = 1
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "unlink") as mock_unlink:
                with pytest.raises(BudjiraError):
                    open_editor()
                mock_unlink.assert_called_once()

    @patch("budjira.utils.editor.subprocess.run")
    @patch("budjira.utils.editor.tempfile.NamedTemporaryFile")
    def test_open_editor_temp_file_already_deleted(
        self,
        mock_tempfile: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """Test cleanup when temp file doesn't exist (already deleted)."""
        # Setup
        temp_path = Path("/tmp/test.md")
        mock_file = Mock()
        mock_file.name = str(temp_path)
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Execute - file doesn't exist
        with patch.object(Path, "read_text", return_value="content"):
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Path, "unlink") as mock_unlink:
                    result = open_editor()

        # Verify - unlink should not be called if file doesn't exist
        assert result == "content"
        mock_unlink.assert_not_called()


class TestOpenEditorWithValidation:
    """Test open_editor_with_validation function."""

    @patch("budjira.utils.editor.open_editor")
    def test_validation_success_first_attempt(self, mock_open_editor: Mock) -> None:
        """Test successful validation on first attempt."""
        # Setup
        mock_open_editor.return_value = "Valid content"

        def validator(content: str) -> tuple[bool, str]:
            return (True, "")

        # Execute
        result = open_editor_with_validation("initial", validator)

        # Verify
        assert result == "Valid content"
        mock_open_editor.assert_called_once_with("initial", editor=None)

    @patch("budjira.utils.editor.open_editor")
    @patch("budjira.utils.editor.input")
    def test_validation_retry_success(
        self,
        mock_input: Mock,
        mock_open_editor: Mock,
    ) -> None:
        """Test successful validation after retry."""
        # Setup
        mock_open_editor.side_effect = ["Invalid content", "Valid content"]
        mock_input.return_value = "y"  # User chooses to retry

        attempt_count = [0]

        def validator(content: str) -> tuple[bool, str]:
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                return (False, "First attempt invalid")
            return (True, "")

        # Execute
        result = open_editor_with_validation("initial", validator, max_attempts=3)

        # Verify
        assert result == "Valid content"
        assert mock_open_editor.call_count == 2
        mock_input.assert_called_once()

    @patch("budjira.utils.editor.open_editor")
    @patch("budjira.utils.editor.input")
    def test_validation_user_cancels(
        self,
        mock_input: Mock,
        mock_open_editor: Mock,
    ) -> None:
        """Test user cancels after validation failure."""
        # Setup
        mock_open_editor.return_value = "Invalid content"
        mock_input.return_value = "n"  # User chooses not to retry

        def validator(content: str) -> tuple[bool, str]:
            return (False, "Content is invalid")

        # Execute and verify exception
        with pytest.raises(BudjiraError, match="Validation failed, user canceled"):
            open_editor_with_validation("initial", validator)

        mock_input.assert_called_once()

    @patch("budjira.utils.editor.open_editor")
    @patch("budjira.utils.editor.input")
    def test_validation_max_attempts_exceeded(
        self,
        mock_input: Mock,
        mock_open_editor: Mock,
    ) -> None:
        """Test validation fails after max attempts."""
        # Setup
        mock_open_editor.return_value = "Invalid content"
        mock_input.return_value = "y"  # User keeps retrying

        def validator(content: str) -> tuple[bool, str]:
            return (False, "Always invalid")

        # Execute and verify exception
        with pytest.raises(BudjiraError, match="Validation failed after 3 attempts"):
            open_editor_with_validation("initial", validator, max_attempts=3)

        assert mock_open_editor.call_count == 3
        assert mock_input.call_count == 2  # Asked to retry twice (not on last attempt)

    @patch("budjira.utils.editor.open_editor")
    def test_validation_with_custom_editor(self, mock_open_editor: Mock) -> None:
        """Test validation with custom editor."""
        # Setup
        mock_open_editor.return_value = "Valid content"

        def validator(content: str) -> tuple[bool, str]:
            return (True, "")

        # Execute
        result = open_editor_with_validation("initial", validator, editor="nano")

        # Verify
        assert result == "Valid content"
        mock_open_editor.assert_called_once_with("initial", editor="nano")

    @patch("budjira.utils.editor.open_editor")
    @patch("budjira.utils.editor.input")
    @patch("budjira.utils.editor.print")
    def test_validation_error_messages_shown(
        self,
        mock_print: Mock,
        mock_input: Mock,
        mock_open_editor: Mock,
    ) -> None:
        """Test validation error messages are shown to user."""
        # Setup
        mock_open_editor.side_effect = ["Invalid 1", "Valid content"]
        mock_input.return_value = "y"

        attempt_count = [0]

        def validator(content: str) -> tuple[bool, str]:
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                return (False, "Error: Missing required section")
            return (True, "")

        # Execute
        result = open_editor_with_validation("initial", validator)

        # Verify
        assert result == "Valid content"
        # Check that error message was printed
        mock_print.assert_called_with("\nError: Missing required section\n")

    @patch("budjira.utils.editor.open_editor")
    @patch("budjira.utils.editor.input")
    def test_validation_multiple_retries(
        self,
        mock_input: Mock,
        mock_open_editor: Mock,
    ) -> None:
        """Test multiple validation retries."""
        # Setup
        mock_open_editor.side_effect = ["Invalid 1", "Invalid 2", "Valid content"]
        mock_input.return_value = "yes"  # User keeps retrying

        attempt_count = [0]

        def validator(content: str) -> tuple[bool, str]:
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                return (False, f"Attempt {attempt_count[0]} failed")
            return (True, "")

        # Execute
        result = open_editor_with_validation("initial", validator, max_attempts=5)

        # Verify
        assert result == "Valid content"
        assert mock_open_editor.call_count == 3
        assert mock_input.call_count == 2
