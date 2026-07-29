# Transition Screen Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `budjira issue update --status` supply transition screen fields, and name the field behind a workflow-validator failure instead of forwarding Jira's anonymous message.

**Architecture:** Three layers, each independently testable. Typed models for transition screen metadata (`budjira/models/transition.py`); a service method that requests that metadata and a `fields` parameter that forwards values (`budjira/services/transitions.py`); and pure resolution/encoding/attribution helpers over those models (`budjira/utils/transition_fields.py`) that the CLI composes. The helpers are pure functions with no Jira client, so the tricky logic is testable without mocks.

**Tech Stack:** Python 3.10+, Typer, Pydantic v2, jira-python, pytest, ruff, mypy strict.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-29-transition-screen-fields-design.md`
- All code and comments in English; user-facing CLI messages in English.
- Type hints on every function; mypy strict must pass.
- Line length 120 (ruff).
- Never call a live Jira API in tests; mock at the jira-python boundary with `autospec=True`.
- Coverage ≥70% overall (enforced), ≥90% for the new service and helper code.
- Conventional commits, no Claude attribution.
- `get_transitions()` keeps its current signature and `id`/`name` return shape — existing callers must not break.
- budjira targets Jira REST v2 today; do not add ADF handling (that is Epic #96).

---

### Task 1: Transition screen metadata models

**Files:**
- Create: `budjira/models/transition.py`
- Test: `tests/models/test_transition.py`
- Modify: `budjira/models/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: `TransitionField(field_id: str, name: str, required: bool, field_type: str | None, allowed_values: list[str] | None)` and `Transition(id: str, name: str, to_status: str | None, fields: list[TransitionField])`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for transition models."""

from __future__ import annotations

import pytest
from budjira.models.transition import Transition, TransitionField
from pydantic import ValidationError


class TestTransitionField:
    """Test TransitionField model."""

    def test_minimal_field(self) -> None:
        field = TransitionField(field_id="customfield_10001", name="Solution details", required=True)

        assert field.field_id == "customfield_10001"
        assert field.name == "Solution details"
        assert field.required is True
        assert field.field_type is None
        assert field.allowed_values is None

    def test_field_with_allowed_values(self) -> None:
        field = TransitionField(
            field_id="resolution",
            name="Resolution",
            required=True,
            field_type="resolution",
            allowed_values=["Done", "Won't Do"],
        )

        assert field.field_type == "resolution"
        assert field.allowed_values == ["Done", "Won't Do"]

    def test_missing_required_attribute_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TransitionField(field_id="customfield_10001", name="Solution details")


class TestTransition:
    """Test Transition model."""

    def test_transition_without_fields(self) -> None:
        transition = Transition(id="11", name="Start Progress")

        assert transition.id == "11"
        assert transition.to_status is None
        assert transition.fields == []

    def test_transition_with_fields(self) -> None:
        transition = Transition(
            id="21",
            name="Resolve",
            to_status="Resolved",
            fields=[TransitionField(field_id="resolution", name="Resolution", required=True)],
        )

        assert transition.to_status == "Resolved"
        assert len(transition.fields) == 1
        assert transition.fields[0].field_id == "resolution"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/models/test_transition.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'budjira.models.transition'`

- [ ] **Step 3: Write minimal implementation**

Create `budjira/models/transition.py`:

```python
"""Data models for Jira workflow transitions and their screen fields."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransitionField(BaseModel):
    """A single field on a transition screen."""

    field_id: str = Field(..., description="Jira field id (e.g., 'customfield_10001')")
    name: str = Field(..., description="Display name shown on the transition screen")
    required: bool = Field(..., description="Whether Jira marks the field as required")
    field_type: str | None = Field(None, description="Field schema type (e.g., 'string', 'option', 'array')")
    allowed_values: list[str] | None = Field(None, description="Permitted values, if the field is constrained")


class Transition(BaseModel):
    """A workflow transition available from an issue's current status."""

    id: str = Field(..., description="Transition id used when executing the transition")
    name: str = Field(..., description="Transition name (e.g., 'Start Progress')")
    to_status: str | None = Field(None, description="Status the issue reaches through this transition")
    fields: list[TransitionField] = Field(default_factory=list, description="Fields on the transition screen")
```

Add to `budjira/models/__init__.py`, following the existing export style in that file:

```python
from budjira.models.transition import Transition, TransitionField
```

and add `"Transition"` and `"TransitionField"` to its `__all__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/models/test_transition.py -v --no-cov`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add budjira/models/transition.py budjira/models/__init__.py tests/models/test_transition.py
git commit -m "feat(models): add transition screen field models"
```

---

### Task 2: Fetch transition screen metadata

