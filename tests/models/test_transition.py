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
            # The ignore below is deliberate: omitting 'required' is exactly what
            # this test exercises, and mypy flags the call it is meant to make.
            TransitionField(field_id="customfield_10001", name="Solution details")  # type: ignore[call-arg]


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
