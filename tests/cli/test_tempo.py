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
    assert call_kwargs["author_account_id"] == "557058:abc123def456", (
        "author_account_id must be the Jira accountId from myself() API, not the username from current_user()"
    )


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


def test_tempo_log_native_fallback_when_tempo_disabled(mock_connection):
    """Test that tempo log falls back to a native Jira worklog when Tempo is disabled (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.TempoClient") as mock_tempo_class:
            with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
                mock_jira = mock_jira_class.from_connection.return_value
                mock_jira.worklogs.add.return_value = "67890"

                result = runner.invoke(app, ["tempo", "log", "PROJ-123", "2h", "--comment", "Native work"])

    assert result.exit_code == 0
    assert "Logged 2h to PROJ-123 (native Jira worklog)" in result.stdout
    assert "Worklog ID: 67890" in result.stdout
    mock_tempo_class.assert_not_called()
    mock_jira.worklogs.add.assert_called_once()
    call_args = mock_jira.worklogs.add.call_args
    assert call_args[0][0] == "PROJ-123"
    assert call_args[0][1] == 120  # 2h in minutes
    assert call_args[0][2] == "Native work"


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


def test_tempo_worklogs_with_date_range(mock_tempo_connection, mock_tempo_client, mock_jira_client):
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


def test_tempo_worklogs_empty_results(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test worklog listing with no results."""
    mock_tempo_client.get_worklogs.return_value = []

    result = runner.invoke(app, ["tempo", "worklogs"])

    assert result.exit_code == 0
    assert "No worklogs found" in result.stdout


def test_tempo_worklogs_without_issue_key(mock_tempo_connection, mock_tempo_client, mock_jira_client):
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