**Files:**
- Modify: `budjira/services/transitions.py`
- Test: `tests/services/test_transitions.py`

**Interfaces:**
- Consumes: `Transition`, `TransitionField` from Task 1
- Produces: `TransitionService.get_transition_details(issue_key: str) -> list[Transition]`

Jira returns screen metadata under each transition's `fields` key when asked with
`expand=transitions.fields`. The raw shape is:

```json
{"id": "21", "name": "Resolve", "to": {"name": "Resolved"},
 "fields": {"resolution": {"required": true, "name": "Resolution",
                           "schema": {"type": "resolution"},
                           "allowedValues": [{"name": "Done"}, {"name": "Won't Do"}]}}}
```

`allowedValues` entries carry either `name` or `value` depending on field type; take
whichever is present.

- [ ] **Step 1: Write the failing test**

Append to `tests/services/test_transitions.py` (create the file with the module docstring
and imports below if it does not exist):

```python
def test_get_transition_details_requests_screen_fields(mock_jira: MagicMock) -> None:
    """The expand parameter is required, otherwise no field metadata comes back."""
    mock_jira.transitions.return_value = []
    service = TransitionService(mock_jira)

    service.get_transition_details("PROJ-123")

    mock_jira.transitions.assert_called_once_with("PROJ-123", expand="transitions.fields")


def test_get_transition_details_maps_screen_fields(mock_jira: MagicMock) -> None:
    """Raw Jira metadata is mapped into typed models."""
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


def test_get_transition_details_handles_transition_without_screen(mock_jira: MagicMock) -> None:
    """A transition with no screen has no fields, not an error."""
    mock_jira.transitions.return_value = [{"id": "11", "name": "Start Progress"}]
    service = TransitionService(mock_jira)

    transitions = service.get_transition_details("PROJ-123")

    assert transitions[0].fields == []
    assert transitions[0].to_status is None
```

If the test file does not exist yet, start it with:

```python
"""Tests for the transition service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from budjira.services.transitions import TransitionService
from jira import JIRA


@pytest.fixture
def mock_jira() -> MagicMock:
    """Mocked jira-python client."""
    return MagicMock(spec=JIRA)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_transitions.py -v --no-cov`
Expected: FAIL — `AttributeError: 'TransitionService' object has no attribute 'get_transition_details'`

- [ ] **Step 3: Write minimal implementation**

Add to `budjira/services/transitions.py`. Add `from budjira.models.transition import Transition, TransitionField`
to the imports, and `from typing import Any` if not already present.

```python
    def get_transition_details(self, issue_key: str) -> list[Transition]:
        """Get available transitions including their screen fields.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of transitions with typed screen field metadata

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch transition details", issue_key=issue_key)
            raw_transitions = self.client.transitions(issue_key, expand="transitions.fields")
            return [self._parse_transition(raw) for raw in raw_transitions]
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            self._handle_jira_error(e, "Fetch transition details", issue_key=issue_key)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching transition details: {e}") from e

    @staticmethod
    def _parse_transition(raw: dict[str, Any]) -> Transition:
        """Map one raw Jira transition dict into a Transition model."""
        fields = [
            TransitionField(
                field_id=field_id,
                name=meta.get("name", field_id),
                required=bool(meta.get("required", False)),
                field_type=(meta.get("schema") or {}).get("type"),
                allowed_values=TransitionService._parse_allowed_values(meta),
            )
            for field_id, meta in (raw.get("fields") or {}).items()
        ]
        return Transition(
            id=str(raw["id"]),
            name=raw["name"],
            to_status=(raw.get("to") or {}).get("name"),
            fields=fields,
        )

    @staticmethod
    def _parse_allowed_values(meta: dict[str, Any]) -> list[str] | None:
        """Extract allowed values; entries carry 'name' or 'value' depending on field type."""
        raw_values = meta.get("allowedValues")
        if not raw_values:
            return None
        values = [v.get("name") or v.get("value") for v in raw_values if isinstance(v, dict)]
        return [v for v in values if v] or None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_transitions.py -v --no-cov`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add budjira/services/transitions.py tests/services/test_transitions.py
git commit -m "feat(transitions): fetch transition screen field metadata"
```

---

### Task 3: Forward field values when transitioning

**Files:**
- Modify: `budjira/services/transitions.py:42` (the `transition` method)
- Test: `tests/services/test_transitions.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: `TransitionService.transition(issue_key: str, transition_name: str, fields: dict[str, Any] | None = None) -> None`

- [ ] **Step 1: Write the failing test**

