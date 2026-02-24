"""Tests for workflow CLI commands."""

from unittest.mock import MagicMock, Mock, patch

from budjira.cli.main import app
from budjira.models.connection import Connection, ConnectionList
from budjira.models.workflow import (
    BookingStatus,
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)
from typer.testing import CliRunner

runner = CliRunner()


def _make_profile(name: str = "ek-to-k") -> WorkflowProfile:
    return WorkflowProfile(
        name=name,
        planning_connection="ek-planning",
        booking_connection="k-booking",
        project_mappings=[
            ProjectMapping(planning_project="EK", booking_project="K"),
        ],
        shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH,
        overbooking_policy=OverbookingPolicy.WARN,
    )


def _make_connections() -> ConnectionList:
    return ConnectionList(
        connections=[
            Connection(
                name="ek-planning",
                url="https://planning.atlassian.net",  # type: ignore[arg-type]
                email="user@example.com",
                project_key="EK",
            ),
            Connection(
                name="k-booking",
                url="https://booking.atlassian.net",  # type: ignore[arg-type]
                email="user@example.com",
                project_key="K",
                tempo_enabled=True,
            ),
        ]
    )


# Help tests


def test_workflow_help() -> None:
    result = runner.invoke(app, ["workflow", "--help"])
    assert result.exit_code == 0
    assert "workflow" in result.stdout.lower()


def test_workflow_list_help() -> None:
    result = runner.invoke(app, ["workflow", "list", "--help"])
    assert result.exit_code == 0


def test_workflow_show_help() -> None:
    result = runner.invoke(app, ["workflow", "show", "--help"])
    assert result.exit_code == 0


def test_workflow_remove_help() -> None:
    result = runner.invoke(app, ["workflow", "remove", "--help"])
    assert result.exit_code == 0


def test_workflow_status_help() -> None:
    result = runner.invoke(app, ["workflow", "status", "--help"])
    assert result.exit_code == 0


def test_workflow_book_help() -> None:
    result = runner.invoke(app, ["workflow", "book", "--help"])
    assert result.exit_code == 0


# List tests


@patch("budjira.cli.workflow.get_settings")
def test_workflow_list_empty(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "list"])
    assert result.exit_code == 0
    assert "No workflow profiles" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_list_with_profiles(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile()])
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "list"])
    assert result.exit_code == 0
    assert "ek-to-k" in result.stdout
    assert "ek-planning" in result.stdout
    assert "k-booking" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_list_json(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile()])
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "list"])
    assert result.exit_code == 0
    assert '"ek-to-k"' in result.stdout
    assert '"total": 1' in result.stdout


# Show tests


@patch("budjira.cli.workflow.get_settings")
def test_workflow_show_found(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile()])
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "show", "ek-to-k"])
    assert result.exit_code == 0
    assert "ek-to-k" in result.stdout
    assert "ek-planning" in result.stdout
    assert "k-booking" in result.stdout
    assert "EK" in result.stdout
    assert "K" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_show_not_found(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_show_json(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile()])
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "show", "ek-to-k"])
    assert result.exit_code == 0
    assert '"name": "ek-to-k"' in result.stdout


# Remove tests


@patch("budjira.cli.workflow.get_settings")
def test_workflow_remove_with_force(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    profile = _make_profile()
    workflows = WorkflowProfileList(profiles=[profile])
    mock_settings.workflows = workflows
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "remove", "ek-to-k", "--force"])
    assert result.exit_code == 0
    assert "removed" in result.stdout.lower()
    mock_settings.save_workflows.assert_called_once()


@patch("budjira.cli.workflow.get_settings")
def test_workflow_remove_not_found(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "remove", "nonexistent", "--force"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_remove_cancelled(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile()])
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "remove", "ek-to-k"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.stdout.lower()
    mock_settings.save_workflows.assert_not_called()


# Setup tests


