"""Tests for WorkflowService."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.models.workflow import (
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)
from budjira.services.workflow import WorkflowService, _format_seconds
from budjira.utils.errors import (
    OverbookingError,
    ShadowTicketAmbiguousError,
    ShadowTicketNotFoundError,
    WorkflowConfigError,
)


def _make_profile(
    overbooking_policy: OverbookingPolicy = OverbookingPolicy.WARN,
) -> WorkflowProfile:
    return WorkflowProfile(
        name="test-profile",
        planning_connection="ek-planning",
        booking_connection="k-booking",
        project_mappings=[
            ProjectMapping(planning_project="EK", booking_project="K"),
        ],
        shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH,
        overbooking_policy=overbooking_policy,
    )


def _make_service(
    profile: WorkflowProfile | None = None,
    planning_jira: MagicMock | None = None,
    booking_jira: MagicMock | None = None,
    tempo_client: MagicMock | None = None,
) -> WorkflowService:
    return WorkflowService(
        profile=profile or _make_profile(),
        planning_jira=planning_jira or MagicMock(),
        booking_jira=booking_jira or MagicMock(),
        tempo_client=tempo_client or MagicMock(),
    )


class TestFormatSeconds:
    """Test _format_seconds helper."""

    def test_hours_and_minutes(self) -> None:
        assert _format_seconds(5400) == "1h 30m"

    def test_hours_only(self) -> None:
        assert _format_seconds(7200) == "2h"

    def test_minutes_only(self) -> None:
        assert _format_seconds(1800) == "30m"

    def test_zero(self) -> None:
        assert _format_seconds(0) == "0m"


class TestGetBookingProject:
    """Test _get_booking_project."""

    def test_mapping_found(self) -> None:
        service = _make_service()
        assert service._get_booking_project("EK") == "K"

    def test_mapping_not_found(self) -> None:
        service = _make_service()
        with pytest.raises(WorkflowConfigError, match="No project mapping"):
            service._get_booking_project("UNKNOWN")


class TestResolveShadowTicket:
    """Test shadow ticket resolution."""

    def test_single_match(self) -> None:
        booking_jira = MagicMock()
        mock_issue = MagicMock()
        mock_issue.key = "K-456"
        booking_jira.search_issues.return_value = [mock_issue]

        service = _make_service(booking_jira=booking_jira)
        result = service.resolve_shadow_ticket("EK-123")

        assert result == "K-456"
        booking_jira.search_issues.assert_called_once_with('project = K AND summary ~ "EK-123"', max_results=10)

    def test_no_match(self) -> None:
        booking_jira = MagicMock()
        booking_jira.search_issues.return_value = []

        service = _make_service(booking_jira=booking_jira)
        with pytest.raises(ShadowTicketNotFoundError, match="Shadow ticket not found"):
            service.resolve_shadow_ticket("EK-999")

    def test_multiple_matches(self) -> None:
        booking_jira = MagicMock()
        issue1 = MagicMock()
        issue1.key = "K-100"
        issue2 = MagicMock()
        issue2.key = "K-200"
        booking_jira.search_issues.return_value = [issue1, issue2]

        service = _make_service(booking_jira=booking_jira)
        with pytest.raises(ShadowTicketAmbiguousError, match="Multiple shadow tickets"):
            service.resolve_shadow_ticket("EK-123")

    def test_invalid_issue_key_format(self) -> None:
        service = _make_service()
        with pytest.raises(ShadowTicketNotFoundError, match="Invalid issue key"):
            service.resolve_shadow_ticket("INVALID")

    def test_unmapped_project(self) -> None:
        service = _make_service()
        with pytest.raises(WorkflowConfigError, match="No project mapping"):
            service.resolve_shadow_ticket("UNKNOWN-123")


class TestGetBookingStatus:
    """Test get_booking_status."""

    def test_with_shadow_and_estimate(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 28800  # 8h
        planning_issue.summary = "Fix login bug"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_issue = MagicMock()
        shadow_issue.key = "K-456"
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        booking_jira.client.issue.return_value = shadow_jira_issue

        tempo_client = MagicMock()
        worklog1 = MagicMock()
        worklog1.timeSpentSeconds = 10800  # 3h
        worklog2 = MagicMock()
        worklog2.timeSpentSeconds = 9000  # 2.5h
        tempo_client.get_worklogs.return_value = [worklog1, worklog2]

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        status = service.get_booking_status("EK-123")

        assert status.planning_issue_key == "EK-123"
        assert status.planning_summary == "Fix login bug"
        assert status.booking_issue_key == "K-456"
        assert status.estimate_seconds == 28800
        assert status.spent_seconds == 19800  # 3h + 2.5h
        assert status.remaining_seconds == 9000  # 8h - 5.5h
        assert status.is_overbooked is False

    def test_shadow_not_found_returns_partial_status(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 28800
        planning_issue.summary = "New task"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        booking_jira.search_issues.return_value = []

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
        )
        status = service.get_booking_status("EK-123")

        assert status.booking_issue_key is None
        assert status.spent_seconds == 0
        assert status.estimate_seconds == 28800
        assert status.is_overbooked is False

    def test_overbooked_status(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 7200  # 2h
        planning_issue.summary = "Quick fix"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        booking_jira.client.issue.return_value = shadow_jira_issue

        tempo_client = MagicMock()
        worklog = MagicMock()
        worklog.timeSpentSeconds = 10800  # 3h > 2h estimate
        tempo_client.get_worklogs.return_value = [worklog]

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        status = service.get_booking_status("EK-123")

        assert status.is_overbooked is True
        assert status.overbooking_seconds == 3600  # 1h over
        assert status.remaining_seconds == 0

    def test_no_estimate(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = None
        planning_issue.summary = "Unestimated"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        booking_jira.client.issue.return_value = shadow_jira_issue

        tempo_client = MagicMock()
        tempo_client.get_worklogs.return_value = []

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        status = service.get_booking_status("EK-123")

        assert status.estimate_seconds is None
        assert status.remaining_seconds is None
        assert status.is_overbooked is False


class TestCheckOverbooking:
    """Test _check_overbooking."""

    def test_no_estimate_skips_check(self) -> None:
        service = _make_service()
        # Should not raise
        service._check_overbooking(None, 0, 3600, "EK-123")

    def test_within_estimate_no_action(self) -> None:
        service = _make_service()
        # Should not raise (7200 + 3600 = 10800 < 28800)
        service._check_overbooking(28800, 7200, 3600, "EK-123")

    def test_warn_policy_prints_warning(self) -> None:
        profile = _make_profile(OverbookingPolicy.WARN)
        service = _make_service(profile=profile)
        # Should not raise even when overbooked
        service._check_overbooking(7200, 7200, 3600, "EK-123")

    def test_block_policy_raises(self) -> None:
        profile = _make_profile(OverbookingPolicy.BLOCK)
        service = _make_service(profile=profile)
        with pytest.raises(OverbookingError, match="Booking blocked"):
            service._check_overbooking(7200, 7200, 3600, "EK-123")

    @patch("budjira.services.workflow.typer.confirm", return_value=False)
    def test_confirm_policy_cancelled(self, mock_confirm: Mock) -> None:
        profile = _make_profile(OverbookingPolicy.CONFIRM)
        service = _make_service(profile=profile)
        with pytest.raises(OverbookingError, match="cancelled by user"):
            service._check_overbooking(7200, 7200, 3600, "EK-123")

    @patch("budjira.services.workflow.typer.confirm", return_value=True)
    def test_confirm_policy_accepted(self, mock_confirm: Mock) -> None:
        profile = _make_profile(OverbookingPolicy.CONFIRM)
        service = _make_service(profile=profile)
        # Should not raise when user confirms
        service._check_overbooking(7200, 7200, 3600, "EK-123")


class TestBookTime:
    """Test book_time."""

    def test_successful_booking(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 28800
        planning_issue.summary = "Fix bug"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        booking_jira.client.issue.return_value = shadow_jira_issue
        booking_jira.client.myself.return_value = {"accountId": "abc123"}

        tempo_client = MagicMock()
        tempo_client.get_worklogs.return_value = []
        mock_worklog = MagicMock()
        mock_worklog.tempoWorklogId = 12345
        tempo_client.create_worklog.return_value = mock_worklog

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        result = service.book_time("EK-123", "2h")

        assert result.tempoWorklogId == 12345
        tempo_client.create_worklog.assert_called_once()
        call_kwargs = tempo_client.create_worklog.call_args[1]
        assert call_kwargs["issue_id"] == 67890
        assert call_kwargs["time_spent_seconds"] == 7200
        assert call_kwargs["author_account_id"] == "abc123"

    def test_booking_with_comment_and_started(self) -> None:
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = None  # No estimate
        planning_issue.summary = "Task"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        booking_jira.client.issue.return_value = shadow_jira_issue
        booking_jira.client.myself.return_value = {"accountId": "abc123"}

        tempo_client = MagicMock()
        tempo_client.get_worklogs.return_value = []
        mock_worklog = MagicMock()
        mock_worklog.tempoWorklogId = 99
        tempo_client.create_worklog.return_value = mock_worklog

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        result = service.book_time("EK-123", "30m", comment="Analysis", started="2026-01-15 09:00")

        assert result.tempoWorklogId == 99
        call_kwargs = tempo_client.create_worklog.call_args[1]
        assert call_kwargs["description"] == "Analysis"
        assert call_kwargs["start_date"] == "2026-01-15"
        assert call_kwargs["start_time"] == "09:00:00"

    def test_booking_shadow_not_found(self) -> None:
        booking_jira = MagicMock()
        booking_jira.search_issues.return_value = []

        service = _make_service(booking_jira=booking_jira)
        with pytest.raises(ShadowTicketNotFoundError):
            service.book_time("EK-999", "1h")


class TestFromProfile:
    """Test WorkflowService.from_profile factory."""

    @patch("budjira.services.workflow.TempoClient")
    @patch("budjira.services.workflow.CredentialStore")
    @patch("budjira.services.workflow.JiraClient")
    @patch("budjira.services.workflow.get_active_connection")
    @patch("budjira.services.workflow.get_settings")
    def test_from_profile_success(
        self,
        mock_get_settings: Mock,
        mock_get_conn: Mock,
        mock_jira_cls: Mock,
        mock_cred_store_cls: Mock,
        mock_tempo_cls: Mock,
    ) -> None:
        # Setup profile
        profile = _make_profile()
        mock_settings = MagicMock()
        mock_settings.workflows = WorkflowProfileList(profiles=[profile])
        mock_get_settings.return_value = mock_settings

        # Setup connections
        planning_conn = MagicMock()
        planning_conn.name = "ek-planning"
        booking_conn = MagicMock()
        booking_conn.name = "k-booking"
        booking_conn.tempo_enabled = True
        booking_conn.get_tempo_credential_key.return_value = "tempo_key"

        mock_get_conn.side_effect = [planning_conn, booking_conn]
        mock_jira_cls.from_connection.side_effect = [MagicMock(), MagicMock()]

        # Setup Tempo
        mock_cred_store = MagicMock()
        mock_cred_store.get_credential.return_value = "tempo-token"
        mock_cred_store_cls.return_value = mock_cred_store

        service = WorkflowService.from_profile("test-profile")
        assert service.profile == profile
        assert mock_jira_cls.from_connection.call_count == 2
        mock_tempo_cls.assert_called_once_with(tempo_token="tempo-token")

    @patch("budjira.services.workflow.get_settings")
    def test_from_profile_not_found(self, mock_get_settings: Mock) -> None:
        mock_settings = MagicMock()
        mock_settings.workflows = WorkflowProfileList()
        mock_get_settings.return_value = mock_settings

        with pytest.raises(WorkflowConfigError, match="not found"):
            WorkflowService.from_profile("nonexistent")

    @patch("budjira.services.workflow.JiraClient")
    @patch("budjira.services.workflow.get_active_connection")
    @patch("budjira.services.workflow.get_settings")
    def test_from_profile_booking_no_tempo(
        self,
        mock_get_settings: Mock,
        mock_get_conn: Mock,
        mock_jira_cls: Mock,
    ) -> None:
        from budjira.utils.errors import ConnectionError

        profile = _make_profile()
        mock_settings = MagicMock()
        mock_settings.workflows = WorkflowProfileList(profiles=[profile])
        mock_get_settings.return_value = mock_settings

        planning_conn = MagicMock()
        booking_conn = MagicMock()
        booking_conn.name = "k-booking"
        booking_conn.tempo_enabled = False

        mock_get_conn.side_effect = [planning_conn, booking_conn]
        mock_jira_cls.from_connection.return_value = MagicMock()

        with pytest.raises(ConnectionError, match="Tempo is not enabled"):
            WorkflowService.from_profile("test-profile")
