"""Tests for EpicService."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from budjira.models.issue import Issue
from budjira.services.epics import EpicService


@pytest.fixture
def mock_jira_client() -> MagicMock:
    """Create a mock JIRA client."""
    return MagicMock()


@pytest.fixture
def sample_issues() -> list[Issue]:
    """Create sample Issue objects for testing."""
    return [
        Issue(
            key="TEST-1",
            summary="Issue 1",
            description="Desc 1",
            issue_type="Story",
            status="To Do",
            priority="Medium",
            assignee="user1",
            reporter="reporter1",
            created=datetime(2025, 1, 1),
            updated=datetime(2025, 1, 1),
            project_key="TEST",
        ),
        Issue(
            key="TEST-2",
            summary="Issue 2",
            description="Desc 2",
            issue_type="Story",
            status="In Progress",
            priority="High",
            assignee="user2",
            reporter="reporter2",
            created=datetime(2025, 1, 2),
            updated=datetime(2025, 1, 2),
            project_key="TEST",
        ),
        Issue(
            key="TEST-3",
            summary="Issue 3",
            description="Desc 3",
            issue_type="Bug",
            status="Done",
            priority="Low",
            assignee="user3",
            reporter="reporter3",
            created=datetime(2025, 1, 3),
            updated=datetime(2025, 1, 3),
            project_key="TEST",
        ),
    ]


class TestEpicServiceGetEpicIssues:
    """Tests for EpicService.get_epic_issues method."""

    @patch("budjira.services.issues.IssueService")
    def test_modern_only(
        self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock, sample_issues: list[Issue]
    ) -> None:
        """Test finding issues via parent field only."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [
            sample_issues[:2],  # Modern query returns 2 issues
            [],  # Legacy query returns none
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        assert len(result) == 2
        assert {i.key for i in result} == {"TEST-1", "TEST-2"}
        assert mock_issue_service.search.call_count == 2

    @patch("budjira.services.issues.IssueService")
    def test_legacy_only(
        self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock, sample_issues: list[Issue]
    ) -> None:
        """Test finding issues via Epic Link field only."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [
            [],  # Modern query returns none
            sample_issues[:2],  # Legacy query returns 2 issues
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        assert len(result) == 2
        assert {i.key for i in result} == {"TEST-1", "TEST-2"}

    @patch("budjira.services.issues.IssueService")
    def test_combined_results_deduplicated(
        self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock, sample_issues: list[Issue]
    ) -> None:
        """Test that issues from both queries are combined and deduplicated.

        This tests the fix for issue #62 where issues linked via different
        methods were not all being returned.
        """
        mock_issue_service = MagicMock()
        # Modern returns TEST-1 and TEST-2
        # Legacy returns TEST-2 (duplicate) and TEST-3 (new)
        mock_issue_service.search.side_effect = [
            sample_issues[:2],  # Modern: TEST-1, TEST-2
            [sample_issues[1], sample_issues[2]],  # Legacy: TEST-2 (dup), TEST-3
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        # Should have all 3 unique issues
        assert len(result) == 3
        assert {i.key for i in result} == {"TEST-1", "TEST-2", "TEST-3"}

    @patch("budjira.services.issues.IssueService")
    def test_no_issues_found(self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock) -> None:
        """Test when no issues are linked to the epic."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [[], []]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        assert len(result) == 0
        assert result == []

    @patch("budjira.services.issues.IssueService")
    def test_modern_query_fails_legacy_succeeds(
        self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock, sample_issues: list[Issue]
    ) -> None:
        """Test graceful handling when modern query fails but legacy succeeds."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [
            RuntimeError("Parent field not supported"),  # Modern fails
            sample_issues,  # Legacy succeeds
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        assert len(result) == 3
        assert {i.key for i in result} == {"TEST-1", "TEST-2", "TEST-3"}

    @patch("budjira.services.issues.IssueService")
    def test_modern_succeeds_legacy_query_fails(
        self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock, sample_issues: list[Issue]
    ) -> None:
        """Test graceful handling when legacy query fails but modern succeeds."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [
            sample_issues,  # Modern succeeds
            RuntimeError("Epic Link field not found"),  # Legacy fails
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        assert len(result) == 3
        assert {i.key for i in result} == {"TEST-1", "TEST-2", "TEST-3"}

    @patch("budjira.services.issues.IssueService")
    def test_both_queries_fail(self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock) -> None:
        """Test that empty list is returned when both queries fail gracefully."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.side_effect = [
            RuntimeError("Modern query failed"),
            RuntimeError("Legacy query failed"),
        ]
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        result = service.get_epic_issues("EPIC-100")

        # Should return empty list, not raise an error
        assert result == []

    @patch("budjira.services.issues.IssueService")
    def test_jql_queries_correct(self, mock_issue_service_class: MagicMock, mock_jira_client: MagicMock) -> None:
        """Test that correct JQL queries are executed."""
        mock_issue_service = MagicMock()
        mock_issue_service.search.return_value = []
        mock_issue_service_class.return_value = mock_issue_service

        service = EpicService(mock_jira_client)
        service.get_epic_issues("PROJ-100")

        # Check both queries were called with correct JQL
        calls = mock_issue_service.search.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "parent = PROJ-100"
        assert calls[1][0][0] == '"Epic Link" = PROJ-100'