def test_tempo_worklogs_table_issue_key_backfill(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test issue_key backfill in table output when Tempo API returns null key (Bug #61).

    Regression test for Bug #61: tempo worklogs table output shows N/A for issue
    even when the worklog has a valid issue.id that can be resolved via Jira API.
    """
    from datetime import date, datetime

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Create worklog with null issue_key but valid issue_id (Bug #61 scenario)
    worklog_null_key = TempoWorklog(
        self="https://api.tempo.io/worklogs/729",
        tempoWorklogId=729,
        issue=TempoIssue(
            self="https://api.tempo.io/issues/10428",
            key=None,  # Tempo returns null
            id=10428,  # But has valid ID
        ),
        timeSpentSeconds=7200,
        startDate=date(2025, 10, 25),
        startTime="09:00:00",
        createdAt=datetime(2025, 10, 25, 9, 0),
        updatedAt=datetime(2025, 10, 25, 9, 0),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:test",
            displayName="Test User",
        ),
    )
    mock_tempo_client.get_worklogs.return_value = [worklog_null_key]

    # Mock Jira API issue() call for backfill - returns the resolved key
    mock_issue = MagicMock()
    mock_issue.key = "PROJ-456"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    result = runner.invoke(app, ["tempo", "worklogs"])

    assert result.exit_code == 0

    # CRITICAL: Verify Jira API was called to backfill issue_key (as string)
    mock_jira_client.from_connection.return_value.client.issue.assert_called_once_with("10428", fields="key")

    # CRITICAL: Verify table output shows the resolved issue key, NOT "N/A"
    assert "PROJ-456" in result.stdout, (
        "Table output should show backfilled issue_key from Jira API, not N/A. "
        "Bug #61: Tempo API returns null key but valid issue.id"
    )
    assert "N/A" not in result.stdout, "N/A should not appear when issue_key can be backfilled from Jira API"


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


def test_tempo_worklogs_json_issue_key_backfill(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test issue_key backfill when Tempo API returns null key (Bug #10).

    Regression test for Bug #10: Tempo API sometimes returns issue.key as null
    even when worklog has valid issueId. The code should backfill the key from
    Jira API to enable automation and epic lookup.

    Root cause: Tempo REST API response contains:
    {"issue": {"self": "...", "key": null, "id": 12345}}
    """
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock worklog with null issue_key but valid issue_id (Bug #10 scenario)
    mock_worklogs = [
        TempoWorklog(
            self="https://api.tempo.io/worklogs/622",
            tempoWorklogId=622,
            issue=TempoIssue(
                self="https://api.tempo.io/issues/12345",
                key=None,  # Tempo returns null
                id=12345,  # But has valid ID
            ),
            timeSpentSeconds=18000,
            startDate=date(2025, 10, 7),
            startTime="09:00:00",
            description="Development work",
            createdAt=datetime(2025, 10, 7, 9, 0),
            updatedAt=datetime(2025, 10, 7, 9, 0),
            author=TempoAuthor(
                self="https://api.tempo.io/users/1",
                accountId="557058:abc",
                displayName="Test User",
            ),
        ),
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Mock Jira API issue() call for backfill
    mock_issue = MagicMock()
    mock_issue.key = "PRD-4"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    # Mock epic fetching
    mock_jira_client.from_connection.return_value.get_issue_epic.return_value = ("PRD-1", "budjira Development")

    # Run command with JSON format
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # CRITICAL 1: Verify Jira API was called to backfill issue_key (as string for mypy compatibility)
    mock_jira_client.from_connection.return_value.client.issue.assert_called_once_with("12345", fields="key")

    # CRITICAL 2: Verify JSON output has backfilled issue_key
    output = json.loads(result.stdout)
    assert output["total"] == 1
    worklog = output["worklogs"][0]
    assert worklog["issue_key"] == "PRD-4", (
        "issue_key should be backfilled from Jira API when Tempo returns null. "
        "This is critical for FoU tax reporting and epic aggregation."
    )

    # CRITICAL 3: Verify epic information is populated (depends on issue_key)
    assert worklog["epic_key"] == "PRD-1"
    assert worklog["epic_name"] == "budjira Development"


def test_tempo_worklogs_json_issue_key_caching(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test that issue_key backfill is cached for multiple worklogs with same issue_id (Bug #10)."""
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock 3 worklogs with null issue_key but same issue_id
    mock_worklogs = [
        TempoWorklog(
            self=f"https://api.tempo.io/worklogs/{i}",
            tempoWorklogId=i,
            issue=TempoIssue(
                self="https://api.tempo.io/issues/12345",
                key=None,  # All have null key
                id=12345,  # Same issue ID
            ),
            timeSpentSeconds=3600 * i,
            startDate=date(2025, 10, 7),
            startTime="09:00:00",
            description=f"Work {i}",
            createdAt=datetime(2025, 10, 7, 9, 0),
            updatedAt=datetime(2025, 10, 7, 9, 0),
            author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="123"),
        )
        for i in range(1, 4)
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Mock Jira API backfill
    mock_issue = MagicMock()
    mock_issue.key = "TEST-100"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    # Mock epic fetching
    mock_jira_client.from_connection.return_value.get_issue_epic.return_value = ("EPIC-50", "Test Epic")

    # Run command
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # CRITICAL: Verify issue backfill was called only ONCE (cached)
    assert mock_jira_client.from_connection.return_value.client.issue.call_count == 1, (
        "issue_key backfill should be cached to minimize Jira API calls"
    )

    # Verify all worklogs have backfilled issue_key
    output = json.loads(result.stdout)
    assert output["total"] == 3
    for worklog in output["worklogs"]:
        assert worklog["issue_key"] == "TEST-100"


def test_tempo_worklogs_json_no_issue_id(mock_tempo_connection, mock_tempo_client, mock_jira_client):
    """Test handling of worklogs with null issue_key AND null issue_id (Bug #10 edge case)."""
    import json

    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock worklog with both null key and null id
    mock_worklogs = [
        TempoWorklog(
            self="https://api.tempo.io/worklogs/999",
            tempoWorklogId=999,
            issue=TempoIssue(
                self="https://api.tempo.io/issues/999",
                key=None,  # No key
                id=None,  # No ID either
            ),
            timeSpentSeconds=3600,
            startDate=date(2025, 10, 7),
            startTime="09:00:00",
            description="Test work",
            createdAt=datetime(2025, 10, 7, 9, 0),
            updatedAt=datetime(2025, 10, 7, 9, 0),
            author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="123"),
        ),
    ]
    mock_tempo_client.get_worklogs.return_value = mock_worklogs

    # Run command
    result = runner.invoke(app, ["--format", "json", "tempo", "worklogs"])

    assert result.exit_code == 0

    # Verify Jira API was NOT called (no issue_id to backfill)
    mock_jira_client.from_connection.return_value.client.issue.assert_not_called()

    # Verify JSON output has null issue_key (cannot backfill)
    output = json.loads(result.stdout)
    assert output["total"] == 1
    worklog = output["worklogs"][0]
    assert worklog["issue_key"] is None
    # Epic fields should not be present (requires issue_key)
    assert "epic_key" not in worklog
    assert "epic_name" not in worklog


def test_tempo_update_worklog_success(mock_tempo_connection, mock_tempo_client):
    """Test successful worklog update with all fields."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock current worklog
    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=123),
        timeSpentSeconds=7200,  # 2h
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        description="Original comment",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    # Mock updated worklog
    updated_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=123),
        timeSpentSeconds=14400,  # 4h
        startDate=date(2025, 10, 28),
        startTime="14:00:00",
        description="Updated comment",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 10, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    mock_tempo_client.get_worklog.return_value = current_worklog
    mock_tempo_client.update_worklog.return_value = updated_worklog

    # Run command with --force to skip confirmation
    result = runner.invoke(
        app,
        [
            "tempo",
            "update-worklog",
            "642",
            "--time-spent",
            "4h",
            "--started",
            "2025-10-28 14:00",
            "--comment",
            "Updated comment",
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert "Updated Tempo worklog 642" in result.stdout
    assert "TEST-123" in result.stdout
    assert "4.00h" in result.stdout
    assert "Updated comment" in result.stdout

    # Verify API calls
    mock_tempo_client.get_worklog.assert_called_once_with(642)
    mock_tempo_client.update_worklog.assert_called_once()


def test_tempo_update_worklog_partial(mock_tempo_connection, mock_tempo_client):
    """Test partial worklog update (only date)."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=123),
        timeSpentSeconds=7200,
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        description="Test work",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    updated_worklog = current_worklog.model_copy(update={"startDate": date(2025, 10, 28)})

    mock_tempo_client.get_worklog.return_value = current_worklog
    mock_tempo_client.update_worklog.return_value = updated_worklog

    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--started", "2025-10-28", "--force"])

    assert result.exit_code == 0
    assert "Updated Tempo worklog 642" in result.stdout
    mock_tempo_client.update_worklog.assert_called_once()


def test_tempo_update_worklog_with_confirmation(mock_tempo_connection, mock_tempo_client, monkeypatch):
    """Test worklog update with confirmation prompt."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=123),
        timeSpentSeconds=7200,
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        description="Test work",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    updated_worklog = current_worklog.model_copy(update={"timeSpentSeconds": 3600})

    mock_tempo_client.get_worklog.return_value = current_worklog
    mock_tempo_client.update_worklog.return_value = updated_worklog

    # Simulate user confirming
    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--time-spent", "1h"], input="y\n")

    assert result.exit_code == 0
    assert "Worklog Update Preview" in result.stdout
    assert "2.00h → 1.00h" in result.stdout  # Show change
    assert "Updated Tempo worklog 642" in result.stdout
    mock_tempo_client.update_worklog.assert_called_once()


def test_tempo_update_worklog_cancelled(mock_tempo_connection, mock_tempo_client):
    """Test worklog update cancelled by user."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=123),
        timeSpentSeconds=7200,
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    mock_tempo_client.get_worklog.return_value = current_worklog

    # User declines confirmation
    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--time-spent", "3h"], input="n\n")

    assert result.exit_code == 0
    assert "Update cancelled" in result.stdout
    mock_tempo_client.update_worklog.assert_not_called()


def test_tempo_update_worklog_no_fields(mock_tempo_connection):
    """Test worklog update with no fields specified."""
    result = runner.invoke(app, ["tempo", "update-worklog", "642"])

    assert result.exit_code == 1
    assert "No updates specified" in result.stdout


def test_tempo_update_worklog_not_found(mock_tempo_connection, mock_tempo_client):
    """Test worklog update with non-existent worklog ID."""
    from budjira.utils.errors import JiraAPIError

    mock_tempo_client.get_worklog.side_effect = JiraAPIError("Worklog 99999 not found")

    result = runner.invoke(app, ["tempo", "update-worklog", "99999", "--time-spent", "2h", "--force"])

    assert result.exit_code == 1
    assert "Worklog 99999 not found" in result.stdout


def test_tempo_update_worklog_native_fallback_when_tempo_disabled(mock_connection):
    """Test that update-worklog falls back to native Jira worklogs when Tempo is disabled (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.worklogs.get.return_value = {
                "id": "67890",
                "author": "Test User",
                "authorAccountId": "557058:abc123",
                "timeSpent": "2h",
                "timeSpentSeconds": 7200,
                "started": "2026-08-20T10:00:00.000+0000",
                "created": "2026-08-20T10:00:00.000+0000",
                "comment": "Old comment",
            }
            mock_jira.worklogs.update.return_value = {
                "id": "67890",
                "author": "Test User",
                "authorAccountId": "557058:abc123",
                "timeSpent": "3h",
                "timeSpentSeconds": 10800,
                "started": "2026-08-20T10:00:00.000+0000",
                "created": "2026-08-20T10:00:00.000+0000",
                "comment": "Old comment",
            }

            result = runner.invoke(
                app,
                ["tempo", "update-worklog", "67890", "--issue", "PROJ-123", "--time-spent", "3h", "--force"],
            )

    assert result.exit_code == 0
    assert "Updated worklog 67890 on PROJ-123 (native Jira)" in result.stdout
    mock_jira.worklogs.update.assert_called_once_with(
        "PROJ-123", "67890", time_spent_minutes=180, comment=None, started=None
    )


def test_tempo_update_worklog_native_requires_issue(mock_connection):
    """Test that native update-worklog without --issue fails with an actionable error (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        result = runner.invoke(app, ["tempo", "update-worklog", "67890", "--time-spent", "2h", "--force"])

    assert result.exit_code == 1
    assert "--issue is required" in result.stdout
    assert "worklog list" in result.stdout


def test_tempo_update_worklog_authentication_error(mock_tempo_connection, mock_tempo_client):
    """Test worklog update with authentication error."""
    from budjira.utils.errors import AuthenticationError

    mock_tempo_client.get_worklog.side_effect = AuthenticationError("Tempo authentication failed")

    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--time-spent", "2h", "--force"])

    assert result.exit_code == 1
    assert "Tempo authentication failed" in result.stdout


def test_tempo_update_worklog_null_issue_id_resolves_from_jira(
    mock_tempo_connection, mock_tempo_client, mock_jira_client
):
    """Test update-worklog resolves issue ID from Jira when Tempo returns None (#72)."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock current worklog with None issue.id but valid key
    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="TEST-123", id=None),
        timeSpentSeconds=7200,
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        description="Test work",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    updated_worklog = current_worklog.model_copy(update={"timeSpentSeconds": 3600})

    mock_tempo_client.get_worklog.return_value = current_worklog
    mock_tempo_client.update_worklog.return_value = updated_worklog

    # Mock Jira API issue() call for ID resolution
    mock_issue = MagicMock()
    mock_issue.id = "12345"
    mock_issue.key = "TEST-123"
    mock_jira_client.from_connection.return_value.client.issue.return_value = mock_issue

    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--time-spent", "1h", "--force"])

    assert result.exit_code == 0
    assert "Updated Tempo worklog 642" in result.stdout

    # Verify update was called with the resolved issue_id
    mock_tempo_client.update_worklog.assert_called_once()
    call_kwargs = mock_tempo_client.update_worklog.call_args[1]
    assert call_kwargs["issue_id"] == 12345


def test_tempo_update_worklog_null_issue_id_and_no_key(mock_tempo_connection, mock_tempo_client):
    """Test update-worklog fails gracefully when both issue.id and issue.key are None (#72)."""
    from budjira.tempo.models import TempoAuthor, TempoIssue, TempoWorklog

    # Mock current worklog with None issue.id AND None issue.key
    current_worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/642",
        tempoWorklogId=642,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key=None, id=None),
        timeSpentSeconds=7200,
        startDate=date(2025, 11, 2),
        startTime="09:00:00",
        createdAt=datetime(2025, 11, 2, 9, 0),
        updatedAt=datetime(2025, 11, 2, 9, 0),
        author=TempoAuthor(self="https://api.tempo.io/users/1", accountId="557058:abc123"),
    )

    mock_tempo_client.get_worklog.return_value = current_worklog

    result = runner.invoke(app, ["tempo", "update-worklog", "642", "--time-spent", "1h", "--force"])

    assert result.exit_code == 1
    assert "no associated issue" in result.stdout

    # Verify update was NOT called
    mock_tempo_client.update_worklog.assert_not_called()


class TestWorkflowPolicyCheck:
    """Test workflow booking policy enforcement in tempo log (#70)."""

    def _make_mock_settings(self) -> MagicMock:
        """Create mock settings with a workflow profile."""
        from budjira.models.workflow import (
            OverbookingPolicy,
            ProjectMapping,
            ShadowTicketStrategy,
            WorkflowProfile,
            WorkflowProfileList,
        )

        profile = WorkflowProfile(
            name="test-workflow",
            planning_connection="planning-conn",
            booking_connection="booking-conn",
            project_mappings=[
                ProjectMapping(planning_project="PLAN", booking_project="BOOK"),
            ],
            shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH,
            overbooking_policy=OverbookingPolicy.WARN,
        )
        mock_settings = MagicMock()
        mock_settings.workflows = WorkflowProfileList(profiles=[profile])
        return mock_settings

    def test_blocks_direct_booking_on_planning_connection(
        self, mock_tempo_connection, mock_tempo_client, mock_jira_client
    ):
        """Direct tempo log on planning connection should be blocked."""
        mock_settings = self._make_mock_settings()

        with (
            patch("budjira.cli.tempo.get_settings", return_value=mock_settings),
            patch("budjira.cli.tempo.get_active_connection") as mock_get_conn,
        ):
            mock_conn = MagicMock()
            mock_conn.name = "planning-conn"
            mock_get_conn.return_value = mock_conn

            result = runner.invoke(app, ["tempo", "log", "PLAN-123", "2h", "--connection", "planning-conn"])

            assert result.exit_code == 1
            assert "Direct booking is not allowed" in result.stdout
            assert "workflow book" in result.stdout
            assert "test-workflow" in result.stdout

    def test_allows_booking_on_non_planning_connection(
        self, mock_tempo_connection, mock_tempo_client, mock_jira_client
    ):
        """Tempo log on a non-planning connection should proceed normally."""
        mock_settings = self._make_mock_settings()
        mock_tempo_client.create_worklog.return_value = TempoWorklog(
            self="https://api.tempo.io/worklogs/1",
            tempoWorklogId=1,
            issue=TempoIssue(self="https://api.tempo.io/issues/123", key="OTHER-123"),
            timeSpentSeconds=7200,
            startDate=date(2025, 10, 25),
            createdAt=datetime(2025, 10, 25, 9, 0),
            updatedAt=datetime(2025, 10, 25, 9, 0),
            author=TempoAuthor(
                self="https://api.tempo.io/users/1",
                accountId="557058:abc",
                displayName="Test User",
            ),
        )

        with patch("budjira.cli.tempo.get_settings", return_value=mock_settings):
            result = runner.invoke(app, ["tempo", "log", "OTHER-123", "2h"])

            assert result.exit_code == 0

    def test_force_flag_bypasses_policy(self, mock_tempo_connection, mock_tempo_client, mock_jira_client):
        """--force should bypass the workflow policy check."""
        mock_settings = self._make_mock_settings()
        mock_tempo_client.create_worklog.return_value = TempoWorklog(
            self="https://api.tempo.io/worklogs/1",
            tempoWorklogId=1,
            issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PLAN-123"),
            timeSpentSeconds=7200,
            startDate=date(2025, 10, 25),
            createdAt=datetime(2025, 10, 25, 9, 0),
            updatedAt=datetime(2025, 10, 25, 9, 0),
            author=TempoAuthor(
                self="https://api.tempo.io/users/1",
                accountId="557058:abc",
                displayName="Test User",
            ),
        )

        with (
            patch("budjira.cli.tempo.get_settings", return_value=mock_settings),
            patch("budjira.cli.tempo.get_active_connection") as mock_get_conn,
        ):
            mock_conn = mock_tempo_connection
            mock_conn.name = "planning-conn"
            mock_get_conn.return_value = mock_conn

            result = runner.invoke(
                app,
                ["tempo", "log", "PLAN-123", "2h", "--connection", "planning-conn", "--force"],
            )

            assert result.exit_code == 0
            mock_tempo_client.create_worklog.assert_called_once()

    def test_no_profiles_allows_booking(self, mock_tempo_connection, mock_tempo_client, mock_jira_client):
        """When no workflow profiles exist, booking should proceed normally."""
        from budjira.models.workflow import WorkflowProfileList

        mock_settings = MagicMock()
        mock_settings.workflows = WorkflowProfileList(profiles=[])
        mock_tempo_client.create_worklog.return_value = TempoWorklog(
            self="https://api.tempo.io/worklogs/1",
            tempoWorklogId=1,
            issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PLAN-123"),
            timeSpentSeconds=7200,
            startDate=date(2025, 10, 25),
            createdAt=datetime(2025, 10, 25, 9, 0),
            updatedAt=datetime(2025, 10, 25, 9, 0),
            author=TempoAuthor(
                self="https://api.tempo.io/users/1",
                accountId="557058:abc",
                displayName="Test User",
            ),
        )

        with patch("budjira.cli.tempo.get_settings", return_value=mock_settings):
            result = runner.invoke(app, ["tempo", "log", "PLAN-123", "2h"])

            assert result.exit_code == 0


# --- Native Jira worklog fallback tests (#113) ---


def _native_worklog(
    worklog_id: str = "67890",
    author: str = "Test User",
    account_id: str = "557058:abc123",
    seconds: int = 7200,
    started: str = "2026-08-20T10:00:00.000+0000",
    comment: str | None = "Native work",
) -> dict[str, object]:
    """Create a native worklog dict as returned by WorklogService."""
    worklog = {
        "id": worklog_id,
        "author": author,
        "authorAccountId": account_id,
        "timeSpent": f"{seconds // 3600}h" if seconds >= 3600 else f"{seconds // 60}m",
        "timeSpentSeconds": seconds,
        "started": started,
        "created": started,
    }
    if comment:
        worklog["comment"] = comment
    return worklog


def test_tempo_worklogs_native_issue_scoped_filters_current_user(mock_connection):
    """Test native worklogs for an issue show only the current user's entries (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            mock_jira.worklogs.list.return_value = [
                _native_worklog("67890", "Test User", "557058:abc123", 7200, comment="Mine"),
                _native_worklog("67891", "Someone Else", "other-account", 3600, comment="Theirs"),
            ]

            result = runner.invoke(app, ["tempo", "worklogs", "PROJ-123"])

    assert result.exit_code == 0
    assert "Jira Worklogs (1 entries)" in result.stdout
    assert "Mine" in result.stdout
    assert "Theirs" not in result.stdout
    mock_jira.worklogs.list.assert_called_once_with("PROJ-123")


def test_tempo_worklogs_native_date_filter(mock_connection):
    """Test native worklogs honor --from/--to against the started date (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            mock_jira.worklogs.list.return_value = [
                _native_worklog("1", started="2026-08-05T10:00:00.000+0000", comment="Early August"),
                _native_worklog("2", started="2026-08-20T10:00:00.000+0000", comment="Mid August"),
            ]

            result = runner.invoke(app, ["tempo", "worklogs", "PROJ-123", "--from", "2026-08-10"])

    assert result.exit_code == 0
    assert "Mid August" in result.stdout
    assert "Early August" not in result.stdout


def test_tempo_worklogs_native_user_scoped_uses_jql(mock_connection):
    """Test native worklogs without issue key search via worklogAuthor JQL (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            issue_a = MagicMock()
            issue_a.key = "PROJ-1"
            issue_b = MagicMock()
            issue_b.key = "PROJ-2"
            mock_jira.client.search_issues.return_value = [issue_a, issue_b]
            mock_jira.worklogs.list.side_effect = lambda key: {
                "PROJ-1": [_native_worklog("1", started="2026-08-20T10:00:00.000+0000", comment="On P1")],
                "PROJ-2": [_native_worklog("2", started="2026-08-21T10:00:00.000+0000", comment="On P2")],
            }[key]

            result = runner.invoke(app, ["tempo", "worklogs", "--from", "2026-08-01", "--to", "2026-08-31"])

    assert result.exit_code == 0
    assert "On P1" in result.stdout
    assert "On P2" in result.stdout

    jql = mock_jira.client.search_issues.call_args[0][0]
    assert "worklogAuthor = currentUser()" in jql
    assert "worklogDate >= '2026-08-01'" in jql
    assert "worklogDate <= '2026-08-31'" in jql


def test_tempo_worklogs_native_user_scoped_defaults_to_current_month(mock_connection):
    """Test native user-scoped listing defaults the range to the current month (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            mock_jira.client.search_issues.return_value = []

            result = runner.invoke(app, ["tempo", "worklogs"])

    assert result.exit_code == 0
    expected_from = date.today().replace(day=1).isoformat()
    jql = mock_jira.client.search_issues.call_args[0][0]
    assert f"worklogDate >= '{expected_from}'" in jql
    assert "worklogDate <=" not in jql


def test_tempo_worklogs_native_json_with_epic(mock_connection):
    """Test native worklogs JSON output includes epic info unless --no-epic (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            mock_jira.worklogs.list.return_value = [_native_worklog()]
            mock_jira.get_issue_epic.return_value = ("EPIC-1", "Big Epic")

            result = runner.invoke(app, ["--format", "json", "tempo", "worklogs", "PROJ-123"])

    assert result.exit_code == 0
    assert '"issue_key": "PROJ-123"' in result.stdout
    assert '"epic_key": "EPIC-1"' in result.stdout
    assert '"author_account_id": "557058:abc123"' in result.stdout


def test_tempo_worklogs_native_json_no_epic(mock_connection):
    """Test native worklogs JSON output with --no-epic skips epic fetching (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.client.myself.return_value = {"accountId": "557058:abc123"}
            mock_jira.worklogs.list.return_value = [_native_worklog()]

            result = runner.invoke(app, ["--format", "json", "tempo", "worklogs", "PROJ-123", "--no-epic"])

    assert result.exit_code == 0
    assert "epic_key" not in result.stdout
    mock_jira.get_issue_epic.assert_not_called()


def test_tempo_delete_worklog_native_with_issue(mock_connection):
    """Test native delete-worklog deletes via the Jira worklog service (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value

            result = runner.invoke(app, ["tempo", "delete-worklog", "67890", "--issue", "PROJ-123", "--force"])

    assert result.exit_code == 0
    assert "Deleted worklog 67890 from PROJ-123 (native Jira)" in result.stdout
    mock_jira.worklogs.delete.assert_called_once_with("PROJ-123", "67890")


def test_tempo_delete_worklog_native_requires_issue(mock_connection):
    """Test native delete-worklog without --issue fails with an actionable error (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        result = runner.invoke(app, ["tempo", "delete-worklog", "67890", "--force"])

    assert result.exit_code == 1
    assert "--issue is required" in result.stdout
    assert "worklog list" in result.stdout


def test_tempo_delete_worklog_native_cancelled(mock_connection):
    """Test native delete-worklog honours a declined confirmation (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value

            result = runner.invoke(app, ["tempo", "delete-worklog", "67890", "--issue", "PROJ-123"], input="n\n")

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.stdout
    mock_jira.worklogs.delete.assert_not_called()


def test_tempo_update_worklog_native_confirm_preview(mock_connection):
    """Test native update-worklog shows a preview and updates on confirmation (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.worklogs.get.return_value = {
                "id": "67890",
                "author": "Test User",
                "authorAccountId": "557058:abc123",
                "timeSpent": "2h",
                "timeSpentSeconds": 7200,
                "started": "2026-08-20T10:00:00.000+0000",
                "created": "2026-08-20T10:00:00.000+0000",
                "comment": "Old comment",
            }
            mock_jira.worklogs.update.return_value = {
                "id": "67890",
                "author": "Test User",
                "authorAccountId": "557058:abc123",
                "timeSpent": "3h",
                "timeSpentSeconds": 10800,
                "started": "2026-08-21T09:30:00.000+0000",
                "created": "2026-08-20T10:00:00.000+0000",
                "comment": "New comment",
            }

            result = runner.invoke(
                app,
                [
                    "tempo",
                    "update-worklog",
                    "67890",
                    "--issue",
                    "PROJ-123",
                    "--time-spent",
                    "3h",
                    "--started",
                    "2026-08-21 09:30",
                    "--comment",
                    "New comment",
                ],
                input="y\n",
            )

    assert result.exit_code == 0
    assert "Worklog Update Preview:" in result.stdout
    assert "2.00h" in result.stdout
    assert "3.00h" in result.stdout
    assert "Old comment" in result.stdout
    assert "New comment" in result.stdout
    mock_jira.worklogs.update.assert_called_once()


def test_tempo_update_worklog_native_cancelled(mock_connection):
    """Test native update-worklog honours a declined confirmation (#113)."""
    mock_connection.tempo_enabled = False

    with patch("budjira.cli.tempo.get_active_connection", return_value=mock_connection):
        with patch("budjira.cli.tempo.JiraClient") as mock_jira_class:
            mock_jira = mock_jira_class.from_connection.return_value
            mock_jira.worklogs.get.return_value = {
                "id": "67890",
                "author": "Test User",
                "authorAccountId": "557058:abc123",
                "timeSpent": "2h",
                "timeSpentSeconds": 7200,
                "started": "2026-08-20T10:00:00.000+0000",
                "created": "2026-08-20T10:00:00.000+0000",
            }

            result = runner.invoke(
                app,
                ["tempo", "update-worklog", "67890", "--issue", "PROJ-123", "--time-spent", "3h"],
                input="n\n",
            )

    assert result.exit_code == 0
    assert "Update cancelled" in result.stdout
    mock_jira.worklogs.update.assert_not_called()
