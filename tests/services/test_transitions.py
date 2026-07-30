# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for the transition service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_jira() -> MagicMock:
    """Mocked jira-python client."""
    return MagicMock()


def test_get_transition_details_requests_screen_fields(mock_jira: MagicMock) -> None:
    """The expand parameter is required, otherwise no field metadata comes back."""
    from budjira.services.transitions import TransitionService

    mock_jira.transitions.return_value = []
    service = TransitionService(mock_jira)

    service.get_transition_details("PROJ-123")

    mock_jira.transitions.assert_called_once_with("PROJ-123", expand="transitions.fields")


def test_get_transition_details_maps_screen_fields(mock_jira: MagicMock) -> None:
    """Raw Jira metadata is mapped into typed models."""
    from budjira.services.transitions import TransitionService

    mock_jira.transitions.return_value = [
        {
            "id": "21",
            "name": "Resolve",
            "to": {"name": "Resolved"},
            "fields": {
                "resolution": {
                    "required": True,
                    "name": "Resolution",
                    "schema": {"type": "resolution"},
                    "allowedValues": [{"name": "Done"}, {"name": "Won't Do"}],
                },
                "customfield_10001": {
                    "required": False,
                    "name": "Solution details",
                    "schema": {"type": "string"},
                },
            },
        }
    ]
    service = TransitionService(mock_jira)

    transitions = service.get_transition_details("PROJ-123")

    assert len(transitions) == 1
    assert transitions[0].id == "21"
    assert transitions[0].to_status == "Resolved"

    by_id = {f.field_id: f for f in transitions[0].fields}
    assert by_id["resolution"].required is True
    assert by_id["resolution"].field_type == "resolution"
    assert by_id["resolution"].allowed_values == ["Done", "Won't Do"]
    assert by_id["customfield_10001"].required is False
    assert by_id["customfield_10001"].allowed_values is None


def test_transition_forwards_fields(mock_jira: MagicMock) -> None:
    """Screen field values must reach transition_issue."""
    from budjira.services.transitions import TransitionService

    mock_jira.transitions.return_value = [{"id": "21", "name": "Resolve"}]
    service = TransitionService(mock_jira)

    service.transition("PROJ-123", "Resolve", fields={"resolution": {"name": "Done"}})

    mock_jira.transition_issue.assert_called_once_with("PROJ-123", "21", fields={"resolution": {"name": "Done"}})


def test_transition_without_fields_sends_none(mock_jira: MagicMock) -> None:
    """Existing behaviour is preserved when no fields are supplied."""
    from budjira.services.transitions import TransitionService

    mock_jira.transitions.return_value = [{"id": "11", "name": "Start Progress"}]
    service = TransitionService(mock_jira)

    service.transition("PROJ-123", "Start Progress")

    mock_jira.transition_issue.assert_called_once_with("PROJ-123", "11", fields=None)


def test_get_transition_details_handles_transition_without_screen(mock_jira: MagicMock) -> None:
    """A transition with no screen has no fields, not an error."""
    from budjira.services.transitions import TransitionService

    mock_jira.transitions.return_value = [{"id": "11", "name": "Start Progress"}]
    service = TransitionService(mock_jira)

    transitions = service.get_transition_details("PROJ-123")

    assert transitions[0].fields == []
    assert transitions[0].to_status is None


def test_get_transition_details_maps_404_to_invalid_issue(mock_jira: MagicMock) -> None:
    """A missing issue is reported as an issue problem, not a generic API error."""
    from budjira.services.transitions import TransitionService
    from budjira.utils.errors import InvalidIssueError
    from jira.exceptions import JIRAError

    mock_jira.transitions.side_effect = JIRAError(status_code=404, text="Not Found")
    service = TransitionService(mock_jira)

    with pytest.raises(InvalidIssueError, match="not found"):
        service.get_transition_details("PROJ-999")


def test_get_transition_details_maps_403_to_permission_error(mock_jira: MagicMock) -> None:
    """A permission problem keeps its own exception type."""
    from budjira.services.transitions import TransitionService
    from budjira.utils.errors import PermissionError as BudjiraPermissionError
    from jira.exceptions import JIRAError

    mock_jira.transitions.side_effect = JIRAError(status_code=403, text="Forbidden")
    service = TransitionService(mock_jira)

    with pytest.raises(BudjiraPermissionError):
        service.get_transition_details("PROJ-123")


def test_get_transition_details_wraps_unexpected_errors(mock_jira: MagicMock) -> None:
    """Anything else surfaces as a JiraAPIError rather than leaking out raw."""
    from budjira.services.transitions import TransitionService
    from budjira.utils.errors import JiraAPIError

    mock_jira.transitions.side_effect = RuntimeError("socket exploded")
    service = TransitionService(mock_jira)

    with pytest.raises(JiraAPIError, match="Unexpected error"):
        service.get_transition_details("PROJ-123")
