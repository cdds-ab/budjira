"""Tests for WorkflowService."""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.models.billing import UNCATEGORISED_BUCKET
from budjira.models.workflow import (
    BillingConfig,
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)
from budjira.services.workflow import WorkflowService, _format_seconds
from budjira.utils.errors import (
    BillingValidationError,
    JiraAPIError,
    OverbookingError,
    ShadowTicketAmbiguousError,
    ShadowTicketNotFoundError,
    ValidationError,
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


class TestGetBookingIssueId:
    """Test _get_booking_issue_id helper."""

    def test_resolves_issue_id(self) -> None:
        booking_jira = MagicMock()
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue

        service = _make_service(booking_jira=booking_jira)
        result = service._get_booking_issue_id("K-456")

        assert result == 67890
        booking_jira.client.issue.assert_called_once_with("K-456")

    def test_warns_on_key_mismatch(self, caplog: pytest.LogCaptureFixture) -> None:
        booking_jira = MagicMock()
        booking_jira.connection.url = "https://booking.atlassian.net"
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        shadow_jira_issue.key = "K-999"  # Different from what we asked
        booking_jira.client.issue.return_value = shadow_jira_issue

        service = _make_service(booking_jira=booking_jira)
        import logging

        with caplog.at_level(logging.WARNING):
            result = service._get_booking_issue_id("K-456")

        assert result == 67890
        assert "Requested K-456 but got K-999" in caplog.text

    def test_logs_connection_url(self, caplog: pytest.LogCaptureFixture) -> None:
        booking_jira = MagicMock()
        booking_jira.connection.url = "https://booking.atlassian.net"
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue

        service = _make_service(booking_jira=booking_jira)
        import logging

        with caplog.at_level(logging.DEBUG):
            service._get_booking_issue_id("K-456")

        assert "https://booking.atlassian.net" in caplog.text


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

    def test_tempo_api_error_returns_zero_spent(self) -> None:
        """Tempo API 400 on worklog query should not crash (regression #69)."""
        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 28800
        planning_issue.summary = "Task with Tempo error"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue

        tempo_client = MagicMock()
        tempo_client.get_worklogs.side_effect = JiraAPIError("Tempo API error: 400 Bad Request")

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        status = service.get_booking_status("EK-123")

        assert status.spent_seconds == 0
        assert status.booking_issue_key == "K-456"
        assert status.estimate_seconds == 28800

    def test_tempo_api_error_logs_connection_url(self, caplog: pytest.LogCaptureFixture) -> None:
        """Tempo API error warning should include connection URL (#72)."""
        import logging

        planning_jira = MagicMock()
        planning_issue = MagicMock()
        planning_issue.time_original_estimate = 28800
        planning_issue.summary = "Task"
        planning_jira.get_issue.return_value = planning_issue

        booking_jira = MagicMock()
        booking_jira.connection.url = "https://booking.atlassian.net"
        shadow_result = MagicMock()
        shadow_result.key = "K-456"
        booking_jira.search_issues.return_value = [shadow_result]
        shadow_jira_issue = MagicMock()
        shadow_jira_issue.id = "67890"
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue

        tempo_client = MagicMock()
        tempo_client.get_worklogs.side_effect = JiraAPIError("400 Bad Request")

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        with caplog.at_level(logging.WARNING):
            service.get_booking_status("EK-123")

        assert "https://booking.atlassian.net" in caplog.text
        assert "400 Bad Request" in caplog.text

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


class TestGetSprintBookingOverview:
    """Test get_sprint_booking_overview."""

    def test_basic_overview(self) -> None:
        planning_jira = MagicMock()
        booking_jira = MagicMock()
        tempo_client = MagicMock()

        # Planning issues in sprint
        issue1 = MagicMock()
        issue1.key = "EK-1"
        issue1.summary = "Task 1"
        issue1.time_original_estimate = 7200
        issue2 = MagicMock()
        issue2.key = "EK-2"
        issue2.summary = "Task 2"
        issue2.time_original_estimate = 3600

        planning_jira.sprints.get_sprint_issues.return_value = [issue1, issue2]

        # Planning issue details for get_booking_status
        planning_jira.get_issue.side_effect = [issue1, issue2]

        # Shadow ticket resolution
        shadow1 = MagicMock()
        shadow1.key = "K-10"
        shadow2 = MagicMock()
        shadow2.key = "K-20"
        booking_jira.search_issues.side_effect = [[shadow1], [shadow2]]

        shadow_jira1 = MagicMock()
        shadow_jira1.id = "100"
        shadow_jira2 = MagicMock()
        shadow_jira2.id = "200"
        booking_jira.client.issue.side_effect = [shadow_jira1, shadow_jira2]

        worklog = MagicMock()
        worklog.timeSpentSeconds = 3600
        tempo_client.get_worklogs.return_value = [worklog]

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        statuses = service.get_sprint_booking_overview(sprint_id=100)

        assert len(statuses) == 2
        assert statuses[0].planning_issue_key == "EK-1"
        assert statuses[1].planning_issue_key == "EK-2"

    def test_overview_with_mine_filter(self) -> None:
        planning_jira = MagicMock()
        planning_jira.sprints.get_sprint_issues.return_value = []

        service = _make_service(planning_jira=planning_jira)
        statuses = service.get_sprint_booking_overview(sprint_id=100, mine_only=True)

        assert statuses == []
        planning_jira.sprints.get_sprint_issues.assert_called_once_with(100, jql_filter="assignee = currentUser()")

    def test_overview_handles_shadow_errors_gracefully(self) -> None:
        planning_jira = MagicMock()
        issue1 = MagicMock()
        issue1.key = "EK-1"
        issue1.summary = "Failing task"
        issue1.time_original_estimate = 7200
        planning_jira.sprints.get_sprint_issues.return_value = [issue1]
        planning_jira.get_issue.side_effect = Exception("API error")

        service = _make_service(planning_jira=planning_jira)
        statuses = service.get_sprint_booking_overview(sprint_id=100)

        assert len(statuses) == 1
        assert statuses[0].planning_issue_key == "EK-1"
        assert statuses[0].booking_issue_key is None


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
        shadow_jira_issue.key = "K-456"
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
        shadow_jira_issue.key = "K-456"
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

    def test_booking_warns_on_id_mismatch_after_create(self, caplog: pytest.LogCaptureFixture) -> None:
        """Tempo-returned issue ID should be validated against what we sent (#72)."""
        import logging

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
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue
        booking_jira.client.myself.return_value = {"accountId": "abc123"}

        tempo_client = MagicMock()
        tempo_client.get_worklogs.return_value = []
        mock_worklog = MagicMock()
        mock_worklog.tempoWorklogId = 12345
        mock_worklog.issue.id = 99999  # Different from what we sent (67890)
        tempo_client.create_worklog.return_value = mock_worklog

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        with caplog.at_level(logging.WARNING):
            service.book_time("EK-123", "2h")

        assert "Tempo stored issue ID 99999 but we sent 67890" in caplog.text

    def test_booking_succeeds_on_tempo_worklog_query_error(self) -> None:
        """Tempo API 400 on overbooking check should not block booking (regression #69)."""
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
        shadow_jira_issue.key = "K-456"
        booking_jira.client.issue.return_value = shadow_jira_issue
        booking_jira.client.myself.return_value = {"accountId": "abc123"}

        tempo_client = MagicMock()
        tempo_client.get_worklogs.side_effect = JiraAPIError("Tempo API error: 400 Bad Request")
        mock_worklog = MagicMock()
        mock_worklog.tempoWorklogId = 555
        mock_worklog.issue.id = 67890
        tempo_client.create_worklog.return_value = mock_worklog

        service = _make_service(
            planning_jira=planning_jira,
            booking_jira=booking_jira,
            tempo_client=tempo_client,
        )
        result = service.book_time("EK-123", "1h")

        assert result.tempoWorklogId == 555
        tempo_client.create_worklog.assert_called_once()


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


# --- Billing report tests (#117) ---

_BILLING = BillingConfig(
    categories={
        "analysis": "billable",
        "support": "billable",
        "warranty": "non-billable",
        "onboarding": "project",
    }
)


def _make_billing_profile(
    billing: BillingConfig | None = _BILLING,
    strategy: ShadowTicketStrategy = ShadowTicketStrategy.SUMMARY_SEARCH,
) -> WorkflowProfile:
    """Profile with a billing block for report tests."""
    profile = _make_profile()
    profile.billing = billing
    profile.shadow_strategy = strategy
    return profile


def _wl(issue_id: int, seconds: int, issue_key: str | None = None, author: str = "user-1") -> MagicMock:
    """Mock a Tempo worklog (only the fields the billing join reads)."""
    worklog = MagicMock()
    worklog.issue.id = issue_id
    worklog.issue.key = issue_key
    worklog.timeSpentSeconds = seconds
    worklog.author.accountId = author
    return worklog


def _issue(key: str, summary: str, labels: list[str] | None = None) -> MagicMock:
    """Mock an Issue (key, summary, labels)."""
    issue = MagicMock()
    issue.key = key
    issue.summary = summary
    issue.labels = labels or []
    return issue


def _make_billing_service(
    *,
    worklogs: list[MagicMock] | None = None,
    booking_issues: list[MagicMock] | None = None,
    planning_issues: list[MagicMock] | None = None,
    profile: WorkflowProfile | None = None,
) -> tuple[WorkflowService, MagicMock, MagicMock, MagicMock]:
    """Wire a WorkflowService with mocked Tempo/Jira for billing tests."""
    tempo = MagicMock()
    tempo.get_worklogs.return_value = worklogs or []
    booking = MagicMock()
    booking.search_issues.return_value = booking_issues or []
    planning = MagicMock()
    planning.search_issues.return_value = planning_issues or []
    service = _make_service(
        profile=profile or _make_billing_profile(),
        planning_jira=planning,
        booking_jira=booking,
        tempo_client=tempo,
    )
    return service, tempo, booking, planning


class TestBillingReport:
    """Test WorkflowService.get_billing_report."""

    def test_groups_by_bucket_and_excludes_project_from_total(self) -> None:
        """Lines land in their configured buckets; the 'project' bucket stays out of the grand total."""
        service, tempo, _, _ = _make_billing_service(
            worklogs=[
                _wl(100, 7200, "K-1"),
                _wl(101, 3600, "K-2"),
                _wl(102, 1800, "K-3"),
            ],
            booking_issues=[
                _issue("K-1", "EK-10 Analysis work"),
                _issue("K-2", "EK-11 Warranty fix"),
                _issue("K-3", "EK-12 Onboarding"),
            ],
            planning_issues=[
                _issue("EK-10", "Analysis work", ["analysis"]),
                _issue("EK-11", "Warranty fix", ["warranty"]),
                _issue("EK-12", "Onboarding", ["onboarding"]),
            ],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert [group.name for group in report.groups] == ["billable", "non-billable", "project"]
        assert report.groups[0].total_seconds == 7200
        assert report.groups[0].lines[0].issue == "EK-10"
        assert report.groups[0].lines[0].category == "analysis"
        assert report.groups[0].lines[0].booking_issue == "K-1"
        # Grand total excludes the 'project' bucket (1800s onboarding)
        assert report.totals.seconds == 10800
        assert report.excluded_from_total == ["project"]
        assert report.warnings == []
        # Tempo was queried for the period (project scope is filtered client-side)
        tempo.get_worklogs.assert_called_once_with(
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 31),
            account_id=None,
            limit=1000,
            offset=0,
        )

    def test_foreign_project_worklogs_are_excluded(self) -> None:
        """Worklogs on issues outside the profile's booking projects never enter the report (#118)."""
        service, _, booking, _planning = _make_billing_service(
            worklogs=[
                _wl(100, 7200, "K-1"),
                _wl(200, 999999, "OTHER-9"),  # shared Tempo instance, unrelated project
            ],
            booking_issues=[_issue("K-1", "EK-10 Analysis work")],
            planning_issues=[_issue("EK-10", "Analysis work", ["analysis"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.totals.seconds == 7200
        all_issues = [line.issue for group in report.groups for line in group.lines]
        assert "OTHER-9" not in all_issues
        # The foreign issue is filtered before any Jira lookup happens for it
        assert booking.search_issues.call_args.args[0] == "key in (K-1)"

    def test_unlabelled_issue_lands_in_uncategorised(self) -> None:
        """An issue without a category label is visible in the uncategorised bucket."""
        service, _, _, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Undocumented work")],
            planning_issues=[_issue("EK-10", "Undocumented work", [])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert [group.name for group in report.groups] == [UNCATEGORISED_BUCKET]
        assert report.groups[0].lines[0].category is None
        assert report.totals.seconds == 3600

    def test_unresolvable_shadow_is_uncategorised_with_warning(self) -> None:
        """A booking issue whose summary carries no planning key is not silently dropped."""
        service, _, _, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "Manually created ticket")],
            planning_issues=[],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert [group.name for group in report.groups] == [UNCATEGORISED_BUCKET]
        assert report.groups[0].lines[0].issue == "K-1"
        assert any("K-1" in warning for warning in report.warnings)

    def test_multiple_category_labels_fail_loudly(self) -> None:
        """require_exactly_one=true aborts the report, naming the offending labels."""
        service, _, _, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Ambiguous")],
            planning_issues=[_issue("EK-10", "Ambiguous", ["analysis", "support"])],
        )

        with pytest.raises(BillingValidationError, match="EK-10"):
            service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

    def test_multiple_category_labels_lenient_mode(self) -> None:
        """require_exactly_one=false picks the alphabetically first label and warns."""
        billing = _BILLING.model_copy(update={"require_exactly_one": False})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Ambiguous")],
            planning_issues=[_issue("EK-10", "Ambiguous", ["support", "analysis"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.groups[0].lines[0].category == "analysis"
        assert report.groups[0].bucket == "billable"
        assert any("multiple category labels" in warning for warning in report.warnings)

    def test_rate_adds_amounts(self) -> None:
        """A configured rate yields amounts on lines, groups and totals."""
        billing = _BILLING.model_copy(update={"rate": 100.0})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 7200, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.groups[0].lines[0].amount == 200.0
        assert report.groups[0].total_amount == 200.0
        assert report.totals.amount == 200.0
        assert report.currency == "EUR"

    def test_rate_zero_means_hours_only(self) -> None:
        """rate = 0 is treated like an absent rate: no amounts anywhere."""
        billing = _BILLING.model_copy(update={"rate": 0.0})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 7200, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.rate is None
        assert report.groups[0].lines[0].amount is None
        assert report.totals.amount is None

    def test_money_never_spans_billing_semantics(self) -> None:
        """#120: amounts and the money total cover only chargeable buckets.

        A combined figure over billable + non-billable would look like an
        invoice total without being one.
        """
        billing = _BILLING.model_copy(update={"rate": 100.0})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 7200, "K-1"), _wl(101, 3600, "K-2")],
            booking_issues=[_issue("K-1", "EK-10 Analysis"), _issue("K-2", "EK-11 Warranty fix")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"]), _issue("EK-11", "Warranty fix", ["warranty"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        billable = next(g for g in report.groups if g.name == "billable")
        non_billable = next(g for g in report.groups if g.name == "non-billable")
        assert billable.lines[0].amount == 200.0
        assert billable.total_amount == 200.0
        # Non-chargeable bucket: hours only, no line/group amounts
        assert non_billable.lines[0].amount is None
        assert non_billable.total_amount is None
        # Hours total spans both, money total only the chargeable one
        assert report.totals.seconds == 10800
        assert report.totals.amount == 200.0
        assert report.chargeable_buckets == ["billable"]

    def test_chargeable_buckets_are_configurable(self) -> None:
        """Contracts with different vocabulary name their chargeable bucket(s) in the config."""
        billing = _BILLING.model_copy(update={"rate": 100.0, "chargeable_buckets": ["non-billable"]})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 7200, "K-1"), _wl(101, 3600, "K-2")],
            booking_issues=[_issue("K-1", "EK-10 Analysis"), _issue("K-2", "EK-11 Warranty fix")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"]), _issue("EK-11", "Warranty fix", ["warranty"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert next(g for g in report.groups if g.name == "billable").total_amount is None
        assert next(g for g in report.groups if g.name == "non-billable").total_amount == 100.0
        assert report.totals.amount == 100.0

    def test_paginates_full_tempo_pages(self) -> None:
        """A full page of worklogs triggers a second request with an offset."""
        full_page = [_wl(100, 36, "K-1") for _ in range(1000)]
        service, tempo, _, _ = _make_billing_service(
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )
        tempo.get_worklogs.side_effect = [
            full_page,
            [_wl(100, 3600, "K-1")],
        ]

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert tempo.get_worklogs.call_count == 2
        assert tempo.get_worklogs.call_args_list[1].kwargs["offset"] == 1000
        assert report.totals.seconds == 1000 * 36 + 3600

    def test_empty_period_yields_empty_report(self) -> None:
        """No worklogs in the period => no groups, zero totals, no warnings."""
        service, _, _, _ = _make_billing_service(worklogs=[])

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.groups == []
        assert report.totals.seconds == 0
        assert report.warnings == []

    def test_requires_billing_block(self) -> None:
        """A profile without a billing block fails with a configuration hint."""
        service, _, _, _ = _make_billing_service(profile=_make_billing_profile(billing=None))

        with pytest.raises(WorkflowConfigError, match="no billing configuration"):
            service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

    def test_requires_summary_strategy(self) -> None:
        """Shadow strategies other than 'summary' are refused explicitly."""
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(strategy=ShadowTicketStrategy.CUSTOM_FIELD)
        )

        with pytest.raises(WorkflowConfigError, match="shadow_strategy"):
            service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

    def test_group_by_category(self) -> None:
        """--group category groups lines by their category label."""
        service, _, _, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, "K-1"), _wl(101, 3600, "K-2")],
            booking_issues=[_issue("K-1", "EK-10 A"), _issue("K-2", "EK-11 B")],
            planning_issues=[_issue("EK-10", "A", ["analysis"]), _issue("EK-11", "B", ["support"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31), group_by="category")

        assert report.grouped_by == "category"
        assert [group.name for group in report.groups] == ["analysis", "support"]
        assert all(group.bucket == "billable" for group in report.groups)

    def test_invalid_group_by(self) -> None:
        """An unknown grouping is rejected."""
        service, _, _, _ = _make_billing_service()

        with pytest.raises(ValidationError, match="Invalid group_by"):
            service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31), group_by="project")

    def test_tempo_key_backfill(self) -> None:
        """Worklogs without an issue key are resolved via the booking instance."""
        service, _, booking, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, None)],
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )
        booking.client.issue.return_value = MagicMock(key="K-1")

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        booking.client.issue.assert_called_once_with("100")
        assert report.groups[0].lines[0].booking_issue == "K-1"

    def test_worklog_without_issue_id_is_skipped(self) -> None:
        """A Tempo worklog without an issue reference contributes nothing."""
        worklog = MagicMock()
        worklog.issue.id = None
        worklog.issue.key = None
        service, _, _, _ = _make_billing_service(worklogs=[worklog])

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.groups == []


