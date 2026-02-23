"""Tests for workflow models."""

import pytest
from budjira.models.workflow import (
    BookingStatus,
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
    WorkflowProfileList,
)
from pydantic import ValidationError


class TestShadowTicketStrategy:
    """Test ShadowTicketStrategy enum."""

    def test_summary_search(self) -> None:
        assert ShadowTicketStrategy.SUMMARY_SEARCH.value == "summary"

    def test_custom_field(self) -> None:
        assert ShadowTicketStrategy.CUSTOM_FIELD.value == "custom_field"

    def test_issue_link(self) -> None:
        assert ShadowTicketStrategy.ISSUE_LINK.value == "issue_link"


class TestOverbookingPolicy:
    """Test OverbookingPolicy enum."""

    def test_warn(self) -> None:
        assert OverbookingPolicy.WARN.value == "warn"

    def test_confirm(self) -> None:
        assert OverbookingPolicy.CONFIRM.value == "confirm"

    def test_block(self) -> None:
        assert OverbookingPolicy.BLOCK.value == "block"


class TestProjectMapping:
    """Test ProjectMapping model."""

    def test_valid_mapping(self) -> None:
        mapping = ProjectMapping(planning_project="EK", booking_project="K")
        assert mapping.planning_project == "EK"
        assert mapping.booking_project == "K"

    def test_empty_planning_project_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectMapping(planning_project="", booking_project="K")

    def test_empty_booking_project_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectMapping(planning_project="EK", booking_project="")

    def test_serialization(self) -> None:
        mapping = ProjectMapping(planning_project="EK", booking_project="K")
        data = mapping.model_dump()
        assert data == {"planning_project": "EK", "booking_project": "K"}


class TestWorkflowProfile:
    """Test WorkflowProfile model."""

    def test_full_profile(self) -> None:
        profile = WorkflowProfile(
            name="ek-to-k",
            planning_connection="ek-planning",
            booking_connection="k-booking",
            project_mappings=[
                ProjectMapping(planning_project="EK", booking_project="K"),
            ],
            shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH,
            overbooking_policy=OverbookingPolicy.WARN,
        )
        assert profile.name == "ek-to-k"
        assert profile.planning_connection == "ek-planning"
        assert profile.booking_connection == "k-booking"
        assert len(profile.project_mappings) == 1
        assert profile.shadow_strategy == ShadowTicketStrategy.SUMMARY_SEARCH
        assert profile.shadow_custom_field is None
        assert profile.overbooking_policy == OverbookingPolicy.WARN

    def test_defaults(self) -> None:
        profile = WorkflowProfile(
            name="test",
            planning_connection="plan",
            booking_connection="book",
        )
        assert profile.project_mappings == []
        assert profile.shadow_strategy == ShadowTicketStrategy.SUMMARY_SEARCH
        assert profile.shadow_custom_field is None
        assert profile.overbooking_policy == OverbookingPolicy.WARN

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowProfile(
                name="",
                planning_connection="plan",
                booking_connection="book",
            )

    def test_custom_field_strategy(self) -> None:
        profile = WorkflowProfile(
            name="test",
            planning_connection="plan",
            booking_connection="book",
            shadow_strategy=ShadowTicketStrategy.CUSTOM_FIELD,
            shadow_custom_field="customfield_10001",
        )
        assert profile.shadow_strategy == ShadowTicketStrategy.CUSTOM_FIELD
        assert profile.shadow_custom_field == "customfield_10001"

    def test_serialization(self) -> None:
        profile = WorkflowProfile(
            name="test",
            planning_connection="plan",
            booking_connection="book",
            project_mappings=[
                ProjectMapping(planning_project="EK", booking_project="K"),
            ],
        )
        data = profile.model_dump()
        assert data["name"] == "test"
        assert data["planning_connection"] == "plan"
        assert data["booking_connection"] == "book"
        assert len(data["project_mappings"]) == 1
        assert data["shadow_strategy"] == "summary"
        assert data["overbooking_policy"] == "warn"


class TestWorkflowProfileList:
    """Test WorkflowProfileList model."""

    def _make_profile(self, name: str = "test") -> WorkflowProfile:
        return WorkflowProfile(
            name=name,
            planning_connection="plan",
            booking_connection="book",
        )

    def test_empty_list(self) -> None:
        profiles = WorkflowProfileList()
        assert profiles.profiles == []

    def test_find_by_name_found(self) -> None:
        profile = self._make_profile("my-profile")
        profiles = WorkflowProfileList(profiles=[profile])
        assert profiles.find_by_name("my-profile") == profile

    def test_find_by_name_not_found(self) -> None:
        profiles = WorkflowProfileList()
        assert profiles.find_by_name("nonexistent") is None

    def test_add_profile(self) -> None:
        profiles = WorkflowProfileList()
        profile = self._make_profile()
        profiles.add(profile)
        assert len(profiles.profiles) == 1
        assert profiles.profiles[0] == profile

    def test_add_duplicate_raises(self) -> None:
        profiles = WorkflowProfileList()
        profiles.add(self._make_profile("dup"))
        with pytest.raises(ValueError, match="already exists"):
            profiles.add(self._make_profile("dup"))

    def test_remove_existing(self) -> None:
        profiles = WorkflowProfileList()
        profiles.add(self._make_profile("to-remove"))
        assert profiles.remove("to-remove") is True
        assert len(profiles.profiles) == 0

    def test_remove_nonexistent(self) -> None:
        profiles = WorkflowProfileList()
        assert profiles.remove("nonexistent") is False


class TestBookingStatus:
    """Test BookingStatus model."""

    def test_full_status(self) -> None:
        status = BookingStatus(
            planning_issue_key="EK-123",
            planning_summary="Fix login bug",
            booking_issue_key="K-456",
            estimate_seconds=28800,
            spent_seconds=19800,
            remaining_seconds=9000,
            is_overbooked=False,
            overbooking_seconds=0,
        )
        assert status.planning_issue_key == "EK-123"
        assert status.planning_summary == "Fix login bug"
        assert status.booking_issue_key == "K-456"
        assert status.estimate_seconds == 28800
        assert status.spent_seconds == 19800
        assert status.remaining_seconds == 9000
        assert status.is_overbooked is False
        assert status.overbooking_seconds == 0

    def test_no_shadow(self) -> None:
        status = BookingStatus(
            planning_issue_key="EK-123",
            planning_summary="Fix login bug",
            booking_issue_key=None,
        )
        assert status.booking_issue_key is None
        assert status.estimate_seconds is None
        assert status.spent_seconds == 0

    def test_overbooked(self) -> None:
        status = BookingStatus(
            planning_issue_key="EK-123",
            planning_summary="Over budget",
            booking_issue_key="K-456",
            estimate_seconds=28800,
            spent_seconds=36000,
            remaining_seconds=0,
            is_overbooked=True,
            overbooking_seconds=7200,
        )
        assert status.is_overbooked is True
        assert status.overbooking_seconds == 7200

    def test_defaults(self) -> None:
        status = BookingStatus(
            planning_issue_key="EK-1",
            planning_summary="Test",
        )
        assert status.booking_issue_key is None
        assert status.estimate_seconds is None
        assert status.spent_seconds == 0
        assert status.remaining_seconds is None
        assert status.is_overbooked is False
        assert status.overbooking_seconds == 0
