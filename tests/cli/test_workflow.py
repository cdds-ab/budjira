"""Tests for workflow alias commands (start, done, block, review)."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from budjira.cli.main import app
from budjira.utils.errors import BudjiraError

runner = CliRunner()


@pytest.fixture
def mock_jira_client():
    """Mock JiraClient for testing."""
    with patch("budjira.cli.workflow.JiraClient") as mock:
        client_instance = MagicMock()
        mock.from_connection.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_connection():
    """Mock connection for testing."""
    with patch("budjira.cli.workflow.get_active_connection") as mock:
        conn = MagicMock()
        conn.name = "test-connection"
        conn.url = "https://test.atlassian.net"
        mock.return_value = conn
        yield conn


class TestStartCommand:
    """Tests for the 'start' command."""

    def test_start_issue_success(self, mock_jira_client, mock_connection):
        """Test starting an issue successfully."""
        result = runner.invoke(app, ["start", "PROJ-123"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-123", "In Progress")
        assert "PROJ-123" in result.stdout
        assert "In Progress" in result.stdout
        assert "✓" in result.stdout

    def test_start_issue_with_connection_flag(self, mock_jira_client, mock_connection):
        """Test starting an issue with explicit connection."""
        result = runner.invoke(app, ["start", "PROJ-123", "--connection", "my-conn"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-123", "In Progress")

    def test_start_issue_transition_fails(self, mock_jira_client, mock_connection):
        """Test starting an issue when transition fails."""
        mock_jira_client.transition_issue.side_effect = BudjiraError("Invalid transition")

        result = runner.invoke(app, ["start", "PROJ-123"])

        assert result.exit_code == 1
        assert "Error" in result.stdout
        assert "Invalid transition" in result.stdout

    def test_start_issue_shows_url(self, mock_jira_client, mock_connection):
        """Test that start command shows issue URL."""
        result = runner.invoke(app, ["start", "PROJ-123"])

        assert result.exit_code == 0
        assert "https://test.atlassian.net/browse/PROJ-123" in result.stdout


class TestDoneCommand:
    """Tests for the 'done' command."""

    def test_done_issue_success(self, mock_jira_client, mock_connection):
        """Test marking an issue as done successfully."""
        result = runner.invoke(app, ["done", "PROJ-456"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-456", "Done")
        assert "PROJ-456" in result.stdout
        assert "Done" in result.stdout
        assert "✓" in result.stdout

    def test_done_issue_with_connection_flag(self, mock_jira_client, mock_connection):
        """Test done command with explicit connection."""
        result = runner.invoke(app, ["done", "PROJ-456", "-c", "my-conn"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-456", "Done")

    def test_done_issue_transition_fails(self, mock_jira_client, mock_connection):
        """Test done command when transition fails."""
        mock_jira_client.transition_issue.side_effect = BudjiraError("Issue not in correct state")

        result = runner.invoke(app, ["done", "PROJ-456"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_done_issue_shows_url(self, mock_jira_client, mock_connection):
        """Test that done command shows issue URL."""
        result = runner.invoke(app, ["done", "PROJ-456"])

        assert result.exit_code == 0
        assert "https://test.atlassian.net/browse/PROJ-456" in result.stdout


class TestBlockCommand:
    """Tests for the 'block' command."""

    def test_block_issue_success(self, mock_jira_client, mock_connection):
        """Test blocking an issue successfully."""
        result = runner.invoke(app, ["block", "PROJ-789"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-789", "Blocked")
        assert "PROJ-789" in result.stdout
        assert "Blocked" in result.stdout
        assert "✓" in result.stdout

    def test_block_issue_with_connection_flag(self, mock_jira_client, mock_connection):
        """Test block command with explicit connection."""
        result = runner.invoke(app, ["block", "PROJ-789", "--connection", "my-conn"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-789", "Blocked")

    def test_block_issue_transition_fails(self, mock_jira_client, mock_connection):
        """Test block command when transition fails."""
        mock_jira_client.transition_issue.side_effect = BudjiraError("Workflow does not have Blocked state")

        result = runner.invoke(app, ["block", "PROJ-789"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_block_issue_shows_url(self, mock_jira_client, mock_connection):
        """Test that block command shows issue URL."""
        result = runner.invoke(app, ["block", "PROJ-789"])

        assert result.exit_code == 0
        assert "https://test.atlassian.net/browse/PROJ-789" in result.stdout


class TestReviewCommand:
    """Tests for the 'review' command."""

    def test_review_issue_success(self, mock_jira_client, mock_connection):
        """Test sending an issue to review successfully."""
        result = runner.invoke(app, ["review", "PROJ-111"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-111", "In Review")
        assert "PROJ-111" in result.stdout
        assert "In Review" in result.stdout
        assert "✓" in result.stdout

    def test_review_issue_with_connection_flag(self, mock_jira_client, mock_connection):
        """Test review command with explicit connection."""
        result = runner.invoke(app, ["review", "PROJ-111", "-c", "my-conn"])

        assert result.exit_code == 0
        mock_jira_client.transition_issue.assert_called_once_with("PROJ-111", "In Review")

    def test_review_issue_transition_fails(self, mock_jira_client, mock_connection):
        """Test review command when transition fails."""
        mock_jira_client.transition_issue.side_effect = BudjiraError("No In Review state in workflow")

        result = runner.invoke(app, ["review", "PROJ-111"])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_review_issue_shows_url(self, mock_jira_client, mock_connection):
        """Test that review command shows issue URL."""
        result = runner.invoke(app, ["review", "PROJ-111"])

        assert result.exit_code == 0
        assert "https://test.atlassian.net/browse/PROJ-111" in result.stdout


class TestHelpText:
    """Tests for help text and documentation."""

    def test_start_command_help(self):
        """Test that start command has helpful documentation."""
        result = runner.invoke(app, ["start", "--help"])

        assert result.exit_code == 0
        assert "Start working on an issue" in result.stdout
        assert "In Progress" in result.stdout
        assert "PROJ-123" in result.stdout

    def test_done_command_help(self):
        """Test that done command has helpful documentation."""
        result = runner.invoke(app, ["done", "--help"])

        assert result.exit_code == 0
        assert "Mark an issue as done" in result.stdout
        assert "Done" in result.stdout

    def test_block_command_help(self):
        """Test that block command has helpful documentation."""
        result = runner.invoke(app, ["block", "--help"])

        assert result.exit_code == 0
        assert "Block an issue" in result.stdout
        assert "Blocked" in result.stdout

    def test_review_command_help(self):
        """Test that review command has helpful documentation."""
        result = runner.invoke(app, ["review", "--help"])

        assert result.exit_code == 0
        assert "Send an issue to review" in result.stdout
        assert "In Review" in result.stdout
