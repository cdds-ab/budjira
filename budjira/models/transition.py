"""Data models for Jira workflow transitions and their screen fields."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransitionField(BaseModel):
    """A single field on a transition screen."""

    field_id: str = Field(..., description="Jira field id (e.g., 'customfield_10001')")
    name: str = Field(..., description="Display name shown on the transition screen")
    required: bool = Field(..., description="Whether Jira marks the field as required")
    field_type: str | None = Field(default=None, description="Field schema type (e.g., 'string', 'option', 'array')")
    allowed_values: list[str] | None = Field(default=None, description="Permitted values, if the field is constrained")


class Transition(BaseModel):
    """A workflow transition available from an issue's current status."""

    id: str = Field(..., description="Transition id used when executing the transition")
    name: str = Field(..., description="Transition name (e.g., 'Start Progress')")
    to_status: str | None = Field(default=None, description="Status the issue reaches through this transition")
    fields: list[TransitionField] = Field(default_factory=list, description="Fields on the transition screen")
