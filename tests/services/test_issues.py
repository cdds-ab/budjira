# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for issue service."""

from unittest.mock import MagicMock, patch

import pytest
from budjira.services.issues import CURRENT_USER_PLACEHOLDER, IssueService, build_create_fields, build_update_fields
from budjira.utils.errors import InvalidIssueError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


class TestDeleteIssue:
    """Test delete method."""

    def test_delete_success(self) -> None:
        """Test deleting an issue successfully."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue

        service = IssueService(mock_client)
        service.delete("PROJ-123")

        mock_client.issue.assert_called_once_with("PROJ-123")
        mock_issue.delete.assert_called_once_with(deleteSubtasks=False)

    def test_delete_with_subtasks(self) -> None:
        """Test deleting an issue with subtasks."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue

        service = IssueService(mock_client)
        service.delete("PROJ-123", delete_subtasks=True)

        mock_client.issue.assert_called_once_with("PROJ-123")
        mock_issue.delete.assert_called_once_with(deleteSubtasks=True)

    def test_delete_issue_not_found(self) -> None:
        """Test deleting a non-existent issue raises InvalidIssueError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = IssueService(mock_client)

        with pytest.raises(InvalidIssueError, match="Issue 'PROJ-999' not found"):
            service.delete("PROJ-999")

    def test_delete_permission_denied(self) -> None:
        """Test deleting without permission raises PermissionError."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=403, text="Permission denied")

        service = IssueService(mock_client)

        with pytest.raises(BudjiraPermissionError, match="Permission denied deleting issue"):
            service.delete("PROJ-123")

    def test_delete_api_error(self) -> None:
        """Test deleting with unexpected API error."""
        mock_client = MagicMock()
        mock_client.issue.side_effect = JIRAError(status_code=500, text="Server error")

        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError):
            service.delete("PROJ-123")