class TestValidateBillingLabels:
    """Test WorkflowService.validate_billing_labels."""

    def test_finds_missing_and_multiple(self) -> None:
        """Issues with zero or multiple category labels are reported."""
        service, _, _, planning = _make_billing_service(
            planning_issues=[
                _issue("EK-10", "Fine", ["analysis"]),
                _issue("EK-11", "No label", []),
                _issue("EK-12", "Two labels", ["analysis", "support"]),
            ],
        )

        validation = service.validate_billing_labels()

        planning.search_issues.assert_called_once_with("project = EK", max_results=1000)
        assert validation.issues_checked == 3
        assert [(v.issue, v.kind) for v in validation.violations] == [("EK-11", "missing"), ("EK-12", "multiple")]
        assert validation.violations[1].labels == ["analysis", "support"]

    def test_clean_project_has_no_violations(self) -> None:
        """A fully labelled project validates clean."""
        service, _, _, _ = _make_billing_service(
            planning_issues=[_issue("EK-10", "Fine", ["analysis"])],
        )

        validation = service.validate_billing_labels()

        assert validation.violations == []
        assert validation.issues_checked == 1

    def test_truncation_flag(self) -> None:
        """A project at the fetch limit marks the validation as truncated."""
        service, _, _, _ = _make_billing_service(
            planning_issues=[_issue(f"EK-{i}", f"Issue {i}", ["analysis"]) for i in range(1000)],
        )

        validation = service.validate_billing_labels()

        assert validation.truncated is True

    def test_requires_billing_block(self) -> None:
        """Validation needs the category labels from the billing block."""
        service, _, _, _ = _make_billing_service(profile=_make_billing_profile(billing=None))

        with pytest.raises(WorkflowConfigError, match="no billing configuration"):
            service.validate_billing_labels()


