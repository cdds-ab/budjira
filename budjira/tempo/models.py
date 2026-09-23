"""Pydantic models for Tempo Timesheets API."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class TempoIssue(BaseModel):
    """Jira issue reference in Tempo API."""

    self: str
    key: str | None = None  # Optional: some worklogs may not have an issue key
    id: int | None = None


class TempoAuthor(BaseModel):
    """Worklog author information."""

    self: str
    accountId: str
    displayName: str | None = None


class TempoAccount(BaseModel):
    """Tempo Account for billing and project tracking."""

    self: str
    key: str
    id: int
    name: str
    status: str = "OPEN"
    global_: bool = Field(alias="global", default=False)


class TempoWorklog(BaseModel):
    """Tempo worklog entry (API response)."""

    self: str
    tempoWorklogId: int
    issue: TempoIssue
    timeSpentSeconds: int
    billableSeconds: int | None = None
    startDate: date
    startTime: str | None = None
    description: str | None = None
    createdAt: datetime
    updatedAt: datetime
    author: TempoAuthor
    attributes: dict[str, Any] | None = None


class TempoWorklogCreate(BaseModel):
    """Tempo worklog creation request."""

    issueId: int  # Numeric issue ID (not issueKey string)
    timeSpentSeconds: int
    startDate: str  # YYYY-MM-DD
    startTime: str = "09:00:00"
    description: str | None = None
    authorAccountId: str
    billableSeconds: int | None = None
    remainingEstimateSeconds: int | None = None


class TempoWorklogUpdate(BaseModel):
    """Tempo worklog update request (all fields optional for partial updates)."""

    issueId: int | None = None
    timeSpentSeconds: int | None = None
    startDate: str | None = None  # YYYY-MM-DD
    startTime: str | None = None
    description: str | None = None
    authorAccountId: str | None = None
    billableSeconds: int | None = None
    remainingEstimateSeconds: int | None = None


class TempoWorklogList(BaseModel):
    """Paginated list of worklogs."""

    results: list[TempoWorklog]
    metadata: dict[str, Any]


class TempoAccountList(BaseModel):
    """Paginated list of accounts."""

    results: list[TempoAccount]
    metadata: dict[str, Any]


class TempoTimesheetPeriod(BaseModel):
    """Period covered by a Tempo timesheet approval."""

    from_: date = Field(alias="from")
    to: date


class TempoTimesheetApprovalStatus(BaseModel):
    """Workflow status of a Tempo timesheet approval.

    The key is one of OPEN / IN_REVIEW / APPROVED / REJECTED. An APPROVED
    timesheet is locked against further bookings in that period.
    """

    key: str
    actor: dict[str, Any] | None = None
    comment: str | None = None
    updatedAt: datetime | None = None


class TempoTimesheetApproval(BaseModel):
    """Tempo timesheet approval for a user and period.

    Response of ``GET /4/timesheet-approvals/user/{accountId}`` and of the
    approval action endpoints (submit/approve/reject/reopen). The ``actions``
    map holds the actions the caller is currently allowed to perform, mapped
    to their API links (e.g. ``submit``).
    """

    status: TempoTimesheetApprovalStatus
    period: TempoTimesheetPeriod | None = None
    requiredSeconds: int = 0
    timeSpentSeconds: int = 0
    actions: dict[str, str] = Field(default_factory=dict)

    @property
    def allowed_actions(self) -> list[str]:
        """Action names the caller may currently perform, sorted (e.g. ``['submit']``)."""
        return sorted(self.actions)

    def allows(self, action: str) -> bool:
        """Check whether the caller may currently perform the given action."""
        return action in self.actions
