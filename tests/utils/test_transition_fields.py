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