class TestBillingIssueCategories:
    """Test the issue_categories path: collective tickets as their own category (#121)."""

    def _service_with_issue_categories(self, **kwargs) -> tuple[WorkflowService, MagicMock, MagicMock, MagicMock]:
        billing = _BILLING.model_copy(update={"issue_categories": {"ACME-101": "billable", "ACME-102": "non-billable"}})
        return _make_billing_service(profile=_make_billing_profile(billing=billing), **kwargs)

    def test_collective_ticket_outside_mapped_project_is_in_scope(self) -> None:
        """A named issue is in scope regardless of project mapping — that is the point."""
        service, _, _booking, _planning = self._service_with_issue_categories(
            worklogs=[_wl(100, 7200, "K-1"), _wl(200, 10800, "ACME-101")],
            booking_issues=[_issue("K-1", "EK-10 Analysis"), _issue("ACME-101", "ACME DEV collective ticket")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.totals.seconds == 18000
        lines = {line.booking_issue: line for group in report.groups for line in group.lines}
        assert lines["ACME-101"].bucket == "billable"
        assert lines["ACME-101"].category == "ACME-101"  # the ticket itself is the category
        assert lines["ACME-101"].summary == "ACME DEV collective ticket"

    def test_issue_mapping_wins_over_labels(self) -> None:
        """Where both paths would apply, the more specific issue statement wins."""
        billing = _BILLING.model_copy(update={"issue_categories": {"K-1": "billable"}})
        service, _, _, _ = _make_billing_service(
            profile=_make_billing_profile(billing=billing),
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["warranty"])],  # label would say non-billable
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        line = report.groups[0].lines[0]
        assert line.bucket == "billable"  # issue mapping beats the warranty label
        assert line.category == "K-1"

    def test_issue_path_is_not_subject_to_require_exactly_one(self) -> None:
        """The issue path is unambiguous by construction — no multi-label failure."""
        service, _, _, _ = self._service_with_issue_categories(
            worklogs=[_wl(100, 3600, "ACME-102")],
            booking_issues=[_issue("ACME-102", "EK-10 Both", ["analysis", "support"])],
            planning_issues=[_issue("EK-10", "Both", ["analysis", "support"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))  # must not raise

        assert report.groups[0].lines[0].bucket == "non-billable"

    def test_unmatched_still_lands_in_uncategorised(self) -> None:
        """Neither issue-mapped nor labelled: the uncategorised net still catches it."""
        service, _, _, _ = self._service_with_issue_categories(
            worklogs=[_wl(100, 3600, "K-9")],
            booking_issues=[_issue("K-9", "EK-99 Unknown work")],
            planning_issues=[_issue("EK-99", "Unknown work", [])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert [group.name for group in report.groups] == [UNCATEGORISED_BUCKET]


class TestBillingContributorScope:
    """Test the --mine contributor scope and the contributor count (#122)."""

    def test_mine_filters_server_side_by_account(self) -> None:
        """mine=True resolves the current user and passes account_id to Tempo."""
        service, tempo, booking, _ = _make_billing_service(
            worklogs=[_wl(100, 3600, "K-1")],
            booking_issues=[_issue("K-1", "EK-10 Analysis")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"])],
        )
        booking.client.myself.return_value = {"accountId": "user-1", "displayName": "Me"}

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31), mine=True)

        tempo.get_worklogs.assert_called_once_with(
            from_date=date(2026, 8, 1),
            to_date=date(2026, 8, 31),
            account_id="user-1",
            limit=1000,
            offset=0,
        )
        assert report.mine_only is True
        assert report.contributors == 1

    def test_contributors_counted_across_bookers(self) -> None:
        """Distinct bookers in scope are counted — a second one is visible in the report."""
        service, _, _, _ = _make_billing_service(
            worklogs=[
                _wl(100, 3600, "K-1", author="user-1"),
                _wl(100, 3600, "K-1", author="user-1"),
                _wl(101, 3600, "K-2", author="user-2"),
            ],
            booking_issues=[_issue("K-1", "EK-10 Analysis"), _issue("K-2", "EK-11 Warranty")],
            planning_issues=[_issue("EK-10", "Analysis", ["analysis"]), _issue("EK-11", "Warranty", ["warranty"])],
        )

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.mine_only is False
        assert report.contributors == 2

    def test_empty_period_reports_zero_contributors(self) -> None:
        """An empty period has no contributors and is not mine-scoped by default."""
        service, _, _, _ = _make_billing_service(worklogs=[])

        report = service.get_billing_report(date(2026, 8, 1), date(2026, 8, 31))

        assert report.contributors == 0
        assert report.mine_only is False
