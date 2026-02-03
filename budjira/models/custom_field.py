"""Custom field configuration models for connection-level field definitions."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CustomFieldType(str, Enum):
    """Supported custom field types in Jira."""

    TEXT = "text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    USER = "user"
    DATE = "date"
    NUMBER = "number"


# Pattern for Jira custom field IDs
CUSTOM_FIELD_ID_PATTERN = re.compile(r"^customfield_\d+$")


class CustomFieldConfig(BaseModel):
    """Configuration for a custom field in a Jira connection.

    This model defines how a custom field should be handled when creating
    or updating issues. It maps a human-readable name to a Jira field ID
    and specifies validation rules.

    Attributes:
        field_id: The Jira custom field ID (e.g., 'customfield_10001')
        type: The field type, determines how values are formatted
        required: Whether this field must be provided when creating issues
        default: Default value to use if not provided
        options: Valid options for select/multi_select fields
        label: Human-readable label for display in prompts
    """

    field_id: str = Field(
        ...,
        description="Jira custom field ID (e.g., customfield_10001)",
    )
    type: CustomFieldType = Field(
        default=CustomFieldType.TEXT,
        description="Field type determining how values are formatted",
    )
    required: bool = Field(
        default=False,
        description="Whether this field is required when creating issues",
    )
    default: str | None = Field(
        default=None,
        description="Default value if not provided",
    )
    options: list[str] | None = Field(
        default=None,
        description="Valid options for select/multi_select fields",
    )
    label: str | None = Field(
        default=None,
        description="Human-readable label for display in prompts",
    )

    @field_validator("field_id")
    @classmethod
    def validate_field_id(cls, v: str) -> str:
        """Validate that field_id matches Jira custom field pattern."""
        if not CUSTOM_FIELD_ID_PATTERN.match(v):
            raise ValueError(
                f"Invalid field_id '{v}'. Must match pattern 'customfield_<number>' " f"(e.g., 'customfield_10001')"
            )
        return v

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str] | None) -> list[str] | None:
        """Validate that options are provided for select types if specified."""
        # Note: We don't require options to be provided, but if they are,
        # they should be non-empty for select types
        if v is not None and len(v) == 0:
            raise ValueError("Options list cannot be empty if provided")
        return v

    def format_value(self, value: str) -> dict[str, str] | list[dict[str, str]] | str | int | float:
        """Format a value according to the field type for Jira API.

        Args:
            value: The raw value to format

        Returns:
            Formatted value suitable for Jira API
        """
        match self.type:
            case CustomFieldType.SELECT:
                return {"value": value}
            case CustomFieldType.MULTI_SELECT:
                # Handle comma-separated values
                values = [v.strip() for v in value.split(",") if v.strip()]
                return [{"value": v} for v in values]
            case CustomFieldType.USER:
                return {"accountId": value}
            case CustomFieldType.NUMBER:
                # Return as number if possible
                try:
                    if "." in value:
                        return float(value)
                    return int(value)
                except ValueError:
                    return value
            case CustomFieldType.DATE | CustomFieldType.TEXT:
                return value

    def validate_value(self, value: str) -> tuple[bool, str | None]:
        """Validate a value against the field configuration.

        Args:
            value: The value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.type in (CustomFieldType.SELECT, CustomFieldType.MULTI_SELECT) and self.options:
            if self.type == CustomFieldType.MULTI_SELECT:
                values = [v.strip() for v in value.split(",") if v.strip()]
                invalid = [v for v in values if v not in self.options]
                if invalid:
                    return False, f"Invalid option(s): {', '.join(invalid)}. Valid: {', '.join(self.options)}"
            elif value not in self.options:
                return False, f"Invalid option: {value}. Valid: {', '.join(self.options)}"

        if self.type == CustomFieldType.NUMBER:
            try:
                float(value)
            except ValueError:
                return False, f"Invalid number: {value}"

        return True, None

    model_config = {"frozen": False, "validate_assignment": True}
