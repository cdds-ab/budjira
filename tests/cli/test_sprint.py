"""Tests for sprint CLI commands."""

import json
from datetime import date
from unittest.mock import MagicMock, Mock, patch

from budjira.cli.main import app
from budjira.models.issue import Issue
from budjira.models.sprint import Board, Sprint, SprintState
from typer.testing import CliRunner

runner = CliRunner()


def _make_sprint(
    sprint_id: int = 100,
    name: str = "Sprint 10",
    state: SprintState = SprintState.ACTIVE,
    start_date: date | None = date(2025, 1, 15),
    end_date: date | None = date(2025, 1, 29),
) -> Sprint:
    return Sprint(
        id=sprint_id,
        name=name,
        state=state,
        start_date=start_date,
        end_date=end_date,
        board_id=42,
    )


def _make_issue(key: str = "TEST-1", summary: str = "Test issue") -> Issue:
    return Issue(
        key=key,
        summary=summary,
        issue_type="Story",
        status="To Do",
        priority="Medium",
        assignee="user1",
        project_key=key.split("-")[0],
    )


def _make_board(board_id: int = 42, name: str = "Test Board") -> Board:
    return Board(id=board_id, name=name, board_type="scrum")


# Help tests


def test_sprint_help() -> None:
    result = runner.invoke(app, ["sprint", "--help"])
    assert result.exit_code == 0
    assert "sprint" in result.stdout.lower()


def test_sprint_list_help() -> None:
    result = runner.invoke(app, ["sprint", "list", "--help"])
    assert result.exit_code == 0


def test_sprint_show_help() -> None:
    result = runner.invoke(app, ["sprint", "show", "--help"])
    assert result.exit_code == 0


