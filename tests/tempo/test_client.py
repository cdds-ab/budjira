"""Tests for TempoClient."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests
from budjira.tempo.client import TempoClient
from budjira.tempo.models import TempoAccount, TempoWorklog
from budjira.utils.errors import AuthenticationError, JiraAPIError, PermissionError


@pytest.fixture
def tempo_client():
    """Create TempoClient instance for testing."""
    return TempoClient(tempo_token="test_token_123")


@pytest.fixture
def mock_worklog_response():
    """Sample Tempo worklog API response."""
    return {
        "self": "https://api.tempo.io/4/worklogs/12345",
        "tempoWorklogId": 12345,
        "issue": {
            "self": "https://jira.example.com/rest/api/3/issue/123",
            "key": "PROJ-123",
        },
        "timeSpentSeconds": 7200,
        "startDate": "2025-10-25",
        "startTime": "09:00:00",
        "description": "Development work",
        "createdAt": "2025-10-25T09:15:00Z",
        "updatedAt": "2025-10-25T09:15:00Z",
        "author": {
            "self": "https://api.tempo.io/users/123",
            "accountId": "557058:abc123",
            "displayName": "John Doe",
        },
    }


@pytest.fixture
def mock_account_response():
    """Sample Tempo account API response."""
    return {
        "self": "https://api.tempo.io/4/accounts/1",
        "key": "ACCT-1",
        "id": 1,
        "name": "Project Account",
        "status": "OPEN",
        "global": False,
    }


def test_tempo_client_initialization():
    """Test TempoClient initializes correctly."""
    client = TempoClient(tempo_token="my_token")
    assert client.tempo_token == "my_token"
    assert client.session.headers["Authorization"] == "Bearer my_token"
    assert client.session.headers["Content-Type"] == "application/json"


@patch("budjira.tempo.client.requests.Session.request")
def test_create_worklog_success(mock_request, tempo_client, mock_worklog_response):
    """Test successful worklog creation."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_worklog_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    worklog = tempo_client.create_worklog(
        issue_id=12345,
        time_spent_seconds=7200,
        start_date="2025-10-25",
        author_account_id="557058:abc123",
        description="Development work",
    )

    assert isinstance(worklog, TempoWorklog)
    assert worklog.tempoWorklogId == 12345
    assert worklog.issue.key == "PROJ-123"
    assert worklog.timeSpentSeconds == 7200
    assert worklog.description == "Development work"

    # Verify API call
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "POST"
    assert "/worklogs" in call_kwargs["url"]
    assert call_kwargs["json"]["issueId"] == 12345
    assert call_kwargs["json"]["timeSpentSeconds"] == 7200


@patch("budjira.tempo.client.requests.Session.request")
def test_create_worklog_authentication_error(mock_request, tempo_client):
    """Test worklog creation with authentication error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(AuthenticationError, match="Tempo authentication failed"):
        tempo_client.create_worklog(
            issue_id=12345,
            time_spent_seconds=3600,
            start_date="2025-10-25",
            author_account_id="557058:abc",
        )


@patch("budjira.tempo.client.requests.Session.request")
def test_create_worklog_permission_error(mock_request, tempo_client):
    """Test worklog creation with permission error."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(PermissionError, match="Access denied"):
        tempo_client.create_worklog(
            issue_id=12345,
            time_spent_seconds=3600,
            start_date="2025-10-25",
            author_account_id="557058:abc",
        )


@patch("budjira.tempo.client.requests.Session.request")
def test_get_worklogs_success(mock_request, tempo_client, mock_worklog_response):
    """Test successful worklog retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [mock_worklog_response],
        "metadata": {"count": 1, "limit": 50, "offset": 0},
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    worklogs = tempo_client.get_worklogs(
        from_date=date(2025, 10, 1),
        to_date=date(2025, 10, 31),
        limit=50,
    )

    assert len(worklogs) == 1
    assert isinstance(worklogs[0], TempoWorklog)
    assert worklogs[0].tempoWorklogId == 12345

    # Verify API call
    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["params"]["from"] == "2025-10-01"
    assert call_kwargs["params"]["to"] == "2025-10-31"
    assert call_kwargs["params"]["limit"] == 50


@patch("budjira.tempo.client.requests.Session.request")
def test_get_worklogs_with_filters(mock_request, tempo_client):
    """Test worklog retrieval with all filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [], "metadata": {}}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    tempo_client.get_worklogs(
        from_date=date(2025, 10, 1),
        to_date=date(2025, 10, 31),
        issue_id=12345,
        account_id="557058:abc",
        limit=100,
        offset=50,
    )

    call_kwargs = mock_request.call_args[1]
    params = call_kwargs["params"]
    assert params["issueId"] == 12345
    assert params["accountId"] == "557058:abc"
    assert params["limit"] == 100
    assert params["offset"] == 50