class TestDescriptionConversion:
    """Markdown descriptions must be converted to Jira wiki markup on upload."""

    def test_create_converts_markdown_description(self) -> None:
        """create() sends wiki markup, not raw Markdown (issue #95)."""
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create("PROJ", "summary", "Task", description="## Title\n- [ ] todo")

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["description"] == "h2. Title\n* (x) todo"

    def test_update_converts_markdown_description(self) -> None:
        """update() sends wiki markup, not raw Markdown (issue #95)."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        service = IssueService(mock_client)

        service.update("PROJ-1", description="## Title\n- [ ] todo")

        fields = mock_issue.update.call_args.kwargs["fields"]
        assert fields["description"] == "h2. Title\n* (x) todo"


WIKI_DESCRIPTION = "{panel:bgColor=#eae6ff}\nh3. Steps\n# first\n# second\n{panel}"


class TestWikiDialectPassthrough:
    """The wiki dialect uploads a description byte-for-byte (issue #106)."""

    def test_create_sends_wiki_description_unchanged(self) -> None:
        """Panel macro, h3. heading and # ordered list survive create()."""
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create(
                "PROJ",
                "summary",
                "Task",
                description=WIKI_DESCRIPTION,
                description_dialect="wiki",
            )

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["description"] == WIKI_DESCRIPTION

    def test_update_sends_wiki_description_unchanged(self) -> None:
        """Panel macro, h3. heading and # ordered list survive update()."""
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        service = IssueService(mock_client)

        service.update("PROJ-1", description=WIKI_DESCRIPTION, description_dialect="wiki")

        fields = mock_issue.update.call_args.kwargs["fields"]
        assert fields["description"] == WIKI_DESCRIPTION


class TestBuildCreateFields:
    """Test the payload builder shared by create() and --dry-run."""

    def test_minimal_payload(self) -> None:
        """Only the mandatory keys are present when nothing optional is given."""
        fields = build_create_fields("PROJ", "Summary", "Bug")

        assert fields == {
            "project": {"key": "PROJ"},
            "summary": "Summary",
            "issuetype": {"name": "Bug"},
        }

    def test_markdown_description_is_converted(self) -> None:
        """Markdown is converted to wiki markup for the payload."""
        fields = build_create_fields("PROJ", "S", "Bug", description="## Heading", description_dialect="markdown")

        assert fields["description"] == "h2. Heading"

    def test_wiki_description_passes_through(self) -> None:
        """Wiki dialect sends the description unchanged."""
        fields = build_create_fields("PROJ", "S", "Bug", description="# ordered", description_dialect="wiki")

        assert fields["description"] == "# ordered"

    def test_optional_fields_and_extra_fields_merged(self) -> None:
        """Priority, assignee, labels and extra fields (parent, timetracking, custom) land in the payload."""
        fields = build_create_fields(
            "PROJ",
            "S",
            "Subtask",
            priority="High",
            assignee="john.doe",
            labels=["bug"],
            extra_fields={"parent": {"key": "PROJ-1"}, "customfield_10001": "x"},
        )

        assert fields["priority"] == {"name": "High"}
        assert fields["assignee"] == {"name": "john.doe"}
        assert fields["labels"] == ["bug"]
        assert fields["parent"] == {"key": "PROJ-1"}
        assert fields["customfield_10001"] == "x"


class TestBuildUpdateFields:
    """Test the payload builder shared by update() and --dry-run."""

    def test_assignee_name(self) -> None:
        fields = build_update_fields(assignee="john.doe")

        assert fields["assignee"] == {"name": "john.doe"}

    def test_assignee_current_user_with_account_id(self) -> None:
        fields = build_update_fields(assignee="currentUser()", current_user_account_id="abc123")

        assert fields["assignee"] == {"accountId": "abc123"}

    def test_assignee_current_user_without_id_uses_placeholder(self) -> None:
        """The dry run resolves nothing; the payload shows where resolution happens."""
        fields = build_update_fields(assignee="currentUser()")

        assert fields["assignee"] == {"accountId": CURRENT_USER_PLACEHOLDER}

    def test_unassign(self) -> None:
        fields = build_update_fields(assignee="")

        assert fields["assignee"] is None

    def test_priority_summary_description(self) -> None:
        fields = build_update_fields(priority="High", summary="New", description="## Heading")

        assert fields["priority"] == {"name": "High"}
        assert fields["summary"] == "New"
        assert fields["description"] == "h2. Heading"

    def test_wiki_description_passes_through(self) -> None:
        fields = build_update_fields(description="h3. Panel", description_dialect="wiki")

        assert fields["description"] == "h3. Panel"

    def test_input_fields_dict_not_mutated(self) -> None:
        original = {"timetracking": {"originalEstimate": "2h"}}

        fields = build_update_fields(fields=original, priority="High")

        assert original == {"timetracking": {"originalEstimate": "2h"}}
        assert fields["timetracking"] == {"originalEstimate": "2h"}
        assert fields["priority"] == {"name": "High"}

    def test_service_update_resolves_current_user_via_myself(self) -> None:
        """update() keeps resolving currentUser() through a myself() read call."""
        mock_client = MagicMock()
        mock_client.myself.return_value = {"accountId": "abc123"}
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        service = IssueService(mock_client)

        service.update("PROJ-1", assignee="currentUser()")

        fields = mock_issue.update.call_args.kwargs["fields"]
        assert fields["assignee"] == {"accountId": "abc123"}


class TestPriorityId:
    """Priority can be sent as {"id": ...} for instances that reject names."""

    def test_create_with_priority_id_sends_id(self) -> None:
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create("PROJ", "summary", "Task", priority_id="3")

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["priority"] == {"id": "3"}

    def test_create_with_priority_name_sends_name(self) -> None:
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create("PROJ", "summary", "Task", priority="High")

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["priority"] == {"name": "High"}

    def test_create_with_priority_id_wins_over_name(self) -> None:
        """The service trusts the caller's explicit id when both are given."""
        mock_client = MagicMock()
        service = IssueService(mock_client)

        with patch("budjira.services.issues.Issue.from_jira_issue", return_value=MagicMock()):
            service.create("PROJ", "summary", "Task", priority="High", priority_id="3")

        fields = mock_client.create_issue.call_args.kwargs["fields"]
        assert fields["priority"] == {"id": "3"}

    def test_update_with_priority_id_sends_id(self) -> None:
        mock_client = MagicMock()
        mock_issue = MagicMock()
        mock_client.issue.return_value = mock_issue
        service = IssueService(mock_client)

        service.update("PROJ-1", priority_id="3")

        fields = mock_issue.update.call_args.kwargs["fields"]
        assert fields["priority"] == {"id": "3"}


class TestPriorityErrorHint:
    """A rejected priority names the values the instance actually offers."""

    @staticmethod
    def _client_with_priorities() -> MagicMock:
        mock_client = MagicMock()
        high = MagicMock()
        high.name = "High"
        medium = MagicMock()
        medium.name = "Medium"
        mock_client.priorities.return_value = [high, medium]
        return mock_client

    def test_create_400_with_priority_lists_available_priorities(self) -> None:
        mock_client = self._client_with_priorities()
        mock_client.create_issue.side_effect = JIRAError(status_code=400, text="priority not valid")
        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError, match="Available priorities on this instance: High, Medium"):
            service.create("PROJ", "summary", "Task", priority="Urgent")

    def test_create_400_with_priority_id_lists_available_priorities(self) -> None:
        mock_client = self._client_with_priorities()
        mock_client.create_issue.side_effect = JIRAError(status_code=400, text="priority not valid")
        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError, match="Available priorities on this instance: High, Medium"):
            service.create("PROJ", "summary", "Task", priority_id="99")

    def test_create_400_without_priority_has_no_hint(self) -> None:
        mock_client = self._client_with_priorities()
        mock_client.create_issue.side_effect = JIRAError(status_code=400, text="bad field")
        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError, match="bad field") as exc_info:
            service.create("PROJ", "summary", "Task")

        assert "Available priorities" not in str(exc_info.value)
        mock_client.priorities.assert_not_called()

    def test_update_400_with_priority_lists_available_priorities(self) -> None:
        mock_client = self._client_with_priorities()
        mock_client.issue.return_value.update.side_effect = JIRAError(status_code=400, text="priority not valid")
        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError, match="Available priorities on this instance: High, Medium"):
            service.update("PROJ-1", priority="Urgent")

    def test_failing_priorities_read_never_masks_the_original_error(self) -> None:
        mock_client = MagicMock()
        mock_client.create_issue.side_effect = JIRAError(status_code=400, text="priority not valid")
        mock_client.priorities.side_effect = JIRAError(status_code=500, text="down")
        service = IssueService(mock_client)

        with pytest.raises(JiraAPIError, match="priority not valid") as exc_info:
            service.create("PROJ", "summary", "Task", priority="Urgent")

        assert "Available priorities" not in str(exc_info.value)
