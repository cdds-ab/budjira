"""Data models for Jira sprints and boards."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SprintState(str, Enum):
    """Jira sprint states."""

    ACTIVE = "active"
    FUTURE = "future"
    CLOSED = "closed"


class Board(BaseModel):
    """Jira Scrum board."""

    id: int = Field(..., description="Board ID")
    name: str = Field(..., description="Board name")
    board_type: str = Field(..., description="Board type (scrum, kanban)")

    @classmethod
    def from_jira_board(cls, jira_board: Any) -> Board:
        """Create Board from jira library board object.

        Args:
            jira_board: Board object from jira library

        Returns:
            Board model instance
        """
        return cls(
            id=jira_board.id,
            name=jira_board.name,
            board_type=jira_board.raw.get("type", "unknown") if hasattr(jira_board, "raw") else "unknown",
        )


class Sprint(BaseModel):
    """Jira sprint."""

    id: int = Field(..., description="Sprint ID")
    name: str = Field(..., description="Sprint name")
    state: SprintState = Field(..., description="Sprint state")
    start_date: date | None = Field(default=None, description="Sprint start date")
    end_date: date | None = Field(default=None, description="Sprint end date")
    complete_date: date | None = Field(default=None, description="Sprint completion date")
    board_id: int | None = Field(default=None, description="Board ID this sprint belongs to")

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        """Parse a date string from the Jira API.

        Handles ISO format strings like '2025-01-15T10:00:00.000Z'.

        Args:
            date_str: Date string or None

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            return None

    @classmethod
    def from_jira_sprint(cls, jira_sprint: Any) -> Sprint:
        """Create Sprint from jira library sprint object.

        Args:
            jira_sprint: Sprint object from jira library

        Returns:
            Sprint model instance
        """
        raw = jira_sprint.raw if hasattr(jira_sprint, "raw") else {}

        state_str = getattr(jira_sprint, "state", raw.get("state", "future"))
        try:
            state = SprintState(state_str.lower())
        except ValueError:
            state = SprintState.FUTURE

        return cls(
            id=jira_sprint.id,
            name=jira_sprint.name,
            state=state,
            start_date=cls._parse_date(raw.get("startDate")),
            end_date=cls._parse_date(raw.get("endDate")),
            complete_date=cls._parse_date(raw.get("completeDate")),
            board_id=raw.get("originBoardId"),
        )


class SprintSummary(BaseModel):
    """Summary statistics for a sprint."""

    sprint: Sprint = Field(..., description="Sprint details")
    total_issues: int = Field(default=0, description="Total number of issues")
    done_issues: int = Field(default=0, description="Issues in done state")
    in_progress_issues: int = Field(default=0, description="Issues in progress")
    todo_issues: int = Field(default=0, description="Issues in to-do state")