@patch("budjira.cli.workflow.get_settings")
def test_workflow_setup_interactive(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_settings.connections = _make_connections()
    mock_get_settings.return_value = mock_settings

    user_input = "\n".join(
        [
            "my-profile",  # Profile name
            "ek-planning",  # Planning connection
            "k-booking",  # Booking connection
            "EK",  # Planning project
            "K",  # Booking project
            "n",  # No more mappings
            "summary",  # Shadow strategy
            "warn",  # Overbooking policy
        ]
    )

    result = runner.invoke(app, ["-q", "workflow", "setup"], input=user_input + "\n")
    assert result.exit_code == 0
    assert "created successfully" in result.stdout
    mock_settings.save_workflows.assert_called_once()


@patch("budjira.cli.workflow.get_settings")
def test_workflow_setup_duplicate_name(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList(profiles=[_make_profile("existing")])
    mock_settings.connections = _make_connections()
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "setup"], input="existing\n")
    assert result.exit_code == 1
    assert "already exists" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_setup_too_few_connections(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_settings.connections = ConnectionList(
        connections=[
            Connection(
                name="single",
                url="https://test.atlassian.net",  # type: ignore[arg-type]
                email="user@example.com",
                project_key="TEST",
            ),
        ]
    )
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "setup"], input="test\n")
    assert result.exit_code == 1
    assert "At least 2 connections" in result.stdout


@patch("budjira.cli.workflow.get_settings")
def test_workflow_setup_booking_no_tempo(mock_get_settings: Mock) -> None:
    mock_settings = MagicMock()
    mock_settings.workflows = WorkflowProfileList()
    mock_settings.connections = ConnectionList(
        connections=[
            Connection(
                name="plan",
                url="https://plan.atlassian.net",  # type: ignore[arg-type]
                email="user@example.com",
                project_key="PLAN",
            ),
            Connection(
                name="book",
                url="https://book.atlassian.net",  # type: ignore[arg-type]
                email="user@example.com",
                project_key="BOOK",
                tempo_enabled=False,
            ),
        ]
    )
    mock_get_settings.return_value = mock_settings

    result = runner.invoke(app, ["-q", "workflow", "setup"], input="test\nplan\nbook\n")
    assert result.exit_code == 1
    assert "Tempo" in result.stdout