@patch("budjira.tempo.client.requests.Session.request")
def test_get_worklogs_never_sends_project_param(mock_request, tempo_client):
    """Tempo v4 rejects a 'project' query parameter with 400 — it must never be sent (#118)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [], "metadata": {}}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    tempo_client.get_worklogs(from_date=date(2025, 10, 1), to_date=date(2025, 10, 31))

    params = mock_request.call_args[1]["params"]
    assert "project" not in params


@patch("budjira.tempo.client.requests.Session.request")
def test_get_worklog_by_id(mock_request, tempo_client, mock_worklog_response):
    """Test getting specific worklog by ID."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_worklog_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    worklog = tempo_client.get_worklog(12345)

    assert isinstance(worklog, TempoWorklog)
    assert worklog.tempoWorklogId == 12345
    assert "/worklogs/12345" in mock_request.call_args[1]["url"]


@patch("budjira.tempo.client.requests.Session.request")
def test_delete_worklog_success(mock_request, tempo_client):
    """Test successful worklog deletion with 204 No Content response."""
    mock_response = MagicMock()
    mock_response.status_code = 204  # No Content
    mock_response.content = b""  # Empty body
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    # Should not raise any exception
    tempo_client.delete_worklog(12345)

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "DELETE"
    assert "/worklogs/12345" in call_kwargs["url"]


@patch("budjira.tempo.client.requests.Session.request")
def test_delete_worklog_not_found_empty_response(mock_request, tempo_client):
    """Test delete worklog with 404 and empty response body."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.content = b""  # Empty body (no JSON)

    # Create HTTPError with the mock response
    error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = error
    mock_request.return_value = mock_response

    # Should raise JiraAPIError with default message
    with pytest.raises(JiraAPIError, match="Resource not found"):
        tempo_client.delete_worklog(99999)


@patch("budjira.tempo.client.requests.Session.request")
def test_get_accounts_success(mock_request, tempo_client, mock_account_response):
    """Test successful accounts retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [mock_account_response],
        "metadata": {"count": 1},
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    accounts = tempo_client.get_accounts(limit=50)

    assert len(accounts) == 1
    assert isinstance(accounts[0], TempoAccount)
    assert accounts[0].key == "ACCT-1"
    assert accounts[0].name == "Project Account"


@patch("budjira.tempo.client.requests.Session.request")
def test_get_account_by_key(mock_request, tempo_client, mock_account_response):
    """Test getting specific account by key."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_account_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    account = tempo_client.get_account("ACCT-1")

    assert isinstance(account, TempoAccount)
    assert account.key == "ACCT-1"
    assert "/accounts/ACCT-1" in mock_request.call_args[1]["url"]


@patch("budjira.tempo.client.requests.Session.request")
def test_network_error(mock_request, tempo_client):
    """Test handling of network errors."""
    mock_request.side_effect = requests.exceptions.RequestException("Network error")

    with pytest.raises(JiraAPIError, match="Failed to connect to Tempo API"):
        tempo_client.get_accounts()


@patch("budjira.tempo.client.requests.Session.request")
def test_404_error_with_message(mock_request, tempo_client):
    """Test handling of 404 errors with API message."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Worklog not found"}
    mock_response.content = b'{"message": "Worklog not found"}'
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(JiraAPIError, match="Worklog not found"):
        tempo_client.get_worklog(99999)


