"""Tests for Tempo models."""

from datetime import date, datetime

import pytest
from budjira.tempo.models import (
    TempoAccount,
    TempoAuthor,
    TempoIssue,
    TempoTimesheetApprovalStatus,
    TempoWorklog,
    TempoWorklogCreate,
    TempoWorklogUpdate,
)
from pydantic import ValidationError


def test_tempo_issue_valid():
    """Test TempoIssue model with valid data."""
    issue = TempoIssue(
        self="https://api.tempo.io/issues/123",
        key="PROJ-123",
        id=123,
    )
    assert issue.key == "PROJ-123"
    assert issue.id == 123


def test_tempo_issue_without_key():
    """Test TempoIssue model without key (some worklogs may have no issue key)."""
    issue = TempoIssue(
        self="https://api.tempo.io/issues/123",
        id=123,
    )
    assert issue.key is None
    assert issue.id == 123


def test_tempo_author_valid():
    """Test TempoAuthor model with valid data."""
    author = TempoAuthor(
        self="https://api.tempo.io/users/123",
        accountId="557058:abc123",
        displayName="John Doe",
    )
    assert author.accountId == "557058:abc123"
    assert author.displayName == "John Doe"


def test_tempo_account_valid():
    """Test TempoAccount model with valid data."""
    account = TempoAccount(
        self="https://api.tempo.io/accounts/123",
        key="ACCT-1",
        id=123,
        name="Project Account",
        status="OPEN",
    )
    assert account.key == "ACCT-1"
    assert account.name == "Project Account"
    assert account.status == "OPEN"


def test_tempo_account_with_alias():
    """Test TempoAccount handles 'global' field alias."""
    data = {
        "self": "https://api.tempo.io/accounts/123",
        "key": "GLOBAL",
        "id": 1,
        "name": "Global Account",
        "status": "OPEN",
        "global": True,
    }
    account = TempoAccount(**data)  # type: ignore[arg-type]
    assert account.global_ is True


def test_tempo_worklog_valid():
    """Test TempoWorklog model with valid data."""
    worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/12345",
        tempoWorklogId=12345,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PROJ-123"),
        timeSpentSeconds=7200,
        startDate=date(2025, 10, 25),
        startTime="09:00:00",
        description="Sizing analysis",
        createdAt=datetime(2025, 10, 25, 9, 15),
        updatedAt=datetime(2025, 10, 25, 9, 15),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:abc",
        ),
    )
    assert worklog.tempoWorklogId == 12345
    assert worklog.issue.key == "PROJ-123"
    assert worklog.timeSpentSeconds == 7200
    assert worklog.description == "Sizing analysis"


def test_tempo_worklog_optional_fields():
    """Test TempoWorklog with minimal required fields."""
    worklog = TempoWorklog(
        self="https://api.tempo.io/worklogs/12345",
        tempoWorklogId=12345,
        issue=TempoIssue(self="https://api.tempo.io/issues/123", key="PROJ-123"),
        timeSpentSeconds=3600,
        startDate=date(2025, 10, 25),
        createdAt=datetime(2025, 10, 25, 9, 0),
        updatedAt=datetime(2025, 10, 25, 9, 0),
        author=TempoAuthor(
            self="https://api.tempo.io/users/123",
            accountId="557058:abc",
        ),
    )
    assert worklog.description is None
    assert worklog.startTime is None
    assert worklog.billableSeconds is None


def test_tempo_worklog_create_valid():
    """Test TempoWorklogCreate model with valid data."""
    worklog_data = TempoWorklogCreate(
        issueId=12345,
        timeSpentSeconds=7200,
        startDate="2025-10-25",
        startTime="09:00:00",
        description="Development work",
        authorAccountId="557058:abc123",
    )
    assert worklog_data.issueId == 12345
    assert worklog_data.timeSpentSeconds == 7200
    assert worklog_data.startDate == "2025-10-25"
    assert worklog_data.description == "Development work"


