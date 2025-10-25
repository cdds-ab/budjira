"""Pydantic models for Tempo Timesheets API."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class TempoIssue(BaseModel):
    """Jira issue reference in Tempo API."""

    self: str
    key: str
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

    issueKey: str
    timeSpentSeconds: int
    startDate: str  # YYYY-MM-DD
    startTime: str = "09:00:00"
    description: str | None = None
    authorAccountId: str
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
