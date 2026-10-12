"""Tests for the status-transition alias commands (#144)."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from budjira.models.transition import Transition, TransitionField
from typer.testing import CliRunner

runner = CliRunner()

ALIASES = [
    ("start", "In Progress"),
    ("done", "Done"),
    ("block", "Blocked"),
    ("review", "In Review"),
]


def _connection() -> Connection:
    return Connection(
        name="test-connection",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@example.com",
        project_key="TEST",
    )


@pytest.fixture
def mock_client():
    with (
        patch("budjira.cli.aliases.JiraClient") as mock_jira_cls,
        patch("budjira.cli.aliases.get_active_connection", return_value=_connection()),
    ):
        client = MagicMock()
        mock_jira_cls.from_connection.return_value = client
        yield client


@pytest.mark.parametrize(("command", "status"), ALIASES)
def test_alias_transitions_via_resolved_name(mock_client: MagicMock, command: str, status: str) -> None:
    """Each alias resolves the transition and executes it like update --status."""
    mock_client.transitions.get_transition_details.return_value = [Transition(id="31", name=status, to_status=status)]

    result = runner.invoke(app, ["-q", command, "TEST-123"])

    assert result.exit_code == 0
    assert "TEST-123" in result.stdout
    assert status in result.stdout
    mock_client.transitions.transition.assert_called_once_with("TEST-123", status, fields=None)


@pytest.mark.parametrize(("command", "status"), ALIASES)
def test_alias_matches_transition_case_insensitively(mock_client: MagicMock, command: str, status: str) -> None:
    """The project's own transition naming wins (e.g. lower-case workflows)."""
    mock_client.transitions.get_transition_details.return_value = [
        Transition(id="31", name=status.lower(), to_status=status)
    ]

    result = runner.invoke(app, ["-q", command, "TEST-123"])

    assert result.exit_code == 0
    mock_client.transitions.transition.assert_called_once_with("TEST-123", status.lower(), fields=None)


@pytest.mark.parametrize(("command", "status"), ALIASES)
def test_alias_unavailable_transition_lists_options(mock_client: MagicMock, command: str, status: str) -> None:
    """An unavailable transition fails with the available ones, same as update --status."""
    mock_client.transitions.get_transition_details.return_value = [
        Transition(id="11", name="Reopen", to_status="To Do")
    ]

    result = runner.invoke(app, ["-q", command, "TEST-123"])

    assert result.exit_code == 1
    assert "Invalid transition" in result.stdout
    assert "Reopen" in result.stdout
    assert "issue update" in result.stdout  # hint to the full command
    mock_client.transitions.transition.assert_not_called()


def test_alias_required_screen_field_aborts_with_hint(mock_client: MagicMock) -> None:
    """A transition with required screen fields must not traceback (#144)."""
    mock_client.transitions.get_transition_details.return_value = [
        Transition(
            id="21",
            name="Done",
            to_status="Done",
            fields=[
                TransitionField(
                    field_id="customfield_10001", name="Solution details", required=True, field_type="string"
                )
            ],
        )
    ]

    result = runner.invoke(app, ["-q", "done", "TEST-123"])

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "issue update" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_alias_connection_flag_is_forwarded(mock_client: MagicMock) -> None:
    """--connection selects the connection."""
    mock_client.transitions.get_transition_details.return_value = [
        Transition(id="31", name="In Progress", to_status="In Progress")
    ]

    with patch("budjira.cli.aliases.get_active_connection", return_value=_connection()) as mock_get:
        result = runner.invoke(app, ["-q", "start", "TEST-123", "--connection", "other"])

    assert result.exit_code == 0
    mock_get.assert_called_once_with("other")


@pytest.mark.parametrize(("command", "status"), ALIASES)
def test_alias_help(command: str, status: str) -> None:
    """Each alias documents itself and its full-command equivalent."""
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert status in result.stdout
