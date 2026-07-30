"""Parsing, resolution and encoding of transition screen field values.

These helpers are pure functions over transition metadata: no Jira client, no I/O.
The CLI composes them, which keeps the fiddly matching logic testable on its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from budjira.utils.errors import ValidationError

if TYPE_CHECKING:
    from budjira.models.transition import Transition, TransitionField

# Field schema types that Jira expects wrapped rather than as a plain string.
_NAME_WRAPPED_TYPES = {"resolution", "priority"}
_VALUE_WRAPPED_TYPES = {"option"}
_ARRAY_TYPES = {"array"}


def parse_field_args(field_args: list[str] | None) -> dict[str, str]:
    """Parse repeatable --field key=value arguments.

    Args:
        field_args: Raw strings from the CLI, or None

    Returns:
        Mapping of user-supplied key to raw string value

    Raises:
        ValidationError: If an argument is not in key=value form
    """
    parsed: dict[str, str] = {}
    for arg in field_args or []:
        key, separator, value = arg.partition("=")
        if not separator or not key.strip():
            raise ValidationError(
                f"Invalid field argument '{arg}'. Expected format: key=value (e.g., --field resolution=Done)."
            )
        parsed[key.strip()] = value
    return parsed


def encode_field_value(field: TransitionField, value: str) -> Any:
    """Encode a raw string into the shape Jira expects for this field type.

    Structured fields reject a plain string: a select field needs {"value": ...},
    a multi-select a list of those, and resolution/priority accept {"name": ...}.
    Types beyond these are deliberately passed through untouched, so an
    unsupported one surfaces as a Jira error instead of being silently mangled.

    Args:
        field: The screen field the value belongs to
        value: Raw string from the CLI or a prompt

    Returns:
        The value in Jira's expected representation
    """
    field_type = (field.field_type or "").lower()
    if field_type in _ARRAY_TYPES:
        return [{"value": value}]
    if field_type in _VALUE_WRAPPED_TYPES:
        return {"value": value}
    if field_type in _NAME_WRAPPED_TYPES:
        return {"name": value}
    return value


def resolve_fields(raw_fields: dict[str, str], transition: Transition) -> dict[str, Any]:
    """Resolve user-supplied keys against a transition's screen fields.

    A key matches either a field id exactly or a display name case-insensitively.

    Args:
        raw_fields: Mapping of user-supplied key to raw string value
        transition: The transition whose screen defines the valid fields

    Returns:
        Mapping of Jira field id to encoded value

    Raises:
        ValidationError: If a key is unknown or ambiguous, or a value is not allowed
    """
    resolved: dict[str, Any] = {}
    for key, value in raw_fields.items():
        field = _match_field(key, transition)
        if field.allowed_values and value not in field.allowed_values:
            allowed = ", ".join(field.allowed_values)
            raise ValidationError(
                f"Value '{value}' is not allowed for field '{field.name}' ({field.field_id}). "
                f"Allowed values: {allowed}"
            )
        resolved[field.field_id] = encode_field_value(field, value)
    return resolved


def _match_field(key: str, transition: Transition) -> TransitionField:
    """Find the single screen field a user-supplied key refers to.

    Args:
        key: Field id or display name as typed by the user
        transition: The transition whose screen is being matched against

    Returns:
        The matching field

    Raises:
        ValidationError: If the key matches no field or several
    """
    for field in transition.fields:
        if field.field_id == key:
            return field

    matches = [f for f in transition.fields if f.name.lower() == key.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        candidates = ", ".join(f.field_id for f in matches)
        raise ValidationError(
            f"Field name '{key}' is ambiguous on transition '{transition.name}'. "
            f"Use the field id instead: {candidates}"
        )

    available = ", ".join(f"{f.field_id} ('{f.name}')" for f in transition.fields) or "none"
    raise ValidationError(
        f"Unknown field '{key}' for transition '{transition.name}'. Available screen fields: {available}"
    )


def missing_required_fields(resolved: dict[str, Any], transition: Transition) -> list[TransitionField]:
    """List required screen fields that have no value yet.

    Args:
        resolved: Already-resolved values, keyed by Jira field id
        transition: The transition whose screen defines the required fields

    Returns:
        Required fields still missing a value
    """
    return [f for f in transition.fields if f.required and f.field_id not in resolved]


def format_field_requirements(fields: list[TransitionField]) -> str:
    """Render fields as copy-pasteable --field hints.

    Args:
        fields: Fields to describe

    Returns:
        One line per field, ready to paste back as CLI arguments
    """
    lines = []
    for field in fields:
        parts = [f"  --field {field.field_id}=<value>", f"# {field.name}"]
        if field.field_type:
            parts.append(f"[{field.field_type}]")
        if field.allowed_values:
            parts.append(f"one of: {', '.join(field.allowed_values)}")
        lines.append(" ".join(parts))
    return "\n".join(lines)