@patch("budjira.tempo.client.requests.Session.request")
def test_update_worklog_success(mock_request, tempo_client, mock_worklog_response):
    """Test successful worklog update."""
    # Prepare updated response
    updated_response = mock_worklog_response.copy()
    updated_response["timeSpentSeconds"] = 10800  # 3h
    updated_response["startDate"] = "2025-10-28"
    updated_response["description"] = "Updated comment"

    mock_response = MagicMock()
    mock_response.json.return_value = updated_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    worklog = tempo_client.update_worklog(
        worklog_id=12345,
        time_spent_seconds=10800,
        start_date="2025-10-28",
        description="Updated comment",
    )

    assert isinstance(worklog, TempoWorklog)
    assert worklog.tempoWorklogId == 12345
    assert worklog.timeSpentSeconds == 10800
    assert worklog.startDate.isoformat() == "2025-10-28"
    assert worklog.description == "Updated comment"

    # Verify API call
    mock_request.assert_called_once()
    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "PUT"
    assert "/worklogs/12345" in call_kwargs["url"]
    assert call_kwargs["json"]["timeSpentSeconds"] == 10800
    assert call_kwargs["json"]["startDate"] == "2025-10-28"
    assert call_kwargs["json"]["description"] == "Updated comment"


@patch("budjira.tempo.client.requests.Session.request")
def test_update_worklog_partial(mock_request, tempo_client, mock_worklog_response):
    """Test partial worklog update (only some fields)."""
    updated_response = mock_worklog_response.copy()
    updated_response["startDate"] = "2025-10-29"

    mock_response = MagicMock()
    mock_response.json.return_value = updated_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    worklog = tempo_client.update_worklog(
        worklog_id=12345,
        start_date="2025-10-29",
    )

    assert isinstance(worklog, TempoWorklog)
    assert worklog.startDate.isoformat() == "2025-10-29"

    # Verify only startDate was sent in request
    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "PUT"
    assert "startDate" in call_kwargs["json"]
    assert "timeSpentSeconds" not in call_kwargs["json"]
    assert "description" not in call_kwargs["json"]


@patch("budjira.tempo.client.requests.Session.request")
def test_update_worklog_authentication_error(mock_request, tempo_client):
    """Test worklog update with authentication error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(AuthenticationError, match="Tempo authentication failed"):
        tempo_client.update_worklog(worklog_id=12345, time_spent_seconds=3600)


@patch("budjira.tempo.client.requests.Session.request")
def test_update_worklog_permission_error(mock_request, tempo_client):
    """Test worklog update with permission error."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(PermissionError, match="Access denied"):
        tempo_client.update_worklog(worklog_id=12345, description="New comment")


@patch("budjira.tempo.client.requests.Session.request")
def test_update_worklog_not_found(mock_request, tempo_client):
    """Test worklog update with 404 error."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Worklog 99999 not found"}
    mock_response.content = b'{"message": "Worklog 99999 not found"}'
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(JiraAPIError, match="Worklog 99999 not found"):
        tempo_client.update_worklog(worklog_id=99999, time_spent_seconds=3600)


@pytest.fixture
def mock_timesheet_approval_response():
    """Sample Tempo timesheet-approval API response (measured shape, #137)."""
    return {
        "period": {"from": "2026-08-01", "to": "2026-08-31"},
        "status": {"key": "OPEN"},
        "requiredSeconds": 147200,
        "timeSpentSeconds": 80000,
        "actions": {
            "submit": "https://api.tempo.io/4/timesheet-approvals/user/557058:abc/submit?from=2026-08-01&to=2026-08-31"
        },
    }


@patch("budjira.tempo.client.requests.Session.request")
def test_get_timesheet_approval_success(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test fetching the timesheet approval status builds the right request."""
    from budjira.tempo.models import TempoTimesheetApproval

    mock_response = MagicMock()
    mock_response.json.return_value = mock_timesheet_approval_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    approval = tempo_client.get_timesheet_approval("557058:abc", date(2026, 8, 1), date(2026, 8, 31))

    assert isinstance(approval, TempoTimesheetApproval)
    assert approval.status.key == "OPEN"
    assert approval.requiredSeconds == 147200
    assert approval.allows("submit")

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "GET"
    assert "/timesheet-approvals/user/557058:abc" in call_kwargs["url"]
    assert call_kwargs["params"] == {"from": "2026-08-01", "to": "2026-08-31"}


@patch("budjira.tempo.client.requests.Session.request")
def test_get_timesheet_approval_authentication_error(mock_request, tempo_client):
    """Test timesheet approval fetch with authentication error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(AuthenticationError, match="Tempo authentication failed"):
        tempo_client.get_timesheet_approval("557058:abc", date(2026, 8, 1), date(2026, 8, 31))


@patch("budjira.tempo.client.requests.Session.request")
def test_get_timesheet_approval_permission_error(mock_request, tempo_client):
    """Test timesheet approval fetch with permission error."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(PermissionError, match="Access denied"):
        tempo_client.get_timesheet_approval("557058:abc", date(2026, 8, 1), date(2026, 8, 31))


@patch("budjira.tempo.client.requests.Session.request")
def test_get_timesheet_approval_not_found(mock_request, tempo_client):
    """Test timesheet approval fetch for an unknown user (404)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "User not found"}
    mock_response.content = b'{"message": "User not found"}'
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(JiraAPIError, match="User not found"):
        tempo_client.get_timesheet_approval("557058:unknown", date(2026, 8, 1), date(2026, 8, 31))


@patch("budjira.tempo.client.requests.Session.request")
def test_submit_timesheet_success(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test submitting a timesheet sends the comment and parses the result."""
    submitted = {**mock_timesheet_approval_response, "status": {"key": "IN_REVIEW"}, "actions": {}}
    mock_response = MagicMock()
    mock_response.json.return_value = submitted
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    approval = tempo_client.submit_timesheet(
        "557058:abc", date(2026, 8, 1), date(2026, 8, 31), comment="All bookings complete"
    )

    assert approval.status.key == "IN_REVIEW"

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "POST"
    assert "/timesheet-approvals/user/557058:abc/submit" in call_kwargs["url"]
    assert call_kwargs["params"] == {"from": "2026-08-01", "to": "2026-08-31"}
    assert call_kwargs["json"] == {"comment": "All bookings complete"}


@patch("budjira.tempo.client.requests.Session.request")
def test_submit_timesheet_without_comment_sends_no_body(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test submitting without a comment omits the JSON body."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_timesheet_approval_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    tempo_client.submit_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31))

    assert mock_request.call_args[1]["json"] is None


@patch("budjira.tempo.client.requests.Session.request")
def test_approve_timesheet_success(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test approving a timesheet (locks the period)."""
    approved = {**mock_timesheet_approval_response, "status": {"key": "APPROVED"}, "actions": {"reopen": "https://x"}}
    mock_response = MagicMock()
    mock_response.json.return_value = approved
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    approval = tempo_client.approve_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31), comment="Reviewed")

    assert approval.status.key == "APPROVED"
    assert approval.allows("reopen")

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "POST"
    assert "/timesheet-approvals/user/557058:abc/approve" in call_kwargs["url"]
    assert call_kwargs["json"] == {"comment": "Reviewed"}


