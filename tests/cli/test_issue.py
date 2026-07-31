"""Test issue CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.transition import Transition, TransitionField
from budjira.utils.errors import InvalidIssueError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError
from typer.testing import CliRunner

runner = CliRunner()


def test_issue_help() -> None:
    """Test issue subcommand help."""
    result = runner.invoke(app, ["issue", "--help"])
    assert result.exit_code == 0
    assert "issue" in result.stdout.lower()
    assert "update" in result.stdout.lower()
    assert "transitions" in result.stdout.lower()


def test_issue_update_help() -> None:
    """Test issue update command help."""
    result = runner.invoke(app, ["issue", "update", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout.lower()
    assert "assignee" in result.stdout.lower()
    assert "priority" in result.stdout.lower()
    assert "label" in result.stdout.lower()
    assert "epic" in result.stdout.lower()


def test_issue_update_requires_argument() -> None:
    """Test that issue update requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "update"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


def test_issue_update_requires_options() -> None:
    """Test that issue update requires at least one update option."""
    result = runner.invoke(app, ["-q", "issue", "update", "PROJ-123"])
    assert result.exit_code != 0
    # Should warn about no updates specified
    assert "no updates" in result.stdout.lower() or "Error" in result.stdout


def test_issue_transitions_help() -> None:
    """Test issue transitions command help."""
    result = runner.invoke(app, ["issue", "transitions", "--help"])
    assert result.exit_code == 0
    assert "transitions" in result.stdout.lower()
    assert "workflow" in result.stdout.lower()


def test_issue_transitions_requires_argument() -> None:
    """Test that issue transitions requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "transitions"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


class TestIssueUpdateTimeTracking:
    """Tests for issue update time tracking functionality."""

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_original_estimate(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with original estimate."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--original-estimate", "4h"],
        )

        assert result.exit_code == 0
        mock_client.update_issue.assert_called()
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert "fields" in call_kwargs
        assert "timetracking" in call_kwargs["fields"]
        assert call_kwargs["fields"]["timetracking"]["originalEstimate"] == "4h"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_remaining_estimate(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with remaining estimate."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--remaining-estimate", "2h30m"],
        )

        assert result.exit_code == 0
        mock_client.update_issue.assert_called()
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert call_kwargs["fields"]["timetracking"]["remainingEstimate"] == "2h30m"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_both_estimates(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with both estimates."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "-q",
                "issue",
                "update",
                "TEST-123",
                "--original-estimate",
                "8h",
                "--remaining-estimate",
                "5h",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.update_issue.call_args.kwargs
        assert call_kwargs["fields"]["timetracking"]["originalEstimate"] == "8h"
        assert call_kwargs["fields"]["timetracking"]["remainingEstimate"] == "5h"

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_log_work(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with log work."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--log-work", "3h"],
        )

        assert result.exit_code == 0
        mock_client.add_worklog.assert_called_once()
        call_kwargs = mock_client.add_worklog.call_args.kwargs
        assert call_kwargs["issue_key"] == "TEST-123"
        assert call_kwargs["time_spent_minutes"] == 180  # 3h = 180m

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_update_with_log_work_and_comment(self, mock_get_conn, mock_jira_client_class):
        """Test updating issue with log work and comment."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection
        mock_client = MagicMock()
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "-q",
                "issue",
                "update",
                "TEST-123",
                "--log-work",
                "2h",
                "--work-comment",
                "Implemented feature",
            ],
        )

        assert result.exit_code == 0
        mock_client.add_worklog.assert_called_once()
        call_kwargs = mock_client.add_worklog.call_args.kwargs
        assert call_kwargs["time_spent_minutes"] == 120
        assert call_kwargs["comment"] == "Implemented feature"

    @patch("budjira.cli.issue.get_active_connection")
    def test_update_work_comment_without_log_work(self, mock_get_conn):
        """Test that --work-comment requires --log-work."""
        from budjira.models.connection import Connection

        mock_connection = Connection(
            name="test",
            url="https://test.atlassian.net",  # type: ignore[arg-type]
            email="test@example.com",
            project_key="TEST",
        )
        mock_get_conn.return_value = mock_connection

        result = runner.invoke(
            app,
            ["-q", "issue", "update", "TEST-123", "--work-comment", "Should fail"],
        )

        assert result.exit_code == 1
        assert "--work-comment requires --log-work" in result.stdout


def _mock_connection() -> MagicMock:
    """Create a mock connection for tests."""
    mock = MagicMock()
    mock.name = "test"
    mock.url = "https://test.atlassian.net"
    return mock


def _mock_issue(key: str = "TEST-123", summary: str = "Test issue") -> MagicMock:
    """Create a mock Issue for tests."""
    mock = MagicMock()
    mock.key = key
    mock.summary = summary
    return mock