```python
def test_transition_forwards_fields(mock_jira: MagicMock) -> None:
    """Screen field values must reach transition_issue."""
    mock_jira.transitions.return_value = [{"id": "21", "name": "Resolve"}]
    service = TransitionService(mock_jira)

    service.transition("TEST-123", "Resolve", fields={"resolution": {"name": "Done"}})

    mock_jira.transition_issue.assert_called_once_with("PROJ-123", "21", fields={"resolution": {"name": "Done"}})


def test_transition_without_fields_sends_none(mock_jira: MagicMock) -> None:
    """Existing behaviour is preserved when no fields are supplied."""
    mock_jira.transitions.return_value = [{"id": "11", "name": "Start Progress"}]
    service = TransitionService(mock_jira)

    service.transition("PROJ-123", "Start Progress")

    mock_jira.transition_issue.assert_called_once_with("PROJ-123", "11", fields=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_transitions.py -k transition_forwards -v --no-cov`
Expected: FAIL — `TypeError: transition() got an unexpected keyword argument 'fields'`

- [ ] **Step 3: Write minimal implementation**

In `budjira/services/transitions.py`, change the signature and the call. Replace

```python
    def transition(self, issue_key: str, transition_name: str) -> None:
```

with

```python
    def transition(self, issue_key: str, transition_name: str, fields: dict[str, Any] | None = None) -> None:
```

extend the docstring's Args with

```
            fields: Optional transition screen field values, keyed by Jira field id
```

and replace

```python
            self.client.transition_issue(issue_key, transition_id)
```

with

```python
            self.client.transition_issue(issue_key, transition_id, fields=fields)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_transitions.py -v --no-cov`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add budjira/services/transitions.py tests/services/test_transitions.py