def test_tempo_worklog_create_minimal():
    """Test TempoWorklogCreate with minimal required fields."""
    worklog_data = TempoWorklogCreate(
        issueId=67890,
        timeSpentSeconds=3600,
        startDate="2025-10-25",
        authorAccountId="557058:xyz",
    )
    assert worklog_data.issueId == 67890
    assert worklog_data.timeSpentSeconds == 3600
    assert worklog_data.startTime == "09:00:00"  # Default value
    assert worklog_data.description is None


def test_tempo_worklog_create_missing_required():
    """Test TempoWorklogCreate fails with missing required fields."""
    with pytest.raises(ValidationError):
        TempoWorklogCreate(  # type: ignore[call-arg]
            timeSpentSeconds=3600,
            startDate="2025-10-25",
            # Missing issueId and authorAccountId
        )


def test_tempo_worklog_create_model_dump():
    """Test TempoWorklogCreate model_dump excludes None values."""
    worklog_data = TempoWorklogCreate(
        issueId=12345,
        timeSpentSeconds=7200,
        startDate="2025-10-25",
        authorAccountId="557058:abc",
        description="Test",
    )
    dumped = worklog_data.model_dump(exclude_none=True)
    assert "billableSeconds" not in dumped
    assert "remainingEstimateSeconds" not in dumped
    assert "description" in dumped


def test_tempo_worklog_update_valid():
    """Test TempoWorklogUpdate model with all fields."""
    update_data = TempoWorklogUpdate(
        issueId=12345,
        timeSpentSeconds=7200,
        startDate="2025-10-28",
        startTime="14:00:00",
        description="Updated comment",
        authorAccountId="557058:abc123",
        billableSeconds=7200,
        remainingEstimateSeconds=3600,
    )
    assert update_data.issueId == 12345
    assert update_data.timeSpentSeconds == 7200
    assert update_data.startDate == "2025-10-28"
    assert update_data.description == "Updated comment"


def test_tempo_worklog_update_partial():
    """Test TempoWorklogUpdate with only some fields (partial update)."""
    update_data = TempoWorklogUpdate(
        timeSpentSeconds=3600,
        startDate="2025-10-29",
    )
    assert update_data.timeSpentSeconds == 3600
    assert update_data.startDate == "2025-10-29"
    assert update_data.description is None
    assert update_data.issueId is None


def test_tempo_worklog_update_empty():
    """Test TempoWorklogUpdate with no fields (all optional)."""
    update_data = TempoWorklogUpdate()
    assert update_data.issueId is None
    assert update_data.timeSpentSeconds is None
    assert update_data.startDate is None
    assert update_data.description is None


def test_tempo_worklog_update_model_dump():
    """Test TempoWorklogUpdate model_dump excludes None values."""
    update_data = TempoWorklogUpdate(
        timeSpentSeconds=7200,
        description="Partial update",
    )
    dumped = update_data.model_dump(exclude_none=True)
    assert dumped == {
        "timeSpentSeconds": 7200,
        "description": "Partial update",
    }
    assert "issueId" not in dumped
    assert "startDate" not in dumped
    assert "billableSeconds" not in dumped


def test_tempo_timesheet_period_valid():
    """Test TempoTimesheetPeriod parses the API 'from' alias."""
    from budjira.tempo.models import TempoTimesheetPeriod

    period = TempoTimesheetPeriod(**{"from": "2026-08-01", "to": "2026-08-31"})  # type: ignore[arg-type]
    assert period.from_ == date(2026, 8, 1)
    assert period.to == date(2026, 8, 31)


def test_tempo_timesheet_period_serializes_alias():
    """Test TempoTimesheetPeriod serializes back to the API field names."""
    from budjira.tempo.models import TempoTimesheetPeriod

    period = TempoTimesheetPeriod(**{"from": "2026-08-01", "to": "2026-08-31"})  # type: ignore[arg-type]
    dumped = period.model_dump(by_alias=True, mode="json")
    assert dumped == {"from": "2026-08-01", "to": "2026-08-31"}


def test_tempo_timesheet_period_missing_to():
    """Test TempoTimesheetPeriod requires the 'to' field."""
    from budjira.tempo.models import TempoTimesheetPeriod

    with pytest.raises(ValidationError):
        TempoTimesheetPeriod(**{"from": "2026-08-01"})  # type: ignore[arg-type]