class TestIssueDelete:
    """Tests for issue delete command."""

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_with_confirmation(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test successful delete with user confirmation."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.return_value = _mock_issue()

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-123"], input="y\n")

        assert result.exit_code == 0
        assert "Deleted issue TEST-123" in result.stdout
        mock_client.issues.delete.assert_called_once_with("TEST-123", delete_subtasks=False)

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_cancelled(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test deletion cancelled by user."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.return_value = _mock_issue()

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-123"], input="n\n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.stdout
        mock_client.issues.delete.assert_not_called()

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_force(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test delete with --force flag skips confirmation."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.return_value = _mock_issue()

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-123", "--force"])

        assert result.exit_code == 0
        assert "Deleted issue TEST-123" in result.stdout
        mock_client.issues.delete.assert_called_once_with("TEST-123", delete_subtasks=False)

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_with_subtasks(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test delete with --delete-subtasks flag."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.return_value = _mock_issue()

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-123", "--force", "--delete-subtasks"])

        assert result.exit_code == 0
        mock_client.issues.delete.assert_called_once_with("TEST-123", delete_subtasks=True)

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_issue_not_found(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test delete when issue does not exist."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.side_effect = InvalidIssueError("Issue 'TEST-999' not found")

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-999", "--force"])

        assert result.exit_code == 1
        assert "not found" in result.stdout
        mock_client.issues.delete.assert_not_called()

    @patch("budjira.cli.issue.JiraClient")
    @patch("budjira.cli.issue.get_active_connection")
    def test_delete_permission_denied(self, mock_get_conn: MagicMock, mock_jira_cls: MagicMock) -> None:
        """Test delete when user lacks permission."""
        mock_get_conn.return_value = _mock_connection()
        mock_client = MagicMock()
        mock_jira_cls.from_connection.return_value = mock_client
        mock_client.issues.get.return_value = _mock_issue()
        mock_client.issues.delete.side_effect = BudjiraPermissionError("Permission denied")

        result = runner.invoke(app, ["-q", "issue", "delete", "TEST-123", "--force"])

        assert result.exit_code == 1
        assert "Permission denied" in result.stdout


@pytest.fixture
def mock_client():
    """Patched JiraClient for transition tests (same patching the decorated tests do)."""
    with (
        patch("budjira.cli.issue.JiraClient") as mock_jira_cls,
        patch("budjira.cli.issue.get_active_connection", return_value=_mock_connection()),
    ):
        client = MagicMock()
        mock_jira_cls.from_connection.return_value = client
        yield client


def _transition_with_required_field() -> Transition:
    """A transition whose screen carries one required text field."""
    return Transition(
        id="21",
        name="Resolve",
        to_status="Resolved",
        fields=[
            TransitionField(
                field_id="customfield_10001",
                name="Solution details",
                required=True,
                field_type="string",
            )
        ],
    )


def test_field_without_status_is_a_usage_error(mock_client: MagicMock) -> None:
    """Screen fields only exist in the context of a transition."""
    result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--field", "resolution=Done"])

    assert result.exit_code == 1
    assert "--status" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_missing_required_field_non_interactive_lists_requirements(mock_client: MagicMock) -> None:
    """Without a TTY there is no prompt - abort with what is needed."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]

    result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--no-interactive"])

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "Solution details" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_supplied_field_is_passed_to_the_transition(mock_client: MagicMock) -> None:
    """A supplied screen field reaches the service layer."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]

    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=Rolled out",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 0
    mock_client.transitions.transition.assert_called_once_with(
        "TEST-123", "Resolve", fields={"customfield_10001": "Rolled out"}
    )


def test_dry_run_performs_no_transition(mock_client: MagicMock) -> None:
    """A dry run must never touch the issue."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]

    result = runner.invoke(
        app,
        ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--field", "customfield_10001=x", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Resolve" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_dry_run_does_not_prompt_for_missing_fields(mock_client: MagicMock) -> None:
    """A dry run must not ask for values it will never send."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]

    with patch("typer.prompt") as mock_prompt:
        result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--dry-run"])

    assert result.exit_code == 0
    mock_prompt.assert_not_called()
    mock_client.transitions.transition.assert_not_called()


def test_missing_required_field_is_prompted_when_interactive(mock_client: MagicMock) -> None:
    """With a TTY the missing value is asked for instead of aborting."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]

    with (
        patch("budjira.cli.issue._can_prompt", return_value=True),
        patch("typer.prompt", return_value="Rolled out"),
    ):
        result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve"])

    assert result.exit_code == 0
    mock_client.transitions.transition.assert_called_once_with(
        "TEST-123", "Resolve", fields={"customfield_10001": "Rolled out"}
    )


def _validator_error() -> JIRAError:
    """A workflow validator rejection: message set, errors object empty."""
    error = JIRAError(status_code=400, text="Provide details about the solution made available.")
    error.response = MagicMock()
    error.response.json.return_value = {
        "errorMessages": ["Provide details about the solution made available."],
        "errors": {},
    }
    return error


def test_validator_failure_names_the_field(mock_client: MagicMock) -> None:
    """Jira's anonymous message is replaced by a concrete field name."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = _validator_error()

    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=x",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "Solution details" in result.stdout


def test_validator_failure_retries_once_when_interactive(mock_client: MagicMock) -> None:
    """After prompting, retry exactly once."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = [_validator_error(), None]

    with (
        patch("budjira.cli.issue._can_prompt", return_value=True),
        patch("typer.prompt", return_value="Rolled out"),
    ):
        result = runner.invoke(
            app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--field", "customfield_10001=x"]
        )

    assert result.exit_code == 0
    assert mock_client.transitions.transition.call_count == 2


def test_unattributable_validator_message_is_forwarded(mock_client: MagicMock) -> None:
    """Never invent a field name."""
    error = JIRAError(status_code=400, text="Something else went wrong")
    error.response = MagicMock()
    error.response.json.return_value = {"errorMessages": ["Something else went wrong"], "errors": {}}
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = error

    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=x",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 1
    assert "Something else went wrong" in result.stdout


def test_validator_failure_is_attributed_through_the_service_error_wrapper(mock_client: MagicMock) -> None:
    """Production shape: the service wraps JIRAError in JiraAPIError.

    _handle_jira_error keeps only the error text, so the response body survives
    solely in the __cause__ chain. Attribution must still work.
    """
    from budjira.utils.errors import JiraAPIError

    original = _validator_error()
    wrapped = JiraAPIError("Transition issue failed: Provide details about the solution made available.")
    wrapped.__cause__ = original

    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = wrapped

    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=x",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "Solution details" in result.stdout