git commit -m "feat(transitions): forward screen field values to transition_issue"
```

---

### Task 4: Parse, resolve and encode field arguments

**Files:**
- Create: `budjira/utils/transition_fields.py`
- Test: `tests/utils/test_transition_fields.py`

**Interfaces:**
- Consumes: `Transition`, `TransitionField` from Task 1
- Produces:
  - `parse_field_args(field_args: list[str] | None) -> dict[str, str]`
  - `resolve_fields(raw_fields: dict[str, str], transition: Transition) -> dict[str, Any]`
  - `missing_required_fields(resolved: dict[str, Any], transition: Transition) -> list[TransitionField]`
  - `format_field_requirements(fields: list[TransitionField]) -> str`
  - `encode_field_value(field: TransitionField, value: str) -> Any`

`encode_field_value` exists because Jira rejects a plain string for structured
fields. Coverage in this slice: `array` → `[{"value": v}]`; `option` → `{"value": v}`;
`resolution` and `priority` → `{"name": v}`; everything else → the plain string.
Other structured types (user, version, …) are out of scope and will surface as a
Jira error rather than being silently mangled.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for transition field parsing, resolution and encoding."""

from __future__ import annotations

import pytest
from budjira.models.transition import Transition, TransitionField
from budjira.utils.errors import ValidationError
from budjira.utils.transition_fields import (
    encode_field_value,
    format_field_requirements,
    missing_required_fields,
    parse_field_args,
    resolve_fields,
)


@pytest.fixture
def transition() -> Transition:
    """A transition with one required option field and one optional text field."""
    return Transition(
        id="21",
        name="Resolve",
        to_status="Resolved",
        fields=[
            TransitionField(
                field_id="resolution",
                name="Resolution",
                required=True,
                field_type="resolution",
                allowed_values=["Done", "Won't Do"],
            ),
            TransitionField(
                field_id="customfield_10001",
                name="Solution details",
                required=False,
                field_type="string",
            ),
        ],
    )


class TestParseFieldArgs:
    """Test parsing of raw --field arguments."""

    def test_parses_key_value_pairs(self) -> None:
        assert parse_field_args(["resolution=Done"]) == {"resolution": "Done"}

    def test_keeps_equals_signs_in_the_value(self) -> None:
        assert parse_field_args(["customfield_10001=a=b"]) == {"customfield_10001": "a=b"}

    def test_none_yields_empty_mapping(self) -> None:
        assert parse_field_args(None) == {}

    def test_missing_equals_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="key=value"):
            parse_field_args(["resolution"])


class TestResolveFields:
    """Test resolution of user-supplied keys against screen metadata."""

    def test_resolves_by_field_id(self, transition: Transition) -> None:
        assert resolve_fields({"resolution": "Done"}, transition) == {"resolution": {"name": "Done"}}

    def test_resolves_by_display_name_case_insensitively(self, transition: Transition) -> None:
        resolved = resolve_fields({"solution DETAILS": "Rolled out"}, transition)

        assert resolved == {"customfield_10001": "Rolled out"}

    def test_optional_field_is_forwarded(self, transition: Transition) -> None:
        """Not only required fields are sent."""
        resolved = resolve_fields({"customfield_10001": "note"}, transition)

        assert "customfield_10001" in resolved

    def test_unknown_key_lists_available_fields(self, transition: Transition) -> None:
        with pytest.raises(ValidationError) as exc:
            resolve_fields({"nonsense": "x"}, transition)

        message = str(exc.value)
        assert "nonsense" in message
        assert "resolution" in message
        assert "Solution details" in message

    def test_ambiguous_name_names_the_candidates(self) -> None:
        ambiguous = Transition(
            id="21",
            name="Resolve",
            fields=[
                TransitionField(field_id="customfield_1", name="Notes", required=False),
                TransitionField(field_id="customfield_2", name="notes", required=False),
            ],
        )

        with pytest.raises(ValidationError, match="ambiguous"):
            resolve_fields({"notes": "x"}, ambiguous)

    def test_value_outside_allowed_values_is_rejected(self, transition: Transition) -> None:
        with pytest.raises(ValidationError) as exc:
            resolve_fields({"resolution": "Nope"}, transition)

        assert "Done" in str(exc.value)


class TestEncodeFieldValue:
    """Test per-type encoding of field values."""

    def test_string_stays_plain(self) -> None:
        field = TransitionField(field_id="customfield_1", name="Notes", required=False, field_type="string")

        assert encode_field_value(field, "hello") == "hello"

    def test_option_is_wrapped_in_value(self) -> None:
        field = TransitionField(field_id="customfield_1", name="Kind", required=False, field_type="option")

        assert encode_field_value(field, "A") == {"value": "A"}

    def test_array_is_wrapped_in_a_list(self) -> None:
        field = TransitionField(field_id="customfield_1", name="Tags", required=False, field_type="array")

        assert encode_field_value(field, "A") == [{"value": "A"}]

    def test_resolution_uses_name(self) -> None:
        field = TransitionField(field_id="resolution", name="Resolution", required=False, field_type="resolution")

        assert encode_field_value(field, "Done") == {"name": "Done"}

    def test_unknown_type_stays_plain(self) -> None:
        field = TransitionField(field_id="customfield_1", name="Odd", required=False, field_type=None)

        assert encode_field_value(field, "x") == "x"


class TestMissingRequiredFields:
    """Test detection of unsatisfied required fields."""

    def test_reports_unsatisfied_required_field(self, transition: Transition) -> None:
        missing = missing_required_fields({}, transition)

        assert [f.field_id for f in missing] == ["resolution"]

    def test_satisfied_required_field_is_not_reported(self, transition: Transition) -> None:
        missing = missing_required_fields({"resolution": {"name": "Done"}}, transition)

        assert missing == []

    def test_optional_field_is_never_reported(self, transition: Transition) -> None:
        missing = missing_required_fields({"resolution": {"name": "Done"}}, transition)

        assert all(f.field_id != "customfield_10001" for f in missing)


class TestFormatFieldRequirements:
    """Test the copy-pasteable requirement listing."""

    def test_lists_id_name_type_and_allowed_values(self, transition: Transition) -> None:
        text = format_field_requirements(transition.fields)

        assert "resolution" in text
        assert "Resolution" in text
        assert "Done" in text
        assert "--field" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/utils/test_transition_fields.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'budjira.utils.transition_fields'`

- [ ] **Step 3: Write minimal implementation**

Create `budjira/utils/transition_fields.py`:

```python
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
                f"Invalid field argument '{arg}'. Expected format: key=value "
                f"(e.g., --field resolution=Done)."
            )
        parsed[key.strip()] = value
    return parsed


def encode_field_value(field: TransitionField, value: str) -> Any:
    """Encode a raw string into the shape Jira expects for this field type.

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
    """Find the single screen field a user-supplied key refers to."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/utils/test_transition_fields.py -v --no-cov`
Expected: PASS (18 tests)

- [ ] **Step 5: Commit**

```bash
git add budjira/utils/transition_fields.py tests/utils/test_transition_fields.py
git commit -m "feat(transitions): resolve and encode transition screen field values"
```

---

### Task 5: Attribute validator failures to a field

**Files:**
- Modify: `budjira/utils/transition_fields.py`
- Test: `tests/utils/test_transition_fields.py`

**Interfaces:**
- Consumes: `Transition`, `TransitionField` from Task 1
- Produces: `attribute_validator_error(messages: list[str], transition: Transition) -> TransitionField | None`

A workflow validator returns `{"errorMessages": ["..."], "errors": {}}` — the empty
`errors` object is what distinguishes it from a normal field error. Matching is
case-insensitive and bidirectional: the message may contain the field name, or the
field name may appear as a fragment of the message.

