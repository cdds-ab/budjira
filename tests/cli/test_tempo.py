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
        # Mock myself() API call to return accountId (Bug #5 fix)
        mock.from_connection.return_value.client.myself.return_value = {
            "accountId": "557058:abc123",
            "emailAddress": "test@example.com",
            "displayName": "Test User",
        }
        # Mock issue() API call to return numeric ID (Bug #5 fix continued)
        mock_issue = MagicMock()
        mock_issue.id = "12345"  # Jira returns as string
        mock_issue.key = "PROJ-123"
        mock.from_connection.return_value.client.issue.return_value = mock_issue
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


def test_tempo_log_passes_correct_account_id(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test that tempo log correctly retrieves and passes Jira accountId to Tempo API (Bug #5).

    Regression test for Bug #5: tempo log must use myself() to get accountId,
    not current_user() which returns username.
    """
    # Mock Jira API myself() response with accountId
    mock_jira_client.from_connection.return_value.client.myself.return_value = {
        "accountId": "557058:abc123def456",
        "emailAddress": "user@example.com",
        "displayName": "Test User",
    }

    # Mock successful worklog creation
    mock_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/99999",
        tempoWorklogId=99999,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-1"),
        timeSpentSeconds=1800,
        startDate=date(2025, 10, 26),
        startTime="09:00:00",
        description="Testing accountId",
        createdAt=datetime(2025, 10, 26, 9, 0),
        updatedAt=datetime(2025, 10, 26, 9, 0),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:abc123def456",
        ),
    )
    mock_tempo_client.create_worklog.return_value = mock_worklog

    result = runner.invoke(
        app,
        ["tempo", "log", "TEST-1", "30m", "--comment", "Testing accountId"],
    )

    assert result.exit_code == 0

    # CRITICAL: Verify that create_worklog was called with the correct accountId
    mock_tempo_client.create_worklog.assert_called_once()
    call_kwargs = mock_tempo_client.create_worklog.call_args[1]
    assert (
        call_kwargs["author_account_id"] == "557058:abc123def456"
    ), "author_account_id must be the Jira accountId from myself() API, not the username from current_user()"


def test_tempo_log_uses_issue_id_not_key(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test that tempo log uses numeric issueId from Jira API, not issueKey (Bug #5 continued).

    Regression test: Tempo API requires issueId (numeric like 12345), not issueKey (string like "AS-13").
    The code must fetch the issue from Jira API to get the numeric ID.

    Root cause from user's curl test:
    {"errors":[{"message":"Issue id cannot be null"}]}
    """
    # Mock Jira API myself() response
    mock_jira_client.from_connection.return_value.client.myself.return_value = {
        "accountId": "557058:testuser",
        "emailAddress": "test@example.com",
    }

    # Mock Jira API issue() response with numeric ID
    mock_issue = MagicMock()
    mock_issue.id = "12345"  # Jira returns this as string
    mock_issue.key = "AS-13"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    # Mock successful Tempo worklog creation
    mock_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/88888",
        tempoWorklogId=88888,
        issue=TempoIssue(self="https://api.tempo.io/issues/12345", key="AS-13", id=12345),
        timeSpentSeconds=1800,
        startDate=date(2025, 10, 26),
        startTime="09:00:00",
        description="Testing issueId",
        createdAt=datetime(2025, 10, 26, 10, 0),
        updatedAt=datetime(2025, 10, 26, 10, 0),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:testuser",
        ),
    )
    mock_tempo_client.create_worklog.return_value = mock_worklog

    result = runner.invoke(
        app,
        ["tempo", "log", "AS-13", "30m", "--comment", "Testing issueId"],
    )

    assert result.exit_code == 0

    # CRITICAL 1: Verify Jira API was called to fetch the issue (to get numeric ID)
    mock_jira_client.from_connection.return_value.client.issue.assert_called_once_with("AS-13")

    # CRITICAL 2: Verify that create_worklog was called with numeric issueId, NOT issueKey
    mock_tempo_client.create_worklog.assert_called_once()
    call_kwargs = mock_tempo_client.create_worklog.call_args[1]
    assert "issue_id" in call_kwargs, "Tempo API requires 'issue_id' parameter"
    assert call_kwargs["issue_id"] == 12345, (
        "issue_id must be numeric ID (12345) from Jira API, "
        "not issueKey string ('AS-13'). Tempo returns: "
        '{"errors":[{"message":"Issue id cannot be null"}]}'
    )
    assert "issue_key" not in call_kwargs, "issue_key should not be sent to Tempo API, only issue_id"


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


