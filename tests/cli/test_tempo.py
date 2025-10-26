"""Tests for Tempo CLI commands."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.tempo.models import TempoAccount, TempoAuthor, TempoIssue, TempoWorklog
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_tempo_client():
    """Mock TempoClient for testing."""
    with patch("budjira.cli.tempo.TempoClient") as mock:
        yield mock.return_value


@pytest.fixture
def mock_jira_client():
    """Mock JiraClient for testing."""
    with patch("budjira.cli.tempo.JiraClient") as mock:
        mock.from_connection.return_value.client.current_user.return_value = "557058:abc123"
        yield mock


@pytest.fixture
def mock_tempo_connection(mock_connection):
    """Create a mock connection with Tempo enabled."""
    mock_connection.tempo_enabled = True
    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.CredentialStore") as mock_store:
            mock_store.return_value.get_credential.return_value = "tempo_token_123"
            yield mock_connection


def test_tempo_log_success(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test successful worklog creation via Tempo."""
    # Mock worklog creation response
    mock_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/12345",
        tempoWorklogId=12345,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PROJ-123"),
        timeSpentSeconds=7200,
        startDate=date(2025, 10, 25),
        startTime="09:00:00",
        description="Development work",
        createdAt=datetime(2025, 10, 25, 9, 15),
        updatedAt=datetime(2025, 10, 25, 9, 15),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:abc123",
        ),
    )
    mock_tempo_client.create_worklog.return_value = mock_worklog

    result = runner.invoke(
        app,
        ["tempo", "log", "PROJ-123", "2h", "--comment", "Development work"],
    )

    assert result.exit_code == 0
    assert "Logged 2h to PROJ-123 via Tempo" in result.stdout
    assert "Tempo Worklog ID: 12345" in result.stdout
    mock_tempo_client.create_worklog.assert_called_once()


