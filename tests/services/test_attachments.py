# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for attachment service."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from budjira.services.attachments import AttachmentService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, ValidationError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


def _make_attachment(
    attachment_id: str = "10001",
    filename: str = "chart.png",
    size: int = 12345,
) -> MagicMock:
    """Create a mock jira Attachment resource."""
    attachment = MagicMock()
    attachment.id = attachment_id
    attachment.filename = filename
    attachment.size = size
    attachment.mimeType = "image/png"
    attachment.content = f"https://test.atlassian.net/attachments/content/{attachment_id}"
    return attachment


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a non-empty file to upload."""
    file = tmp_path / "chart.png"
    file.write_bytes(b"\x89PNG fake image data")
    return file


class TestAddAttachment:
    """Test add method."""

    def test_add_success(self, sample_file: Path) -> None:
        """Test uploading a file returns attachment details including the id."""
        mock_client = MagicMock()
        mock_client.add_attachment.return_value = _make_attachment()

        service = AttachmentService(mock_client)
        result = service.add("PROJ-123", sample_file)

        assert result == {
            "id": "10001",
            "filename": "chart.png",
            "size": 12345,
            "mime_type": "image/png",
            "content": "https://test.atlassian.net/attachments/content/10001",
        }
        call_kwargs = mock_client.add_attachment.call_args.kwargs
        assert call_kwargs["issue"] == "PROJ-123"
        assert call_kwargs["filename"] == "chart.png"
        # The file handle must be closed after upload
        assert call_kwargs["attachment"].closed

    def test_add_file_not_found(self, tmp_path: Path) -> None:
        """Test a missing file raises ValidationError before any API call."""
        mock_client = MagicMock()
        service = AttachmentService(mock_client)

        with pytest.raises(ValidationError, match="File not found"):
            service.add("PROJ-123", tmp_path / "missing.png")

        mock_client.add_attachment.assert_not_called()

    def test_add_empty_file(self, tmp_path: Path) -> None:
        """Test an empty file is rejected locally (Jira rejects empty uploads)."""
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")

        service = AttachmentService(MagicMock())
        with pytest.raises(ValidationError, match="File is empty"):
            service.add("PROJ-123", empty)

    def test_add_issue_not_found(self, sample_file: Path) -> None:
        """Test 404 raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.add_attachment.side_effect = JIRAError(status_code=404, text="Issue does not exist")

        service = AttachmentService(mock_client)
        with pytest.raises(InvalidIssueError, match="PROJ-123"):
            service.add("PROJ-123", sample_file)

    def test_add_permission_denied(self, sample_file: Path) -> None:
        """Test 403 raises PermissionError."""
        mock_client = MagicMock()
        mock_client.add_attachment.side_effect = JIRAError(status_code=403, text="Forbidden")

        service = AttachmentService(mock_client)
        with pytest.raises(BudjiraPermissionError, match="permission"):
            service.add("PROJ-123", sample_file)

    def test_add_api_error(self, sample_file: Path) -> None:
        """Test other JIRA errors raise JiraAPIError."""
        mock_client = MagicMock()
        mock_client.add_attachment.side_effect = JIRAError(status_code=500, text="Internal Server Error")

        service = AttachmentService(mock_client)
        with pytest.raises(JiraAPIError, match="Add attachment failed"):
            service.add("PROJ-123", sample_file)