def test_tempo_timesheet_approval_status_valid():
    """Test TempoTimesheetApprovalStatus with a full API payload."""
    from budjira.tempo.models import TempoTimesheetApprovalStatus

    status = TempoTimesheetApprovalStatus(
        key="APPROVED",
        actor={"self": "https://api.tempo.io/users/1", "accountId": "557058:abc"},
        comment="Reviewed",
        updatedAt=datetime(2026, 9, 1, 10, 0),
    )
    assert status.key == "APPROVED"
    assert status.actor is not None
    assert status.actor["accountId"] == "557058:abc"
    assert status.comment == "Reviewed"


def test_tempo_timesheet_approval_status_minimal():
    """Test TempoTimesheetApprovalStatus with only the required key."""
    from budjira.tempo.models import TempoTimesheetApprovalStatus

    status = TempoTimesheetApprovalStatus(key="OPEN")
    assert status.actor is None
    assert status.comment is None
    assert status.updatedAt is None


def test_tempo_timesheet_approval_status_missing_key():
    """Test TempoTimesheetApprovalStatus requires the key."""
    from budjira.tempo.models import TempoTimesheetApprovalStatus

    with pytest.raises(ValidationError):
        TempoTimesheetApprovalStatus()  # type: ignore[call-arg]


def test_tempo_timesheet_approval_valid_measured_payload():
    """Test TempoTimesheetApproval parses the measured Tempo Cloud v4 response (#137)."""
    from budjira.tempo.models import TempoTimesheetApproval

    data = {
        "period": {"from": "2026-08-01", "to": "2026-08-31"},
        "status": {"key": "OPEN"},
        "requiredSeconds": 147200,
        "timeSpentSeconds": 80000,
        "actions": {
            "submit": "https://api.tempo.io/4/timesheet-approvals/user/557058:abc/submit?from=2026-08-01&to=2026-08-31"
        },
    }
    approval = TempoTimesheetApproval(**data)  # type: ignore[arg-type]
    assert approval.status.key == "OPEN"
    assert approval.period is not None
    assert approval.period.from_ == date(2026, 8, 1)
    assert approval.requiredSeconds == 147200
    assert approval.timeSpentSeconds == 80000
    assert approval.allows("submit")
    assert not approval.allows("approve")
    assert approval.allowed_actions == ["submit"]


def test_tempo_timesheet_approval_defaults():
    """Test TempoTimesheetApproval defaults for optional fields."""
    from budjira.tempo.models import TempoTimesheetApproval

    approval = TempoTimesheetApproval(status=TempoTimesheetApprovalStatus(key="IN_REVIEW"))
    assert approval.period is None
    assert approval.requiredSeconds == 0
    assert approval.timeSpentSeconds == 0
    assert approval.actions == {}
    assert approval.allowed_actions == []
    assert not approval.allows("submit")


def test_tempo_timesheet_approval_multiple_actions_sorted():
    """Test allowed_actions returns the sorted action names."""
    from budjira.tempo.models import TempoTimesheetApproval

    approval = TempoTimesheetApproval(
        status=TempoTimesheetApprovalStatus(key="IN_REVIEW"),
        actions={"reopen": "https://example.com/reopen", "approve": "https://example.com/approve"},
    )
    assert approval.allowed_actions == ["approve", "reopen"]


def test_tempo_timesheet_approval_missing_status():
    """Test TempoTimesheetApproval requires a status."""
    from budjira.tempo.models import TempoTimesheetApproval

    with pytest.raises(ValidationError):
        TempoTimesheetApproval(requiredSeconds=100)  # type: ignore[call-arg]


def test_tempo_timesheet_approval_model_dump():
    """Test TempoTimesheetApproval serializes for JSON output."""
    from budjira.tempo.models import TempoTimesheetApproval

    approval = TempoTimesheetApproval(
        status=TempoTimesheetApprovalStatus(key="APPROVED"),
        requiredSeconds=3600,
        timeSpentSeconds=3600,
        actions={},
    )
    dumped = approval.model_dump(mode="json")
    assert dumped["status"]["key"] == "APPROVED"
    assert dumped["requiredSeconds"] == 3600