# Status tests


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_status_success(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()
    mock_service.get_booking_status.return_value = BookingStatus(
        planning_issue_key="EK-123",
        planning_summary="Fix login bug",
        booking_issue_key="K-456",
        estimate_seconds=28800,
        spent_seconds=19800,
        remaining_seconds=9000,
        is_overbooked=False,
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "status", "EK-123", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    assert "EK-123" in result.stdout
    assert "K-456" in result.stdout
    assert "Fix login bug" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_status_no_shadow(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()
    mock_service.get_booking_status.return_value = BookingStatus(
        planning_issue_key="EK-123",
        planning_summary="New task",
        booking_issue_key=None,
        estimate_seconds=28800,
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "status", "EK-123", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    assert "Not found" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_status_json(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()
    mock_service.get_booking_status.return_value = BookingStatus(
        planning_issue_key="EK-123",
        planning_summary="Test",
        booking_issue_key="K-456",
        estimate_seconds=28800,
        spent_seconds=19800,
        remaining_seconds=9000,
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "status", "EK-123", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    assert '"EK-123"' in result.stdout
    assert '"K-456"' in result.stdout


# Book tests


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_book_success(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_worklog = MagicMock()
    mock_worklog.tempoWorklogId = 12345
    mock_service.book_time.return_value = mock_worklog
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "book", "EK-123", "2h", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    mock_service.book_time.assert_called_once_with(
        planning_issue_key="EK-123",
        time_spent="2h",
        comment=None,
        started=None,
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_book_with_options(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_worklog = MagicMock()
    mock_worklog.tempoWorklogId = 12345
    mock_service.book_time.return_value = mock_worklog
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(
        app,
        [
            "-q",
            "workflow",
            "book",
            "EK-123",
            "2h30m",
            "--profile",
            "ek-to-k",
            "--comment",
            "Analysis work",
            "--started",
            "yesterday",
        ],
    )
    assert result.exit_code == 0
    mock_service.book_time.assert_called_once_with(
        planning_issue_key="EK-123",
        time_spent="2h30m",
        comment="Analysis work",
        started="yesterday",
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_book_shadow_not_found(mock_service_cls: Mock) -> None:
    from budjira.utils.errors import ShadowTicketNotFoundError

    mock_service = MagicMock()
    mock_service.book_time.side_effect = ShadowTicketNotFoundError("Shadow not found")
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "book", "EK-123", "2h", "--profile", "ek-to-k"])
    assert result.exit_code == 1
    assert "Shadow not found" in result.stdout


# Sprint overview tests


def test_workflow_sprint_help() -> None:
    result = runner.invoke(app, ["workflow", "sprint", "--help"])
    assert result.exit_code == 0


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_sprint_no_profile(mock_service_cls: Mock) -> None:
    result = runner.invoke(app, ["-q", "workflow", "sprint"])
    assert result.exit_code == 1
    assert "profile" in result.stdout.lower()


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_sprint_table_output(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()

    # Mock planning connection
    mock_planning_conn = MagicMock()
    mock_planning_conn.board_id = 42
    mock_service.planning_jira.connection = mock_planning_conn

    # Mock sprint
    from datetime import date

    from budjira.models.sprint import Sprint, SprintState

    mock_sprint = Sprint(
        id=100,
        name="Sprint 10",
        state=SprintState.ACTIVE,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 1, 29),
    )
    mock_service.planning_jira.sprints.get_active_sprint.return_value = mock_sprint

    # Mock overview
    mock_service.get_sprint_booking_overview.return_value = [
        BookingStatus(
            planning_issue_key="EK-1",
            planning_summary="Task 1",
            booking_issue_key="K-10",
            estimate_seconds=7200,
            spent_seconds=3600,
            remaining_seconds=3600,
        ),
    ]

    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "sprint", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    assert "Sprint 10" in result.stdout
    assert "EK-1" in result.stdout
    assert "K-10" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_sprint_json_output(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()

    mock_planning_conn = MagicMock()
    mock_planning_conn.board_id = 42
    mock_service.planning_jira.connection = mock_planning_conn

    from datetime import date

    from budjira.models.sprint import Sprint, SprintState

    mock_sprint = Sprint(
        id=100,
        name="Sprint 10",
        state=SprintState.ACTIVE,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 1, 29),
    )
    mock_service.planning_jira.sprints.get_active_sprint.return_value = mock_sprint

    mock_service.get_sprint_booking_overview.return_value = [
        BookingStatus(
            planning_issue_key="EK-1",
            planning_summary="Task 1",
            booking_issue_key="K-10",
            estimate_seconds=7200,
            spent_seconds=3600,
            remaining_seconds=3600,
        ),
    ]
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "sprint", "--profile", "ek-to-k"])
    assert result.exit_code == 0
    assert '"EK-1"' in result.stdout
    assert '"Sprint 10"' in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_sprint_unbooked_filter(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()

    mock_planning_conn = MagicMock()
    mock_planning_conn.board_id = 42
    mock_service.planning_jira.connection = mock_planning_conn

    from datetime import date

    from budjira.models.sprint import Sprint, SprintState

    mock_sprint = Sprint(
        id=100,
        name="Sprint 10",
        state=SprintState.ACTIVE,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 1, 29),
    )
    mock_service.planning_jira.sprints.get_active_sprint.return_value = mock_sprint

    mock_service.get_sprint_booking_overview.return_value = [
        BookingStatus(
            planning_issue_key="EK-1",
            planning_summary="Fully booked",
            booking_issue_key="K-10",
            estimate_seconds=7200,
            spent_seconds=7200,
            remaining_seconds=0,
        ),
        BookingStatus(
            planning_issue_key="EK-2",
            planning_summary="Partially booked",
            booking_issue_key="K-20",
            estimate_seconds=7200,
            spent_seconds=3600,
            remaining_seconds=3600,
        ),
    ]
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "sprint", "--profile", "ek-to-k", "--unbooked"])
    assert result.exit_code == 0
    # EK-2 should be shown (remaining > 0), EK-1 should be filtered out
    assert "EK-2" in result.stdout
    assert "EK-1" not in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_sprint_no_active_sprint(mock_service_cls: Mock) -> None:
    mock_service = MagicMock()
    mock_service.profile = _make_profile()

    mock_planning_conn = MagicMock()
    mock_planning_conn.board_id = 42
    mock_service.planning_jira.connection = mock_planning_conn

    mock_service.planning_jira.sprints.get_active_sprint.return_value = None
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "sprint", "--profile", "ek-to-k"])
    assert result.exit_code == 1
    assert "No active sprint" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_book_overbooking_blocked(mock_service_cls: Mock) -> None:
    from budjira.utils.errors import OverbookingError

    mock_service = MagicMock()
    mock_service.book_time.side_effect = OverbookingError("Blocked by policy")
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "book", "EK-123", "2h", "--profile", "ek-to-k"])
    assert result.exit_code == 1
    assert "Blocked" in result.stdout
