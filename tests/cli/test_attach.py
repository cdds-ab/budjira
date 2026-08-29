"""Tests for attach CLI command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.utils.errors import (
    AuthenticationError as BudjiraAuthenticationError,
)
from budjira.utils.errors import (
    BudjiraError,
    InvalidIssueError,
    ValidationError,
)
from budjira.utils.errors import (
    ConnectionError as BudjiraConnectionError,
)
from budjira.utils.errors import (
    PermissionError as BudjiraPermissionError,
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


@pytest.fixture
def sample_files(tmp_path: Path) -> list[Path]:
    """Create two non-empty files to attach."""
    chart = tmp_path / "chart.png"
    chart.write_bytes(b"\x89PNG fake image data")
    report = tmp_path / "report.pdf"
    report.write_bytes(b"%PDF fake report")
    return [chart, report]


def _attachment_dict(file: Path, attachment_id: str) -> dict[str, object]:
    """Build an attachment dict as returned by AttachmentService.add."""
    return {
        "id": attachment_id,
        "filename": file.name,
        "size": file.stat().st_size,
        "mime_type": None,
        "content": f"https://test.atlassian.net/attachments/content/{attachment_id}",
    }


class TestAttachCommand:
    """Tests for 'budjira attach' command."""

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_single_file(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test attaching a single file."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.return_value = _attachment_dict(sample_files[0], "10001")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0])])

        assert result.exit_code == 0
        assert "Attached chart.png" in result.stdout
        mock_client.attachments.add.assert_called_once_with("TEST-123", sample_files[0])

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_multiple_files(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test attaching several files in one command."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.side_effect = [
            _attachment_dict(sample_files[0], "10001"),
            _attachment_dict(sample_files[1], "10002"),
        ]
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0]), str(sample_files[1])])

        assert result.exit_code == 0
        assert "Attached chart.png" in result.stdout
        assert "Attached report.pdf" in result.stdout
        assert mock_client.attachments.add.call_count == 2

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_json_format(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test --format json emits structured attachment data."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.return_value = _attachment_dict(sample_files[0], "10001")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["--format", "json", "attach", "TEST-123", str(sample_files[0])])

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["issue"] == "TEST-123"
        assert payload["attachments"][0]["id"] == "10001"
        assert payload["attachments"][0]["filename"] == "chart.png"

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_file_not_found(self, mock_get_conn, mock_jira_client_class, mock_connection, tmp_path):
        """Test a missing file surfaces the service's ValidationError."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.side_effect = ValidationError("File not found: 'missing.png'")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(tmp_path / "missing.png")])

        assert result.exit_code == 1
        assert "File not found" in result.stdout

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_issue_not_found(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test an unknown issue surfaces as Invalid Issue."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.side_effect = InvalidIssueError("Issue 'TEST-123' not found.")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0])])

        assert result.exit_code == 1
        assert "Invalid Issue" in result.stdout

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_permission_denied(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test lacking attachment permission is reported clearly."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.side_effect = BudjiraPermissionError("You don't have permission ...")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0])])

        assert result.exit_code == 1
        assert "Permission Denied" in result.stdout

    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_with_connection_flag(self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files):
        """Test --connection is passed through to connection resolution."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.return_value = _attachment_dict(sample_files[0], "10001")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0]), "--connection", "my-connection"])

        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("my-connection")
        assert result.exit_code == 0
        mock_get_conn.assert_called_once_with("my-connection")

    @pytest.mark.parametrize(
        ("error", "label"),
        [
            (BudjiraConnectionError("Unreachable"), "Connection Error:"),
            (BudjiraAuthenticationError("Bad token"), "Authentication Error:"),
            (BudjiraError("boom"), "Error:"),
        ],
    )
    @patch("budjira.cli.attach.JiraClient")
    @patch("budjira.cli.attach.get_active_connection")
    def test_attach_error_labels(
        self, mock_get_conn, mock_jira_client_class, mock_connection, sample_files, error, label
    ):
        """Test each error category is reported with its label."""
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_client.attachments.add.side_effect = error
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(app, ["attach", "TEST-123", str(sample_files[0])])

        assert result.exit_code == 1
        assert label in result.stdout


class TestFormatSize:
    """Unit tests for the _format_size helper."""

    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            (0, "0 B"),
            (512, "512 B"),
            (2048, "2.0 KB"),
            (5 * 1024 * 1024, "5.0 MB"),
        ],
    )
    def test_format_size(self, size, expected):
        """Byte counts are formatted as B/KB/MB."""
        from budjira.cli.attach import _format_size

        assert _format_size(size) == expected