# Sprint list tests


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_table(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = None
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.detect_board.return_value = _make_board()
    mock_client.sprints.get_sprints.return_value = [
        _make_sprint(1, "Sprint 1", SprintState.CLOSED),
        _make_sprint(2, "Sprint 2", SprintState.ACTIVE),
        _make_sprint(3, "Sprint 3", SprintState.FUTURE, None, None),
    ]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list"])
    assert result.exit_code == 0
    assert "Sprint 1" in result.stdout
    assert "Sprint 2" in result.stdout
    assert "Sprint 3" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_with_state_filter(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_sprints.return_value = [_make_sprint()]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list", "--state", "active"])
    assert result.exit_code == 0
    mock_client.sprints.get_sprints.assert_called_once_with(42, state="active")


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_with_board_flag(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = None
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_sprints.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list", "--board", "99"])
    assert result.exit_code == 0
    mock_client.sprints.get_sprints.assert_called_once_with(99, state=None)


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_json(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_sprints.return_value = [_make_sprint()]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "list"])
    assert result.exit_code == 0
    assert '"Sprint 10"' in result.stdout
    assert '"total": 1' in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_empty(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_sprints.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list"])
    assert result.exit_code == 0
    assert "No sprints found" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_invalid_state(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list", "--state", "invalid"])
    assert result.exit_code == 1
    assert "Invalid state" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_list_uses_connection_board_id(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    """When connection has board_id, use it without auto-detection."""
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 77

    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_sprints.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "list"])
    assert result.exit_code == 0
    mock_client.sprints.get_sprints.assert_called_once_with(77, state=None)
    mock_client.sprints.detect_board.assert_not_called()


# Sprint show tests


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_active(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = _make_sprint()
    mock_client.sprints.get_sprint_issues.return_value = [
        _make_issue("TEST-1", "First issue"),
        _make_issue("TEST-2", "Second issue"),
    ]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show"])
    assert result.exit_code == 0
    assert "Sprint 10" in result.stdout
    assert "TEST-1" in result.stdout
    assert "TEST-2" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_by_name(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(name="Sprint 5")
    mock_client.sprints.get_sprint_issues.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show", "Sprint 5"])
    assert result.exit_code == 0
    assert "Sprint 5" in result.stdout
    mock_client.sprints.find_sprint_by_name.assert_called_once_with(42, "Sprint 5")


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_mine_filter(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = _make_sprint()
    mock_client.sprints.get_sprint_issues.return_value = [_make_issue()]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show", "--mine"])
    assert result.exit_code == 0
    call_args = mock_client.sprints.get_sprint_issues.call_args
    assert "assignee = currentUser()" in (call_args[1].get("jql_filter") or call_args[0][1] or "")


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_json(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = _make_sprint()
    mock_client.sprints.get_sprint_issues.return_value = [_make_issue("TEST-1", "Issue 1")]
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "show"])
    assert result.exit_code == 0
    assert '"TEST-1"' in result.stdout
    assert '"Sprint 10"' in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_no_active_sprint(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = None
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show"])
    assert result.exit_code == 1
    assert "No active sprint" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_empty_sprint(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = _make_sprint()
    mock_client.sprints.get_sprint_issues.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show"])
    assert result.exit_code == 0
    assert "No issues" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_show_status_and_type_filters(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = 42
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_client.sprints.get_active_sprint.return_value = _make_sprint()
    mock_client.sprints.get_sprint_issues.return_value = []
    mock_jira_cls.from_connection.return_value = mock_client

    result = runner.invoke(app, ["-q", "sprint", "show", "--status", "In Progress", "--type", "Bug"])
    assert result.exit_code == 0
    call_args = mock_client.sprints.get_sprint_issues.call_args
    jql = call_args[1].get("jql_filter") or ""
    assert 'status = "In Progress"' in jql
    assert 'issuetype = "Bug"' in jql


def _mock_client_and_conn(mock_get_conn: Mock, mock_jira_cls: Mock, board_id: int | None = 42) -> MagicMock:
    """Wire up a mock connection + client for write-op tests."""
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_conn.project_key = "TEST"
    mock_conn.board_id = board_id
    mock_get_conn.return_value = mock_conn

    mock_client = MagicMock()
    mock_jira_cls.from_connection.return_value = mock_client
    return mock_client


# Sprint move tests


def test_sprint_move_help() -> None:
    result = runner.invoke(app, ["sprint", "move", "--help"])
    assert result.exit_code == 0


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_move_by_name(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10")

    result = runner.invoke(app, ["-q", "sprint", "move", "TEST-1", "TEST-2", "--to", "Sprint 10"])
    assert result.exit_code == 0
    mock_client.sprints.find_sprint_by_name.assert_called_once_with(42, "Sprint 10")
    mock_client.sprints.move_issues.assert_called_once_with(100, ["TEST-1", "TEST-2"])
    assert "Moved 2 issue(s)" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_move_by_id(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.get_sprint.return_value = _make_sprint(100, "Sprint 10")

    result = runner.invoke(app, ["-q", "sprint", "move", "TEST-1", "--sprint-id", "100"])
    assert result.exit_code == 0
    mock_client.sprints.get_sprint.assert_called_once_with(100)
    mock_client.sprints.move_issues.assert_called_once_with(100, ["TEST-1"])


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_move_by_id_skips_board_detection(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    """--sprint-id must not trigger board auto-detection (team-managed safe, #87)."""
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls, board_id=None)
    mock_client.sprints.get_sprint.return_value = _make_sprint(107, "Future Sprint", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "sprint", "move", "PROJ-1", "PROJ-2", "--sprint-id", "107"])
    assert result.exit_code == 0
    mock_client.sprints.move_issues.assert_called_once_with(107, ["PROJ-1", "PROJ-2"])
    # The whole point of #87: no board lookup at all when --sprint-id is given.
    mock_client.sprints.detect_board.assert_not_called()


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_move_requires_target(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    _mock_client_and_conn(mock_get_conn, mock_jira_cls)

    result = runner.invoke(app, ["-q", "sprint", "move", "TEST-1"])
    assert result.exit_code == 1
    assert "--to" in result.stdout or "--sprint-id" in result.stdout


# Sprint create tests


def test_sprint_create_help() -> None:
    result = runner.invoke(app, ["sprint", "create", "--help"])
    assert result.exit_code == 0


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_create_basic(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.create_sprint.return_value = _make_sprint(200, "Sprint 20", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "sprint", "create", "Sprint 20"])
    assert result.exit_code == 0
    mock_client.sprints.create_sprint.assert_called_once()
    kwargs = mock_client.sprints.create_sprint.call_args.kwargs
    assert kwargs["name"] == "Sprint 20"
    assert kwargs["board_id"] == 42
    assert kwargs["start_date"] is None
    assert "Created sprint 'Sprint 20'" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_create_with_future_dates(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.create_sprint.return_value = _make_sprint(200, "Sprint 20", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "sprint", "create", "Sprint 20", "--start", "today", "--end", "2099-12-31"])
    assert result.exit_code == 0
    kwargs = mock_client.sprints.create_sprint.call_args.kwargs
    assert kwargs["start_date"] is not None
    assert kwargs["end_date"] is not None
    assert kwargs["end_date"].year == 2099


# Sprint start tests


def test_sprint_start_help() -> None:
    result = runner.invoke(app, ["sprint", "start", "--help"])
    assert result.exit_code == 0


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_start_with_force(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10", SprintState.FUTURE)
    mock_client.sprints.start_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)

    result = runner.invoke(
        app, ["-q", "sprint", "start", "Sprint 10", "--start", "today", "--end", "2099-12-31", "--force"]
    )
    assert result.exit_code == 0
    mock_client.sprints.start_sprint.assert_called_once()
    assert mock_client.sprints.start_sprint.call_args.args[0] == 100
    assert "Started sprint 'Sprint 10'" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_start_requires_target(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    _mock_client_and_conn(mock_get_conn, mock_jira_cls)

    result = runner.invoke(app, ["-q", "sprint", "start", "--force"])
    assert result.exit_code == 1
    assert "No sprint specified" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_start_abort_on_decline(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "sprint", "start", "Sprint 10"], input="n\n")
    assert result.exit_code == 0
    mock_client.sprints.start_sprint.assert_not_called()
    assert "Aborted" in result.stdout


# Sprint close tests


def test_sprint_close_help() -> None:
    result = runner.invoke(app, ["sprint", "close", "--help"])
    assert result.exit_code == 0


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_close_active_with_force(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.get_active_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)
    mock_client.sprints.close_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.CLOSED)

    result = runner.invoke(app, ["-q", "sprint", "close", "--force"])
    assert result.exit_code == 0
    mock_client.sprints.close_sprint.assert_called_once_with(100)
    assert "Closed sprint 'Sprint 10'" in result.stdout


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_close_json_requires_force(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "close", "Sprint 10"])
    assert result.exit_code == 1
    assert "Confirmation required" in result.stdout
    mock_client.sprints.close_sprint.assert_not_called()


# JSON output contract tests (success paths)


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_move_json_output(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10")

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "move", "TEST-1", "TEST-2", "--to", "Sprint 10"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["moved"] == ["TEST-1", "TEST-2"]
    assert payload["sprint"]["id"] == 100
    assert payload["sprint"]["name"] == "Sprint 10"


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_create_json_output(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.create_sprint.return_value = _make_sprint(200, "Sprint 20", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "create", "Sprint 20"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == 200
    assert payload["state"] == "future"


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_start_json_output(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10", SprintState.FUTURE)
    mock_client.sprints.start_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)

    result = runner.invoke(
        app,
        ["-q", "--format", "json", "sprint", "start", "Sprint 10", "--start", "today", "--end", "2099-12-31", "-f"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == 100
    assert payload["state"] == "active"


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_close_json_output(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.get_active_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)
    mock_client.sprints.close_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.CLOSED)

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "close", "--force"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == 100
    assert payload["state"] == "closed"


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_start_json_requires_force(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.find_sprint_by_name.return_value = _make_sprint(100, "Sprint 10", SprintState.FUTURE)

    result = runner.invoke(app, ["-q", "--format", "json", "sprint", "start", "Sprint 10"])
    assert result.exit_code == 1
    assert "Confirmation required" in result.stdout
    mock_client.sprints.start_sprint.assert_not_called()


@patch("budjira.cli.sprint.JiraClient")
@patch("budjira.cli.sprint.get_active_connection")
def test_sprint_close_abort_on_decline(mock_get_conn: Mock, mock_jira_cls: Mock) -> None:
    mock_client = _mock_client_and_conn(mock_get_conn, mock_jira_cls)
    mock_client.sprints.get_active_sprint.return_value = _make_sprint(100, "Sprint 10", SprintState.ACTIVE)

    result = runner.invoke(app, ["-q", "sprint", "close"], input="n\n")
    assert result.exit_code == 0
    mock_client.sprints.close_sprint.assert_not_called()
    assert "Aborted" in result.stdout