def test_tempo_log_with_started_date(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test worklog creation with custom start date."""
    mock_worklog = MagicMock()
    mock_worklog.tempoWorklogId = 54321
    mock_tempo_client.create_worklog.return_value = mock_worklog

    result = runner.invoke(
        app,
        ["tempo", "log", "PROJ-456", "3h30m", "--started", "yesterday", "--comment", "Bug fixing"],
    )

    assert result.exit_code == 0
    assert "Logged 3h30m to PROJ-456 via Tempo" in result.stdout


def test_tempo_log_tempo_not_enabled(mock_connection):
    """Test error when Tempo is not enabled for connection."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        result = runner.invoke(app, ["tempo", "log", "PROJ-123", "2h"])

        assert result.exit_code == 1
        assert "Tempo is not enabled" in result.stdout


def test_tempo_log_no_token(mock_connection):
    """Test error when Tempo token is not configured."""
    mock_connection.tempo_enabled = True

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.CredentialStore") as mock_store:
            mock_store.return_value.get_credential.return_value = None

            result = runner.invoke(app, ["tempo", "log", "PROJ-123", "2h"])

            assert result.exit_code == 1
            assert "Tempo token not found" in result.stdout


def test_tempo_worklogs_success(mock_tempo_connection, mock_tempo_client):
    """Test successful worklog listing."""
    mock_worklogs = [
        TempoWorklog(
            self="https://api.tempo.io/worklogs/1",
            tempoWorklogId=1,
            issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PROJ-123"),
            timeSpentSeconds=7200,
            startDate=date(2025, 10, 25),
            createdAt=datetime(2025, 10, 25, 9, 0),
            updatedAt=datetime(2025, 10, 25, 9, 0),
            author=TempoAuthor(
                self="https://api.tempo.io/users/1",
                accountId="557058:abc",
                displayName="John Doe",
            ),
            description="Work done",
        ),
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    result = runner.invoke(app, ["tempo", "worklogs", "PROJ-123"])

    assert result.exit_code == 0
    assert "PROJ-123" in result.stdout
    assert "2h 0m" in result.stdout
    assert "John Doe" in result.stdout


def test_tempo_worklogs_with_date_range(mock_tempo_connection, mock_tempo_client):
    """Test worklog listing with date range filter."""
    mock_tempo_client.get_worklogs.return_value = []

    result = runner.invoke(
        app,
        ["tempo", "worklogs", "--from", "2025-10-01", "--to", "2025-10-31"],
    )

    assert result.exit_code == 0
    mock_tempo_client.get_worklogs.assert_called_once()
    call_kwargs = mock_tempo_client.get_worklogs.call_args[1]
    assert call_kwargs["from_date"] == date(2025, 10, 1)
    assert call_kwargs["to_date"] == date(2025, 10, 31)


def test_tempo_worklogs_empty_results(mock_tempo_connection, mock_tempo_client):
    """Test worklog listing with no results."""
    mock_tempo_client.get_worklogs.return_value = []

    result = runner.invoke(app, ["tempo", "worklogs"])

    assert result.exit_code == 0
    assert "No worklogs found" in result.stdout


def test_tempo_worklogs_without_issue_key(mock_tempo_connection, mock_tempo_client):
    """Test worklog listing handles worklogs without issue key."""
    from datetime import date, datetime

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Create worklog without issue key
    worklog_no_key = TempoWorklog(
        self="https://api.tempo.io/worklogs/999",
        tempoWorklogId=999,
        issue=TempoIssue(self="https://api.tempo.io/issues/999"),  # No key
        timeSpentSeconds=3600,
        startDate=date(2025, 10, 25),
        createdAt=datetime(2025, 10, 25, 10, 0),
        updatedAt=datetime(2025, 10, 25, 10, 0),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:test",
            displayName="Test User",
        ),
    )
    mock_tempo_client.get_worklogs.return_value = [worklog_no_key]

    result = runner.invoke(app, ["tempo", "worklogs"])

    assert result.exit_code == 0
    assert "999" in result.stdout  # Worklog ID shown
    assert "N/A" in result.stdout or "n/a" in result.stdout.lower()  # No issue key


def test_tempo_delete_worklog_with_confirmation(mock_tempo_connection, mock_tempo_client):
    """Test worklog deletion with user confirmation."""
    result = runner.invoke(
        app,
        ["tempo", "delete-worklog", "12345"],
        input="y\n",  # Confirm deletion
    )

    assert result.exit_code == 0
    assert "Deleted Tempo worklog 12345" in result.stdout
    mock_tempo_client.delete_worklog.assert_called_once_with(12345)


def test_tempo_delete_worklog_cancelled(mock_tempo_connection, mock_tempo_client):
    """Test worklog deletion cancelled by user."""
    result = runner.invoke(
        app,
        ["tempo", "delete-worklog", "12345"],
        input="n\n",  # Cancel deletion
    )

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.stdout
    mock_tempo_client.delete_worklog.assert_not_called()


def test_tempo_delete_worklog_force(mock_tempo_connection, mock_tempo_client):
    """Test worklog deletion with --force flag."""
    result = runner.invoke(
        app,
        ["tempo", "delete-worklog", "12345", "--force"],
    )

    assert result.exit_code == 0
    assert "Deleted Tempo worklog 12345" in result.stdout
    mock_tempo_client.delete_worklog.assert_called_once_with(12345)


def test_tempo_accounts_success(mock_tempo_connection, mock_tempo_client):
    """Test successful accounts listing."""
    mock_accounts = [
        TempoAccount(
            self="https://api.tempo.io/accounts/1",
            key="ACCT-1",
            id=1,
            name="Project Account",
            status="OPEN",
        ),
        TempoAccount(
            self="https://api.tempo.io/accounts/2",
            key="ACCT-2",
            id=2,
            name="Global Account",
            status="OPEN",
        ),
    ]
    mock_tempo_client.get_accounts.return_value = mock_accounts

    result = runner.invoke(app, ["tempo", "accounts"])

    assert result.exit_code == 0
    assert "ACCT-1" in result.stdout
    assert "Project Account" in result.stdout
    assert "ACCT-2" in result.stdout


def test_tempo_accounts_empty(mock_tempo_connection, mock_tempo_client):
    """Test accounts listing with no results."""
    mock_tempo_client.get_accounts.return_value = []

    result = runner.invoke(app, ["tempo", "accounts"])

    assert result.exit_code == 0
    assert "No Tempo accounts found" in result.stdout