- [ ] **Step 1: Write the failing test**

```python
class TestAttributeValidatorError:
    """Test mapping an anonymous validator message onto a screen field."""

    def test_matches_field_named_in_the_message(self, transition: Transition) -> None:
        field = attribute_validator_error(
            ["Provide details about the solution made available."], transition
        )

        assert field is not None
        assert field.field_id == "customfield_10001"

    def test_matching_ignores_case(self, transition: Transition) -> None:
        field = attribute_validator_error(["SOLUTION DETAILS must be set"], transition)

        assert field is not None
        assert field.field_id == "customfield_10001"

    def test_returns_none_when_nothing_matches(self, transition: Transition) -> None:
        assert attribute_validator_error(["Something else went wrong"], transition) is None

    def test_returns_none_for_no_messages(self, transition: Transition) -> None:
        assert attribute_validator_error([], transition) is None
```

Note: the first test matches because the message contains the words of the field name
"Solution details" — matching is on the field name appearing in the message,
case-insensitively.

Add `attribute_validator_error` to the imports at the top of the test file.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/utils/test_transition_fields.py -k Validator -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'attribute_validator_error'`

- [ ] **Step 3: Write minimal implementation**

Append to `budjira/utils/transition_fields.py`:

```python
def attribute_validator_error(messages: list[str], transition: Transition) -> TransitionField | None:
    """Find the screen field a workflow validator message refers to.

    Workflow validators report failures with an empty ``errors`` object, so the
    offending field is never named. Match the message text against the screen's
    field names instead of forwarding Jira's bare sentence.

    Args:
        messages: Jira's errorMessages entries
        transition: The transition that was attempted

    Returns:
        The matched field, or None when no field name appears in any message
    """
    for message in messages:
        lowered = message.lower()
        for field in transition.fields:
            if field.name.lower() in lowered:
                return field
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/utils/test_transition_fields.py -v --no-cov`
Expected: PASS — the first validator test fails if the message does not literally
contain the field name. If `test_matches_field_named_in_the_message` fails, change its
message to `"Provide Solution details about the solution made available."` — matching is
deliberately literal so it never invents a field.

- [ ] **Step 5: Commit**

```bash
git add budjira/utils/transition_fields.py tests/utils/test_transition_fields.py
git commit -m "feat(transitions): attribute workflow validator errors to a screen field"
```

---

### Task 6: Wire --field, --dry-run and prompting into the CLI

**Files:**
- Modify: `budjira/cli/issue.py` (the `update` command; the `--status` call site is at `budjira/cli/issue.py:163-169`)
- Test: `tests/cli/test_issue.py`

**Interfaces:**
- Consumes: `get_transition_details`, `transition(fields=...)`, and every helper from Tasks 4 and 5
- Produces: CLI behaviour only

New options on `issue update`: `--field` (repeatable), `--dry-run`, and
`--interactive/--no-interactive` (`-i/-n`, default `True`), matching `create`.

Prompting happens only when interactive **and** `sys.stdin.isatty()`. budjira is
driven by agents and CI, where `--no-interactive` is easy to forget and a prompt
would hang forever.

- [ ] **Step 1: Write the failing test**

`tests/cli/test_issue.py` has **no** shared client fixture: each test decorates itself
with `@patch("budjira.cli.issue.JiraClient")` and
`@patch("budjira.cli.issue.get_active_connection")`, and invokes the CLI as
`["-q", "issue", "update", "TEST-123", ...]`. Repeating that eight times would bury the
behaviour under setup, so add one fixture that performs exactly the same patching, then
write the new tests against it. Leave the existing decorated tests untouched.

Append to `tests/cli/test_issue.py`:

```python
@pytest.fixture
def mock_client():
    """Patched JiraClient for issue update tests (same patching the decorated tests do)."""
    from budjira.models.connection import Connection

    connection = Connection(
        name="test",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@example.com",
        project_key="TEST",
    )
    with (
        patch("budjira.cli.issue.JiraClient") as client_class,
        patch("budjira.cli.issue.get_active_connection", return_value=connection),
    ):
        client = MagicMock()
        client_class.from_connection.return_value = client
        yield client


def _transition_with_required_field() -> Transition:
    return Transition(
        id="21",
        name="Resolve",
        to_status="Resolved",
        fields=[
            TransitionField(
                field_id="customfield_10001",
                name="Solution details",
                required=True,
                field_type="string",
            )
        ],
    )