@patch("budjira.tempo.client.requests.Session.request")
def test_approve_timesheet_permission_error(mock_request, tempo_client):
    """Test approving without the approver role (403)."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(PermissionError, match="Access denied"):
        tempo_client.approve_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31))


@patch("budjira.tempo.client.requests.Session.request")
def test_reject_timesheet_success(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test rejecting a submitted timesheet with a comment."""
    rejected = {**mock_timesheet_approval_response, "status": {"key": "REJECTED"}}
    mock_response = MagicMock()
    mock_response.json.return_value = rejected
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    approval = tempo_client.reject_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31), comment="Hours missing")

    assert approval.status.key == "REJECTED"

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "POST"
    assert "/timesheet-approvals/user/557058:abc/reject" in call_kwargs["url"]
    assert call_kwargs["json"] == {"comment": "Hours missing"}


@patch("budjira.tempo.client.requests.Session.request")
def test_reopen_timesheet_success(mock_request, tempo_client, mock_timesheet_approval_response):
    """Test reopening a timesheet returns to OPEN."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_timesheet_approval_response
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    approval = tempo_client.reopen_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31))

    assert approval.status.key == "OPEN"
    assert approval.allows("submit")

    call_kwargs = mock_request.call_args[1]
    assert call_kwargs["method"] == "POST"
    assert "/timesheet-approvals/user/557058:abc/reopen" in call_kwargs["url"]
    assert call_kwargs["params"] == {"from": "2026-08-01", "to": "2026-08-31"}
    assert call_kwargs["json"] is None


@patch("budjira.tempo.client.requests.Session.request")
def test_reopen_timesheet_api_error(mock_request, tempo_client):
    """Test reopening with a server error (e.g. 400 invalid transition)."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"message": "Timesheet cannot be reopened"}
    mock_response.content = b'{"message": "Timesheet cannot be reopened"}'
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
    mock_request.return_value = mock_response

    with pytest.raises(JiraAPIError, match="Timesheet cannot be reopened"):
        tempo_client.reopen_timesheet("557058:abc", date(2026, 8, 1), date(2026, 8, 31))