def test_tempo_worklogs_success(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test successful worklog listing with issue filter."""
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

    # Verify that get_worklogs was called with numeric issue_id, not issue_key
    mock_tempo_client.get_worklogs.assert_called_once()
    call_kwargs = mock_tempo_client.get_worklogs.call_args[1]
    assert "issue_id" in call_kwargs
    assert call_kwargs["issue_id"] == 12345  # Numeric ID from mock_jira_client
    assert "issue_key" not in call_kwargs


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


def test_tempo_worklogs_uses_issue_id_not_key(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test that tempo worklogs uses numeric issueId for filtering (Bug #7).

    Regression test for Bug #7: tempo worklogs ISSUE-KEY fails with 400 Bad Request.
    The Tempo API requires numeric issueId (like 12345) not issueKey (like "AS-13")
    when filtering worklogs by issue.

    Root cause from user report:
    400 Client Error: Bad Request for url: https://api.tempo.io/4/worklogs?issue=AS-13
    """
    # Mock Jira API issue() response with numeric ID
    mock_issue = MagicMock()
    mock_issue.id = "12345"  # Jira returns as string
    mock_issue.key = "AS-13"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    # Mock empty worklog response
    mock_tempo_client.get_worklogs.return_value = []

    result = runner.invoke(app, ["tempo", "worklogs", "AS-13"])
    assert result.exit_code == 0

    # CRITICAL 1: Verify Jira API was called to fetch the issue (to get numeric ID)
    mock_jira_client.from_connection.return_value.client.issue.assert_called_once_with("AS-13")

    # CRITICAL 2: Verify that get_worklogs was called with numeric issue_id, NOT issue_key
    mock_tempo_client.get_worklogs.assert_called_once()
    call_kwargs = mock_tempo_client.get_worklogs.call_args[1]
    assert "issue_id" in call_kwargs, "Tempo API requires 'issue_id' parameter"
    assert call_kwargs["issue_id"] == 12345, (
        "issue_id must be numeric ID (12345) from Jira API, "
        "not issueKey string ('AS-13'). Tempo returns 400 Bad Request otherwise."
    )
    assert "issue_key" not in call_kwargs, "issue_key should not be sent to Tempo API, only issue_id"


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


# JSON Output Tests (Feature Request #8)


def test_tempo_worklogs_json_output(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test tempo worklogs with JSON output format."""
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock worklogs
    mock_worklogs = [
        TempoWorklog(
            self="https://api.tempo.io/worklogs/100",
            tempoWorklogId=100,
            issue=TempoIssue(self="https://api.tempo.io/issues/1", key="TEST-1"),
            timeSpentSeconds=3600,
            startDate=date(2025, 10, 26),
            startTime="09:00:00",
            description="Test work",
            createdAt=datetime(2025, 10, 26, 9, 0),
            updatedAt=datetime(2025, 10, 26, 9, 0),
            author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="123"),
        ),
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Mock epic fetching
    mock_jira_client.from_connection.return_value.get_issue_epic.return_value = ("EPIC-1", "Test Epic")

    # Run command with --format json
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)
    assert output["total"] == 1
    assert len(output["worklogs"]) == 1

    worklog = output["worklogs"][0]
    assert worklog["id"] == 100
    assert worklog["issue_key"] == "TEST-1"
    assert worklog["time_spent_seconds"] == 3600
    assert worklog["time_spent_display"] == "1h 0m"
    assert worklog["date"] == "2025-10-26"
    assert worklog["epic_key"] == "EPIC-1"
    assert worklog["epic_name"] == "Test Epic"


def test_tempo_worklogs_json_no_epic_flag(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test tempo worklogs JSON output with --no-epic flag (performance mode)."""
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock worklogs
    mock_worklogs = [
        TempoWorklog(
            self="https://api.tempo.io/worklogs/100",
            tempoWorklogId=100,
            issue=TempoIssue(self="https://api.tempo.io/issues/1", key="TEST-1"),
            timeSpentSeconds=1800,
            startDate=date(2025, 10, 26),
            startTime="09:00:00",
            description="Test work",
            createdAt=datetime(2025, 10, 26, 9, 0),
            updatedAt=datetime(2025, 10, 26, 9, 0),
            author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="123", displayName="Test User"),
        ),
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Run command with --format json --no-epic
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs", "--no-epic"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)
    assert output["total"] == 1

    worklog = output["worklogs"][0]
    assert worklog["id"] == 100
    assert worklog["time_spent_display"] == "30m"
    assert worklog["author_display_name"] == "Test User"
    # Epic fields should not be present when --no-epic is used
    assert "epic_key" not in worklog
    assert "epic_name" not in worklog

    # Verify get_issue_epic was NOT called (performance optimization)
    mock_jira_client.from_connection.return_value.get_issue_epic.assert_not_called()


def test_tempo_worklogs_json_empty_results(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test tempo worklogs JSON output with no results."""
    import json

    mock_tempo_client.get_worklogs.return_value = []

    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # Parse JSON output
    output = json.loads(result.stdout)
    assert output["total"] == 0
    assert output["worklogs"] == []


def test_tempo_worklogs_json_epic_caching(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test that epic information is cached when multiple worklogs have same issue."""
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock 3 worklogs on the same issue
    mock_worklogs = [
        TempoWorklog(
            self=f"https://api.tempo.io/worklogs/{i}",
            tempoWorklogId=i,
            issue=TempoIssue(self="https://api.tempo.io/issues/1", key="TEST-1"),
            timeSpentSeconds=3600,
            startDate=date(2025, 10, 26),
            startTime="09:00:00",
            description=f"Work {i}",
            createdAt=datetime(2025, 10, 26, 9, 0),
            updatedAt=datetime(2025, 10, 26, 9, 0),
            author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="123"),
        )
        for i in range(1, 4)
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Mock epic fetching
    mock_jira_client.from_connection.return_value.get_issue_epic.return_value = ("EPIC-1", "Test Epic")

    # Run command
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # Verify epic was fetched only ONCE (cached for subsequent worklogs)
    assert mock_jira_client.from_connection.return_value.get_issue_epic.call_count == 1

    # Parse JSON output - all worklogs should have epic info
    output = json.loads(result.stdout)
    assert output["total"] == 3
    for worklog in output["worklogs"]:
        assert worklog["epic_key"] == "EPIC-1"
        assert worklog["epic_name"] == "Test Epic"