def test_field_without_status_is_a_usage_error(mock_client: MagicMock) -> None:
    """Screen fields only exist in the context of a transition."""
    result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--field", "resolution=Done"])

    assert result.exit_code == 1
    assert "--status" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_missing_required_field_non_interactive_lists_requirements(mock_client: MagicMock) -> None:
    """Without a TTY there is no prompt — abort with what is needed."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--no-interactive"])

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "Solution details" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_supplied_field_is_passed_to_the_transition(mock_client: MagicMock) -> None:
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=Rolled out",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 0
    mock_client.transitions.transition.assert_called_once_with(
        "TEST-123", "Resolve", fields={"customfield_10001": "Rolled out"}
    )


def test_dry_run_performs_no_transition(mock_client: MagicMock) -> None:
    """A dry run must never touch the issue."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    result = runner.invoke(
        app,
        ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--field", "customfield_10001=x", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Resolve" in result.stdout
    mock_client.transitions.transition.assert_not_called()


def test_dry_run_does_not_prompt_for_missing_fields(mock_client: MagicMock) -> None:
    """A dry run must not ask for values it will never send."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    with patch("typer.prompt") as mock_prompt:
        result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--dry-run"])

    assert result.exit_code == 0
    mock_prompt.assert_not_called()
    mock_client.transitions.transition.assert_not_called()


def test_missing_required_field_is_prompted_when_interactive(mock_client: MagicMock) -> None:
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    with (
        patch("budjira.cli.issue.sys.stdin.isatty", return_value=True),
        patch("typer.prompt", return_value="Rolled out"),
    ):
        result = runner.invoke(app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve"])

    assert result.exit_code == 0
    mock_client.transitions.transition.assert_called_once_with(
        "TEST-123", "Resolve", fields={"customfield_10001": "Rolled out"}
    )
```

Add to that file's imports (`pytest` is not imported there yet):

```python
import pytest
from budjira.models.transition import Transition, TransitionField
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/cli/test_issue.py -k "field or dry_run" -v --no-cov`
Expected: FAIL — `no such option: --field`

- [ ] **Step 3: Write minimal implementation**

`budjira/cli/issue.py` currently imports only `Annotated` from `typing` and already
imports `JiraClient`, `BudjiraError` and `console`. Extend the import block to:

```python
import sys
from typing import Annotated, Any

from budjira.models.transition import Transition
from budjira.utils.transition_fields import (
    attribute_validator_error,
    format_field_requirements,
    missing_required_fields,
    parse_field_args,
    resolve_fields,
)
```

`sys` is imported as a module (not `from sys import stdin`) because the tests patch
`budjira.cli.issue.sys.stdin.isatty`.

Add three options to the `update_issue` signature, after `status`:

```python
    field: Annotated[
        list[str] | None,
        typer.Option("--field", help="Transition screen field as key=value (repeatable)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the transition and its fields without performing it")
    ] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive/--no-interactive", "-i/-n", help="Prompt for missing required fields")
    ] = True,
```

Add this helper above `update_issue`:

```python
def _collect_transition_fields(
    client: JiraClient,
    issue_key: str,
    status: str,
    field_args: list[str] | None,
    interactive: bool,
    dry_run: bool,
) -> tuple[Transition, dict[str, Any]]:
    """Resolve screen field values for a transition, prompting when allowed.

    Args:
        client: Connected Jira client
        issue_key: Issue key
        status: Transition name requested with --status
        field_args: Raw --field arguments
        interactive: Whether prompting is permitted
        dry_run: Whether this is a dry run (never prompts)

    Returns:
        The matched transition and the resolved field values

    Raises:
        BudjiraError: If the transition is unknown or a required field is missing
    """
    transitions = client.transitions.get_transition_details(issue_key)
    matched = next((t for t in transitions if t.name.lower() == status.lower()), None)
    if matched is None:
        available = ", ".join(t.name for t in transitions) or "none"
        raise BudjiraError(f"Invalid transition '{status}' for {issue_key}. Available transitions: {available}")

    resolved = resolve_fields(parse_field_args(field_args), matched)

    missing = missing_required_fields(resolved, matched)
    if missing and not dry_run:
        if interactive and sys.stdin.isatty():
            for field_meta in missing:
                answer = typer.prompt(f"{field_meta.name} ({field_meta.field_id})")
                resolved.update(resolve_fields({field_meta.field_id: answer}, matched))
        else:
            raise BudjiraError(
                f"Transition '{matched.name}' requires field values that were not supplied:\n"
                f"{format_field_requirements(missing)}"
            )

    return matched, resolved
```

Replace the `if status:` block at `budjira/cli/issue.py:163-169` with:

```python
        if field and not status:
            console.print("[red]Error:[/red] --field requires --status; screen fields belong to a transition.")
            raise typer.Exit(1)

        if status:
            try:
                matched, resolved = _collect_transition_fields(
                    client, issue_key, status, field, interactive, dry_run
                )

                if dry_run:
                    console.print(f"[cyan]Dry run:[/cyan] would transition {issue_key} via '{matched.name}'")
                    if matched.to_status:
                        console.print(f"  Target status: {matched.to_status}")
                    for field_id, value in resolved.items():
                        console.print(f"  {field_id} = {value}")
                    still_missing = missing_required_fields(resolved, matched)
                    if still_missing:
                        console.print("[yellow]Missing required fields:[/yellow]")
                        console.print(format_field_requirements(still_missing))
                    return

                client.transitions.transition(issue_key, matched.name, fields=resolved or None)
                changes.append(("Status", f"→ {status}"))
            except BudjiraError as e:
                console.print(f"[red]✗[/red] Status update failed: {e}")
                raise typer.Exit(1) from e
```

Note `fields=resolved or None`: with no screen fields this sends `None`, preserving
the exact call shape the pre-existing tests assert.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/cli/test_issue.py -v --no-cov`
Expected: PASS, including the pre-existing `--status` tests

- [ ] **Step 5: Commit**

```bash
git add budjira/cli/issue.py tests/cli/test_issue.py
git commit -m "feat(issue): add --field and --dry-run for transition screen fields"
```

---

### Task 7: Name the field behind a validator failure in the CLI

**Files:**
- Modify: `budjira/cli/issue.py`
- Test: `tests/cli/test_issue.py`

**Interfaces:**
- Consumes: `attribute_validator_error` from Task 5
- Produces: CLI behaviour only

On failure the CLI inspects the underlying `JIRAError`'s response body. Retry exactly
once: a second failure means the attribution was wrong, and looping writes noise into
the issue history.

- [ ] **Step 1: Write the failing test**

```python
def _validator_error() -> JIRAError:
    error = JIRAError(status_code=400, text="Provide Solution details about the solution.")
    error.response = MagicMock()
    error.response.json.return_value = {
        "errorMessages": ["Provide Solution details about the solution."],
        "errors": {},
    }
    return error


def test_validator_failure_names_the_field(mock_client: MagicMock) -> None:
    """Jira's anonymous message is replaced by a concrete field name."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = _validator_error()
    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=x",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 1
    assert "customfield_10001" in result.stdout
    assert "Solution details" in result.stdout


