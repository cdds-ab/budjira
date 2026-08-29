"""Tests for workflow CLI commands."""

import calendar
from datetime import date
from unittest.mock import MagicMock, Mock, patch

from budjira.cli.main import app
from budjira.models.billing import (
    BillingGroup,
    BillingLine,
    BillingReport,
    BillingTotals,
    BillingValidation,
    BillingViolation,
)
from budjira.models.connection import Connection, ConnectionList
from budjira.models.workflow import (
    BookingStatus,
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)
from budjira.utils.errors import BillingValidationError, WorkflowConfigError
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


# Billing tests (#117)


def _billing_report() -> BillingReport:
    """Build a small billing report with two buckets."""
    return BillingReport(
        profile="ek-to-k",
        period_from=date(2026, 8, 1),
        period_to=date(2026, 8, 31),
        excluded_from_total=["project"],
        groups=[
            BillingGroup(
                name="billable",
                bucket="billable",
                lines=[
                    BillingLine(
                        issue="EK-10",
                        booking_issue="K-1",
                        category="analysis",
                        bucket="billable",
                        summary="Analysis work",
                        seconds=7200,
                        hours=2.0,
                    )
                ],
                total_seconds=7200,
                total_hours=2.0,
            ),
            BillingGroup(
                name="project",
                bucket="project",
                lines=[
                    BillingLine(
                        issue="EK-12",
                        booking_issue="K-3",
                        category="onboarding",
                        bucket="project",
                        summary="Onboarding",
                        seconds=1800,
                        hours=0.5,
                    )
                ],
                total_seconds=1800,
                total_hours=0.5,
            ),
        ],
        totals=BillingTotals(seconds=7200, hours=2.0),
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_table(mock_service_cls: Mock) -> None:
    """Table output shows groups, line details and the total without the excluded bucket."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--month", "2026-08"])

    assert result.exit_code == 0
    assert "Billing Report: ek-to-k" in result.stdout
    assert "billable" in result.stdout
    assert "EK-10" in result.stdout
    assert "project" in result.stdout  # excluded bucket is still shown
    assert "excluding: project" in result.stdout
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 8, 31), group_by="bucket", mine=False
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_json(mock_service_cls: Mock) -> None:
    """JSON output emits the deterministic report schema for agents/scripts."""
    import json

    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["profile"] == "ek-to-k"
    assert payload["period_from"] == "2026-08-01"
    assert payload["period_to"] == "2026-08-31"
    assert payload["grouped_by"] == "bucket"
    assert payload["groups"][0]["name"] == "billable"
    assert payload["groups"][0]["lines"][0]["issue"] == "EK-10"
    assert payload["totals"]["seconds"] == 7200
    assert payload["excluded_from_total"] == ["project"]
    assert payload["warnings"] == []


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_default_month_is_current(mock_service_cls: Mock) -> None:
    """Without --month/--from/--to the current month is reported."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    today = date.today()
    _, last_day = calendar.monthrange(today.year, today.month)
    mock_service.get_billing_report.assert_called_once_with(
        date(today.year, today.month, 1),
        date(today.year, today.month, last_day),
        group_by="bucket",
        mine=False,
    )


def test_workflow_billing_month_and_from_conflict() -> None:
    """--month and --from/--to are mutually exclusive."""
    result = runner.invoke(
        app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--month", "2026-08", "--from", "2026-08-01"]
    )

    assert result.exit_code == 1
    assert "cannot be combined" in result.stdout


def test_workflow_billing_from_without_to() -> None:
    """--from requires --to."""
    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--from", "2026-08-01"])

    assert result.exit_code == 1
    assert "must be given together" in result.stdout


def test_workflow_billing_from_after_to() -> None:
    """An inverted period is rejected."""
    result = runner.invoke(
        app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--from", "2026-08-31", "--to", "2026-08-01"]
    )

    assert result.exit_code == 1
    assert "must not be after" in result.stdout


def test_workflow_billing_invalid_month() -> None:
    """An invalid --month value is rejected."""
    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--month", "2026-13"])

    assert result.exit_code == 1
    assert "Invalid month format" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_from_to(mock_service_cls: Mock) -> None:
    """--from/--to override --month."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(
        app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--from", "2026-08-01", "--to", "2026-09-30"]
    )

    assert result.exit_code == 0
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 9, 30), group_by="bucket", mine=False
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_group_category(mock_service_cls: Mock) -> None:
    """--group category is passed through to the service."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--group", "category"])

    assert result.exit_code == 0
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 8, 31), group_by="category", mine=False
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_bucket_filter_json(mock_service_cls: Mock) -> None:
    """--bucket filters the groups and recomputes the totals over the shown lines."""
    import json

    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(
        app, ["-q", "--format", "json", "workflow", "billing", "--profile", "ek-to-k", "--bucket", "project"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [group["name"] for group in payload["groups"]] == ["project"]
    # Totals reflect the filter, not the exclusion
    assert payload["totals"]["seconds"] == 1800


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_validate_clean(mock_service_cls: Mock) -> None:
    """--validate exits 0 when all issues carry exactly one category label."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.validate_billing_labels.return_value = BillingValidation(
        profile="ek-to-k", issues_checked=5, violations=[]
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--validate"])

    assert result.exit_code == 0
    assert "exactly one category label" in result.stdout
    mock_service.get_billing_report.assert_not_called()


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_validate_violations_exit_1(mock_service_cls: Mock) -> None:
    """--validate exits 1 and lists violations (CI/agent friendly)."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.validate_billing_labels.return_value = BillingValidation(
        profile="ek-to-k",
        issues_checked=5,
        violations=[BillingViolation(issue="EK-11", kind="missing", summary="No label")],
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--validate"])

    assert result.exit_code == 1
    assert "EK-11" in result.stdout
    assert "missing" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_validate_json(mock_service_cls: Mock) -> None:
    """--validate emits structured JSON."""
    import json

    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.validate_billing_labels.return_value = BillingValidation(
        profile="ek-to-k",
        issues_checked=5,
        violations=[BillingViolation(issue="EK-12", kind="multiple", labels=["analysis", "support"])],
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "billing", "--profile", "ek-to-k", "--validate"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["issues_checked"] == 5
    assert payload["violations"][0]["issue"] == "EK-12"
    assert payload["violations"][0]["labels"] == ["analysis", "support"]


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_no_billing_block(mock_service_cls: Mock) -> None:
    """A profile without a billing block fails with a configuration hint."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.side_effect = WorkflowConfigError(
        "Workflow profile 'ek-to-k' has no billing configuration."
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 1
    assert "no billing configuration" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_multiple_labels_error(mock_service_cls: Mock) -> None:
    """A BillingValidationError from the service surfaces with the offending issues."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.side_effect = BillingValidationError(
        "Issues with multiple category labels: EK-10 (analysis, support)."
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 1
    assert "EK-10" in result.stdout
    assert result.exit_code == 1
    assert "EK-10" in result.stdout


def test_workflow_billing_invalid_from_date() -> None:
    """A malformed --from date is rejected with a usage error."""
    result = runner.invoke(
        app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--from", "01.08.2026", "--to", "2026-08-31"]
    )

    assert result.exit_code == 1
    assert "Invalid date" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_with_rate_renders_amounts(mock_service_cls: Mock) -> None:
    """A configured rate adds the rate header and amount columns."""
    report = _billing_report()
    report.rate = 95.0
    report.groups[0].lines[0].amount = 190.0
    report.groups[0].total_amount = 190.0
    report.totals.amount = 190.0
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    assert "95.00 EUR/h" in result.stdout
    assert "190.00 EUR" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_empty_period(mock_service_cls: Mock) -> None:
    """An empty period renders a clear message instead of empty tables."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = BillingReport(
        profile="ek-to-k", period_from=date(2026, 8, 1), period_to=date(2026, 8, 31)
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    assert "No worklogs booked in this period" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_renders_warnings(mock_service_cls: Mock) -> None:
    """Warnings from the report are shown under the table."""
    report = _billing_report()
    report.warnings = ["K-9: no planning key in its summary; counted as uncategorised"]
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    assert "Warning:" in result.stdout
    assert "K-9" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_group_category_rendering(mock_service_cls: Mock) -> None:
    """A category-grouped report renders without the redundant Category column."""
    report = _billing_report()
    report.grouped_by = "category"
    report.groups[0].name = "analysis"
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--group", "category"])

    assert result.exit_code == 0
    assert "analysis" in result.stdout
    assert "EK-10" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_validate_truncated_warning(mock_service_cls: Mock) -> None:
    """A truncated label check prints a warning."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.validate_billing_labels.return_value = BillingValidation(
        profile="ek-to-k", issues_checked=1000, violations=[], truncated=True
    )
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--validate"])

    assert result.exit_code == 0
    assert "fetch limit" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_unexpected_error(mock_service_cls: Mock) -> None:
    """Unexpected failures surface with a generic error message."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.side_effect = RuntimeError("boom")
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 1
    assert "Unexpected error" in result.stdout


def _mixed_billing_report_with_rate() -> BillingReport:
    """Report with a chargeable and a non-chargeable bucket, rate set (#120)."""
    return BillingReport(
        profile="ek-to-k",
        period_from=date(2026, 8, 1),
        period_to=date(2026, 8, 31),
        rate=100.0,
        chargeable_buckets=["billable"],
        groups=[
            BillingGroup(
                name="billable",
                bucket="billable",
                lines=[
                    BillingLine(
                        issue="EK-10",
                        booking_issue="K-1",
                        category="analysis",
                        bucket="billable",
                        summary="Analysis work",
                        seconds=7200,
                        hours=2.0,
                        amount=200.0,
                    )
                ],
                total_seconds=7200,
                total_hours=2.0,
                total_amount=200.0,
            ),
            BillingGroup(
                name="non-billable",
                bucket="non-billable",
                lines=[
                    BillingLine(
                        issue="EK-11",
                        booking_issue="K-2",
                        category="warranty",
                        bucket="non-billable",
                        summary="Warranty fix",
                        seconds=3600,
                        hours=1.0,
                        amount=None,
                    )
                ],
                total_seconds=3600,
                total_hours=1.0,
                total_amount=None,
            ),
        ],
        totals=BillingTotals(seconds=10800, hours=3.0, amount=200.0),
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_total_not_duplicated(mock_service_cls: Mock) -> None:
    """#120 minor: the hour total is printed once, not in two formats."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    assert "Total: 2h" in result.stdout
    assert "(2.00h)" not in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_money_total_labeled_chargeable(mock_service_cls: Mock) -> None:
    """#120: the money total covers only chargeable buckets and says so."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _mixed_billing_report_with_rate()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    # Hours total spans both buckets, money total only the chargeable one
    assert "Total: 3h" in result.stdout
    assert "Chargeable: 200.00 EUR" in result.stdout
    # The non-chargeable group shows hours only — no 100.00 EUR group figure
    assert "non-billable — 1h" in result.stdout
    assert "non-billable — 1h (" not in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_bucket_filter_non_chargeable_has_no_amount(mock_service_cls: Mock) -> None:
    """Filtering to a non-chargeable bucket yields a hours-only total even with a rate."""
    import json

    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _mixed_billing_report_with_rate()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(
        app, ["-q", "--format", "json", "workflow", "billing", "--profile", "ek-to-k", "--bucket", "non-billable"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["totals"]["seconds"] == 3600
    assert payload["totals"]["amount"] is None


# Billing contributor scope tests (#122)


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_mine_flag(mock_service_cls: Mock) -> None:
    """--mine restricts the report to the current user's worklogs."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--mine"])

    assert result.exit_code == 0
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 8, 31), group_by="bucket", mine=True
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_mine_and_all_conflict(mock_service_cls: Mock) -> None:
    """--mine and --all are mutually exclusive."""
    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--mine", "--all"])

    assert result.exit_code == 1
    assert "cannot be used together" in result.stdout
    mock_service_cls.from_profile.assert_not_called()


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_mine_by_default_from_profile(mock_service_cls: Mock) -> None:
    """mine_by_default in the profile restricts without the flag."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = True
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 8, 31), group_by="bucket", mine=True
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_all_overrides_mine_by_default(mock_service_cls: Mock) -> None:
    """--all overrides a profile's mine_by_default for one report."""
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = True
    mock_service.get_billing_report.return_value = _billing_report()
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--all"])

    assert result.exit_code == 0
    mock_service.get_billing_report.assert_called_once_with(
        date(2026, 8, 1), date(2026, 8, 31), group_by="bucket", mine=False
    )


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_shows_contributor_count(mock_service_cls: Mock) -> None:
    """The header names the number of distinct bookers, so a second one is visible."""
    report = _billing_report()
    report.contributors = 2
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    assert "2 contributor(s)" in result.stdout
    assert "consider --mine" in result.stdout  # shared-project hint


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_mine_scope_note(mock_service_cls: Mock) -> None:
    """A --mine report says so in the header."""
    report = _billing_report()
    report.mine_only = True
    report.contributors = 1
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "workflow", "billing", "--profile", "ek-to-k", "--mine"])

    assert result.exit_code == 0
    assert "your worklogs only" in result.stdout


@patch("budjira.cli.workflow.WorkflowService")
def test_workflow_billing_json_has_contributors(mock_service_cls: Mock) -> None:
    """JSON output carries mine_only and contributors for agents/scripts."""
    import json

    report = _billing_report()
    report.contributors = 3
    mock_service = MagicMock()
    mock_service.profile.billing.mine_by_default = False
    mock_service.get_billing_report.return_value = report
    mock_service_cls.from_profile.return_value = mock_service

    result = runner.invoke(app, ["-q", "--format", "json", "workflow", "billing", "--profile", "ek-to-k"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["contributors"] == 3
    assert payload["mine_only"] is False
