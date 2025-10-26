"""Tests for Tempo models."""

from datetime import date, datetime

import pytest
from budjira.tempo.models import (
    TempoAccount,
    TempoAuthor,
    TempoIssue,
    TempoWorklog,
    TempoWorklogCreate,
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
        issueKey="PROJ-123",
        timeSpentSeconds=7200,
        startDate="2025-10-25",
        startTime="09:00:00",
        description="Development work",
        authorAccountId="557058:abc123",
    )
    assert worklog_data.issueKey == "PROJ-123"
    assert worklog_data.timeSpentSeconds == 7200
    assert worklog_data.startDate == "2025-10-25"
    assert worklog_data.description == "Development work"


def test_tempo_worklog_create_minimal():
    """Test TempoWorklogCreate with minimal required fields."""
    worklog_data = TempoWorklogCreate(
        issueKey="PROJ-456",
        timeSpentSeconds=3600,
        startDate="2025-10-25",
        authorAccountId="557058:xyz",
    )
    assert worklog_data.issueKey == "PROJ-456"
    assert worklog_data.timeSpentSeconds == 3600
    assert worklog_data.startTime == "09:00:00"  # Default value
    assert worklog_data.description is None


def test_tempo_worklog_create_missing_required():
    """Test TempoWorklogCreate fails with missing required fields."""
    with pytest.raises(ValidationError):
        TempoWorklogCreate(  # type: ignore[call-arg]
            timeSpentSeconds=3600,
            startDate="2025-10-25",
            # Missing issueKey and authorAccountId
        )


def test_tempo_worklog_create_model_dump():
    """Test TempoWorklogCreate model_dump excludes None values."""
    worklog_data = TempoWorklogCreate(
        issueKey="PROJ-123",
        timeSpentSeconds=7200,
        startDate="2025-10-25",
        authorAccountId="557058:abc",
        description="Test",
    )
    dumped = worklog_data.model_dump(exclude_none=True)
    assert "billableSeconds" not in dumped
    assert "remainingEstimateSeconds" not in dumped
    assert "description" in dumped