def test_validator_failure_retries_once_when_interactive(mock_client: MagicMock) -> None:
    """After prompting, retry exactly once."""
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = [_validator_error(), None]
    with (
        patch("budjira.cli.issue.sys.stdin.isatty", return_value=True),
        patch("typer.prompt", return_value="Rolled out"),
    ):
        result = runner.invoke(
            app, ["-q", "issue", "update", "TEST-123", "--status", "Resolve", "--field", "customfield_10001=x"]
        )

    assert result.exit_code == 0
    assert mock_client.transitions.transition.call_count == 2


def test_unattributable_validator_message_is_forwarded(mock_client: MagicMock) -> None:
    """Never invent a field name."""
    error = JIRAError(status_code=400, text="Something else went wrong")
    error.response = MagicMock()
    error.response.json.return_value = {"errorMessages": ["Something else went wrong"], "errors": {}}
    mock_client.transitions.get_transition_details.return_value = [_transition_with_required_field()]
    mock_client.transitions.transition.side_effect = error
    result = runner.invoke(
        app,
        [
            "-q",
            "issue",
            "update",
            "TEST-123",
            "--status",
            "Resolve",
            "--field",
            "customfield_10001=x",
            "--no-interactive",
        ],
    )

    assert result.exit_code == 1
    assert "Something else went wrong" in result.stdout
```

Add `from jira.exceptions import JIRAError` to the test file's imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/cli/test_issue.py -k validator -v --no-cov`
Expected: FAIL — the raw Jira message is printed without the field name

- [ ] **Step 3: Write minimal implementation**

Add this helper to `budjira/cli/issue.py`:

```python
def _validator_messages(error: Exception) -> list[str]:
    """Extract errorMessages from a Jira error whose 'errors' object is empty.

    A populated 'errors' object means Jira already named the field, so there is
    nothing to attribute.

    Args:
        error: Exception raised while transitioning

    Returns:
        The anonymous validator messages, empty if this is not that case
    """
    response = getattr(error, "response", None)
    if response is None:
        return []
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - a non-JSON body simply carries no attribution
        return []
    if body.get("errors"):
        return []
    messages = body.get("errorMessages") or []
    return [str(m) for m in messages]
```

Replace the `client.transitions.transition(...)` call inside the `if status:` block with:

