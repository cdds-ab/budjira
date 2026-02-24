"""Tests for sprint models."""

from unittest.mock import MagicMock

from budjira.models.sprint import Board, Sprint, SprintState, SprintSummary


class TestSprintState:
    """Tests for SprintState enum."""

    def test_active(self) -> None:
        assert SprintState.ACTIVE.value == "active"

    def test_future(self) -> None:
        assert SprintState.FUTURE.value == "future"

    def test_closed(self) -> None:
        assert SprintState.CLOSED.value == "closed"

    def test_from_string(self) -> None:
        assert SprintState("active") == SprintState.ACTIVE
        assert SprintState("future") == SprintState.FUTURE
        assert SprintState("closed") == SprintState.CLOSED


class TestBoard:
    """Tests for Board model."""

    def test_basic_creation(self) -> None:
        board = Board(id=1, name="My Board", board_type="scrum")
        assert board.id == 1
        assert board.name == "My Board"
        assert board.board_type == "scrum"

    def test_from_jira_board(self) -> None:
        mock_board = MagicMock()
        mock_board.id = 42
        mock_board.name = "Test Board"
        mock_board.raw = {"type": "scrum"}

        board = Board.from_jira_board(mock_board)
        assert board.id == 42
        assert board.name == "Test Board"
        assert board.board_type == "scrum"

    def test_from_jira_board_no_raw(self) -> None:
        mock_board = MagicMock(spec=["id", "name"])
        mock_board.id = 1
        mock_board.name = "Board"

        board = Board.from_jira_board(mock_board)
        assert board.board_type == "unknown"

    def test_from_jira_board_kanban(self) -> None:
        mock_board = MagicMock()
        mock_board.id = 10
        mock_board.name = "Kanban Board"
        mock_board.raw = {"type": "kanban"}

        board = Board.from_jira_board(mock_board)
        assert board.board_type == "kanban"


class TestSprint:
    """Tests for Sprint model."""

    def test_basic_creation(self) -> None:
        sprint = Sprint(id=1, name="Sprint 1", state=SprintState.ACTIVE)
        assert sprint.id == 1
        assert sprint.name == "Sprint 1"
        assert sprint.state == SprintState.ACTIVE
        assert sprint.start_date is None
        assert sprint.end_date is None

    def test_from_jira_sprint_active(self) -> None:
        mock_sprint = MagicMock()
        mock_sprint.id = 100
        mock_sprint.name = "Sprint 10"
        mock_sprint.state = "active"
        mock_sprint.raw = {
            "state": "active",
            "startDate": "2025-01-15T10:00:00.000Z",
            "endDate": "2025-01-29T10:00:00.000Z",
            "originBoardId": 42,
        }

        sprint = Sprint.from_jira_sprint(mock_sprint)
        assert sprint.id == 100
        assert sprint.name == "Sprint 10"
        assert sprint.state == SprintState.ACTIVE
        assert sprint.start_date is not None
        assert sprint.start_date.isoformat() == "2025-01-15"
        assert sprint.end_date is not None
        assert sprint.end_date.isoformat() == "2025-01-29"
        assert sprint.board_id == 42

    def test_from_jira_sprint_closed_with_complete_date(self) -> None:
        mock_sprint = MagicMock()
        mock_sprint.id = 99
        mock_sprint.name = "Sprint 9"
        mock_sprint.state = "closed"
        mock_sprint.raw = {
            "state": "closed",
            "startDate": "2025-01-01T00:00:00.000Z",
            "endDate": "2025-01-15T00:00:00.000Z",
            "completeDate": "2025-01-14T16:30:00.000Z",
            "originBoardId": 42,
        }

        sprint = Sprint.from_jira_sprint(mock_sprint)
        assert sprint.state == SprintState.CLOSED
        assert sprint.complete_date is not None
        assert sprint.complete_date.isoformat() == "2025-01-14"

    def test_from_jira_sprint_future_no_dates(self) -> None:
        mock_sprint = MagicMock()
        mock_sprint.id = 101
        mock_sprint.name = "Sprint 11"
        mock_sprint.state = "future"
        mock_sprint.raw = {"state": "future"}

        sprint = Sprint.from_jira_sprint(mock_sprint)
        assert sprint.state == SprintState.FUTURE
        assert sprint.start_date is None
        assert sprint.end_date is None
        assert sprint.complete_date is None
        assert sprint.board_id is None

    def test_from_jira_sprint_unknown_state_defaults_to_future(self) -> None:
        mock_sprint = MagicMock()
        mock_sprint.id = 1
        mock_sprint.name = "Unknown"
        mock_sprint.state = "WEIRD_STATE"
        mock_sprint.raw = {"state": "WEIRD_STATE"}

        sprint = Sprint.from_jira_sprint(mock_sprint)
        assert sprint.state == SprintState.FUTURE

    def test_parse_date_none(self) -> None:
        assert Sprint._parse_date(None) is None

    def test_parse_date_empty(self) -> None:
        assert Sprint._parse_date("") is None

    def test_parse_date_invalid(self) -> None:
        assert Sprint._parse_date("not-a-date") is None

    def test_parse_date_valid_iso(self) -> None:
        result = Sprint._parse_date("2025-03-15T00:00:00.000Z")
        assert result is not None
        assert result.isoformat() == "2025-03-15"


class TestSprintSummary:
    """Tests for SprintSummary model."""

    def test_defaults(self) -> None:
        sprint = Sprint(id=1, name="S1", state=SprintState.ACTIVE)
        summary = SprintSummary(sprint=sprint)
        assert summary.total_issues == 0
        assert summary.done_issues == 0
        assert summary.in_progress_issues == 0
        assert summary.todo_issues == 0

    def test_with_values(self) -> None:
        sprint = Sprint(id=1, name="S1", state=SprintState.ACTIVE)
        summary = SprintSummary(
            sprint=sprint,
            total_issues=10,
            done_issues=3,
            in_progress_issues=4,
            todo_issues=3,
        )
        assert summary.total_issues == 10
        assert summary.done_issues == 3
