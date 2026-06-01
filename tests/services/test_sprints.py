"""Tests for SprintService."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from budjira.models.issue import Issue
from budjira.services.sprints import SprintService
from budjira.utils.errors import JiraAPIError, PermissionError
from jira.exceptions import JIRAError


@pytest.fixture
def mock_jira_client() -> MagicMock:
    """Create a mock JIRA client."""
    return MagicMock()


@pytest.fixture
def service(mock_jira_client: MagicMock) -> SprintService:
    """Create a SprintService with mock client."""
    return SprintService(mock_jira_client)


def _make_jira_board(board_id: int = 42, name: str = "Test Board", board_type: str = "scrum") -> MagicMock:
    """Create a mock Jira board object."""
    board = MagicMock()
    board.id = board_id
    board.name = name
    board.raw = {"type": board_type}
    return board


def _make_jira_sprint(
    sprint_id: int = 100,
    name: str = "Sprint 10",
    state: str = "active",
) -> MagicMock:
    """Create a mock Jira sprint object."""
    sprint = MagicMock()
    sprint.id = sprint_id
    sprint.name = name
    sprint.state = state
    sprint.raw = {
        "state": state,
        "startDate": "2025-01-15T10:00:00.000Z",
        "endDate": "2025-01-29T10:00:00.000Z",
        "originBoardId": 42,
    }
    return sprint


def _make_issue(key: str = "TEST-1", summary: str = "Test issue") -> Issue:
    """Create a sample Issue."""
    return Issue(
        key=key,
        summary=summary,
        issue_type="Story",
        status="To Do",
        project_key=key.split("-")[0],
    )


class TestGetBoards:
    """Tests for SprintService.get_boards."""

    def test_returns_boards(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = [
            _make_jira_board(1, "Board 1"),
            _make_jira_board(2, "Board 2"),
        ]

        boards = service.get_boards("TEST")
        assert len(boards) == 2
        assert boards[0].id == 1
        assert boards[1].id == 2
        # No server-side type filter so team-managed ('simple') boards are visible too.
        mock_jira_client.boards.assert_called_once_with(projectKeyOrID="TEST")

    def test_empty_boards(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = []
        boards = service.get_boards("TEST")
        assert boards == []

    def test_jira_error(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.side_effect = JIRAError(status_code=403, text="Forbidden")
        with pytest.raises((JiraAPIError, PermissionError)):
            service.get_boards("TEST")


class TestDetectBoard:
    """Tests for SprintService.detect_board."""

    def test_single_board(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = [_make_jira_board(42, "My Board")]

        board = service.detect_board("TEST")
        assert board.id == 42
        assert board.name == "My Board"

    def test_team_managed_simple_board(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        # Team-managed projects expose a board of type 'simple' (not 'scrum').
        mock_jira_client.boards.return_value = [_make_jira_board(99, "TM Board", board_type="simple")]

        board = service.detect_board("TEST")
        assert board.id == 99
        assert board.board_type == "simple"

    def test_no_boards(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = []
        with pytest.raises(JiraAPIError, match="No sprint-capable board"):
            service.detect_board("TEST")

    def test_kanban_only_is_not_sprint_capable(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = [_make_jira_board(7, "Kanban", board_type="kanban")]
        with pytest.raises(JiraAPIError, match="No sprint-capable board"):
            service.detect_board("TEST")

    def test_multiple_boards(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.boards.return_value = [
            _make_jira_board(1, "Board A"),
            _make_jira_board(2, "Board B"),
        ]
        with pytest.raises(JiraAPIError, match="Multiple sprint-capable boards"):
            service.detect_board("TEST")

    def test_kanban_ignored_when_one_sprint_board(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        # A kanban board alongside one scrum board must not trigger the "multiple" error.
        mock_jira_client.boards.return_value = [
            _make_jira_board(1, "Kanban", board_type="kanban"),
            _make_jira_board(2, "Scrum", board_type="scrum"),
        ]
        board = service.detect_board("TEST")
        assert board.id == 2


class TestGetSprints:
    """Tests for SprintService.get_sprints."""

    def test_all_sprints(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [
            _make_jira_sprint(1, "Sprint 1", "closed"),
            _make_jira_sprint(2, "Sprint 2", "active"),
            _make_jira_sprint(3, "Sprint 3", "future"),
        ]

        sprints = service.get_sprints(42)
        assert len(sprints) == 3
        mock_jira_client.sprints.assert_called_once_with(42, state=None)

    def test_filtered_by_state(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [_make_jira_sprint(2, "Sprint 2", "active")]

        sprints = service.get_sprints(42, state="active")
        assert len(sprints) == 1
        mock_jira_client.sprints.assert_called_once_with(42, state="active")

    def test_jira_error(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.side_effect = JIRAError(status_code=404, text="Board not found")
        from budjira.utils.errors import InvalidIssueError

        with pytest.raises(InvalidIssueError):
            service.get_sprints(999)


class TestGetActiveSprint:
    """Tests for SprintService.get_active_sprint."""

    def test_active_sprint_found(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [_make_jira_sprint(10, "Active Sprint", "active")]

        sprint = service.get_active_sprint(42)
        assert sprint is not None
        assert sprint.name == "Active Sprint"

    def test_no_active_sprint(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = []

        sprint = service.get_active_sprint(42)
        assert sprint is None


class TestGetSprintIssues:
    """Tests for SprintService.get_sprint_issues."""

    @patch("budjira.services.issues.IssueService")
    def test_basic_sprint_issues(self, mock_issue_service_class: MagicMock, service: SprintService) -> None:
        mock_issue_service = MagicMock()
        issues = [_make_issue("TEST-1"), _make_issue("TEST-2")]
        mock_issue_service.search.return_value = issues
        mock_issue_service_class.return_value = mock_issue_service

        result = service.get_sprint_issues(100)
        assert len(result) == 2
        mock_issue_service.search.assert_called_once_with("sprint = 100", max_results=200)

    @patch("budjira.services.issues.IssueService")
    def test_sprint_issues_with_filter(self, mock_issue_service_class: MagicMock, service: SprintService) -> None:
        mock_issue_service = MagicMock()
        mock_issue_service.search.return_value = [_make_issue("TEST-1")]
        mock_issue_service_class.return_value = mock_issue_service

        service.get_sprint_issues(100, jql_filter="assignee = currentUser()")
        mock_issue_service.search.assert_called_once_with("sprint = 100 AND assignee = currentUser()", max_results=200)

    @patch("budjira.services.issues.IssueService")
    def test_sprint_issues_empty(self, mock_issue_service_class: MagicMock, service: SprintService) -> None:
        mock_issue_service = MagicMock()
        mock_issue_service.search.return_value = []
        mock_issue_service_class.return_value = mock_issue_service

        result = service.get_sprint_issues(100)
        assert result == []


class TestFindSprintByName:
    """Tests for SprintService.find_sprint_by_name."""

    def test_exact_match(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [
            _make_jira_sprint(1, "Sprint 1", "closed"),
            _make_jira_sprint(2, "Sprint 2", "active"),
        ]

        sprint = service.find_sprint_by_name(42, "Sprint 2")
        assert sprint.name == "Sprint 2"

    def test_case_insensitive(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [_make_jira_sprint(1, "Sprint Alpha", "active")]

        sprint = service.find_sprint_by_name(42, "sprint alpha")
        assert sprint.name == "Sprint Alpha"

    def test_partial_match(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [
            _make_jira_sprint(1, "Project X Sprint 5", "active"),
        ]

        sprint = service.find_sprint_by_name(42, "Sprint 5")
        assert sprint.name == "Project X Sprint 5"

    def test_not_found(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [_make_jira_sprint(1, "Sprint 1", "active")]

        with pytest.raises(JiraAPIError, match="not found"):
            service.find_sprint_by_name(42, "Sprint 99")

    def test_ambiguous_match_with_exact(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        """Exact match should win when multiple partial matches exist."""
        mock_jira_client.sprints.return_value = [
            _make_jira_sprint(1, "Sprint 1", "closed"),
            _make_jira_sprint(2, "Sprint 10", "active"),
            _make_jira_sprint(3, "Sprint 11", "future"),
        ]

        sprint = service.find_sprint_by_name(42, "Sprint 1")
        assert sprint.name == "Sprint 1"

    def test_ambiguous_without_exact(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprints.return_value = [
            _make_jira_sprint(1, "Alpha Sprint 1", "closed"),
            _make_jira_sprint(2, "Beta Sprint 1", "active"),
        ]

        with pytest.raises(JiraAPIError, match="Multiple sprints match"):
            service.find_sprint_by_name(42, "Sprint 1")


class TestGetSprint:
    """Tests for SprintService.get_sprint."""

    def test_returns_sprint(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprint.return_value = _make_jira_sprint(100, "Sprint 10", "active")

        sprint = service.get_sprint(100)
        assert sprint.id == 100
        assert sprint.name == "Sprint 10"
        mock_jira_client.sprint.assert_called_once_with(100)

    def test_not_found(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        from budjira.utils.errors import InvalidIssueError

        mock_jira_client.sprint.side_effect = JIRAError(status_code=404, text="Not found")
        with pytest.raises(InvalidIssueError, match="not found"):
            service.get_sprint(999)


class TestMoveIssues:
    """Tests for SprintService.move_issues."""

    def test_moves_issues(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        service.move_issues(100, ["TEST-1", "TEST-2"])
        mock_jira_client.add_issues_to_sprint.assert_called_once_with(sprint_id=100, issue_keys=["TEST-1", "TEST-2"])

    def test_permission_error(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.add_issues_to_sprint.side_effect = JIRAError(status_code=403, text="Forbidden")
        with pytest.raises(PermissionError):
            service.move_issues(100, ["TEST-1"])


class TestCreateSprint:
    """Tests for SprintService.create_sprint."""

    def test_creates_sprint(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_sprint.return_value = _make_jira_sprint(200, "Sprint 20", "future")

        sprint = service.create_sprint(42, "Sprint 20")
        assert sprint.id == 200
        assert sprint.name == "Sprint 20"
        mock_jira_client.create_sprint.assert_called_once_with(
            name="Sprint 20", board_id=42, startDate=None, endDate=None, goal=None
        )

    def test_creates_sprint_with_dates_and_goal(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_sprint.return_value = _make_jira_sprint(200, "Sprint 20", "future")

        start = datetime(2026, 6, 1, 0, 0, 0)
        end = datetime(2026, 6, 14, 0, 0, 0)
        service.create_sprint(42, "Sprint 20", start_date=start, end_date=end, goal="Ship it")

        mock_jira_client.create_sprint.assert_called_once_with(
            name="Sprint 20",
            board_id=42,
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            goal="Ship it",
        )

    def test_permission_error(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.create_sprint.side_effect = JIRAError(status_code=403, text="Forbidden")
        with pytest.raises(PermissionError):
            service.create_sprint(42, "Sprint 20")


class TestSprintStateTransitions:
    """Tests for SprintService.start_sprint and close_sprint."""

    def test_start_sprint(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprint.return_value = _make_jira_sprint(100, "Sprint 10", "active")
        start = datetime(2026, 6, 1, 0, 0, 0)
        end = datetime(2026, 6, 14, 0, 0, 0)

        sprint = service.start_sprint(100, start_date=start, end_date=end)
        assert sprint.state.value == "active"
        mock_jira_client.update_sprint.assert_called_once_with(
            id=100, state="active", startDate=start.isoformat(), endDate=end.isoformat()
        )
        mock_jira_client.sprint.assert_called_once_with(100)

    def test_close_sprint(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.sprint.return_value = _make_jira_sprint(100, "Sprint 10", "closed")

        sprint = service.close_sprint(100)
        assert sprint.state.value == "closed"
        mock_jira_client.update_sprint.assert_called_once_with(id=100, state="closed", startDate=None, endDate=None)

    def test_start_sprint_error(self, service: SprintService, mock_jira_client: MagicMock) -> None:
        mock_jira_client.update_sprint.side_effect = JIRAError(status_code=400, text="No dates set")
        with pytest.raises(JiraAPIError):
            service.start_sprint(100)