```python
                try:
                    client.transitions.transition(issue_key, matched.name, fields=resolved or None)
                except Exception as transition_error:
                    messages = _validator_messages(transition_error)
                    culprit = attribute_validator_error(messages, matched) if messages else None
                    if culprit is None:
                        raise

                    detail = f"'{culprit.name}' ({culprit.field_id})"
                    if not (interactive and sys.stdin.isatty()):
                        console.print(
                            f"[red]✗[/red] Transition '{matched.name}' was rejected by a workflow validator. "
                            f"The message refers to field {detail}. Supply it with:\n"
                            f"{format_field_requirements([culprit])}"
                        )
                        raise typer.Exit(1) from transition_error

                    console.print(f"[yellow]![/yellow] A workflow validator requires field {detail}.")
                    answer = typer.prompt(f"{culprit.name} ({culprit.field_id})")
                    resolved.update(resolve_fields({culprit.field_id: answer}, matched))
                    client.transitions.transition(issue_key, matched.name, fields=resolved)

                changes.append(("Status", f"→ {status}"))
```

The bare `raise` re-raises the original error so the existing `except BudjiraError`
handler and Jira's own message survive unchanged when nothing can be attributed.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/cli/test_issue.py -v --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add budjira/cli/issue.py tests/cli/test_issue.py
git commit -m "feat(issue): name the screen field behind a workflow validator failure"
```

---

### Task 8: Documentation and full quality gate

**Files:**
- Modify: `README.md`, `budjira/models/ai_prompt.py`, `.claude/ai-usage-prompt.md`, `.claude/context.md`

**Interfaces:**
- Consumes: the finished feature
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Document the feature in README.md**

In the issue-update section, add:

```markdown
**Transition screen fields**

Some transitions present a screen with fields that must be filled:

```bash
# Inspect what a transition needs, without touching the issue
budjira issue update PROJ-123 --status "Resolve" --dry-run

# Supply screen fields by id or display name
budjira issue update PROJ-123 --status "Resolve" \
    --field resolution=Done \
    --field "Solution details=Rolled out to production"
```

Missing required fields are prompted for interactively. With `--no-interactive`,
or when stdin is not a terminal, budjira aborts and lists exactly which fields
are needed instead of hanging on a prompt.
```

- [ ] **Step 2: Update the AI prompt template**

The prompt text lives in `budjira/models/ai_prompt.py` (not in `budjira/cli/ai.py`).
Find the issue-update section and add:

```markdown
### Transition Screen Fields

Some transitions require fields that only exist on the transition screen.

```bash
# See what a transition needs without performing it
budjira issue update PROJ-123 --status "Resolve" --dry-run

# Supply fields by id or by display name
budjira issue update PROJ-123 --status "Resolve" \
    --field resolution=Done \
    --field "Solution details=Rolled out"
```

Non-interactive callers (agents, CI) get an abort listing the required fields with
their ids, types and allowed values — never a hanging prompt. When a workflow
validator rejects the transition, budjira names the field the message refers to
instead of forwarding Jira's anonymous sentence.
```

- [ ] **Step 3: Regenerate the AI prompt**

```bash
uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md
```

- [ ] **Step 4: Update .claude/context.md**

Add the feature under implemented features and refresh the test statistics from the
output of the next step.

- [ ] **Step 5: Run the full quality gate**

```bash
uv run pytest --cov=budjira --cov-report=term-missing
uv run ruff check .
uv run mypy budjira
uv run pre-commit run --all-files
```

Expected: all pass, coverage ≥70% overall.

- [ ] **Step 6: Commit and open the pull request**

```bash
git add README.md budjira/models/ai_prompt.py .claude/ai-usage-prompt.md .claude/context.md
git commit -m "docs: document transition screen fields and dry-run"
git push -u origin fix/issue-101-transition-screen-fields
gh pr create --base master --title "feat(issue): transition screen fields and validator attribution" --body "Implements parts 2 and 3 of #101 plus --dry-run. Path finding (part 1) and ADF (part 4) remain open on the issue."
```

Do **not** close #101: parts 1 and 4 stay open. Reference the issue without a
closing keyword.

---

## Notes for the implementer

- Branch: `fix/issue-101-transition-screen-fields`, created from an up-to-date `master`.
- `budjira/models/__init__.py` and `budjira/services/__init__.py` follow an explicit
  export style; match it rather than adding bare imports.
- The pre-existing tests for `issue update --status` must keep passing untouched. If one
  breaks, the call shape changed — fix the implementation, not the test.
- `--no-cov` in the per-task commands avoids the 70% gate firing on a single test file.
  The full gate in Task 8 runs coverage properly.
