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


class TestCollectiveProfile:
    """Collective strategy: standing booking targets instead of per-issue shadows (#131)."""

    def _profile(self, **overrides: object) -> WorkflowProfile:
        base: dict[str, object] = {
            "name": "acme-shadow",
            "planning_connection": "acme-planning",
            "booking_connection": "acme-booking",
            "project_mappings": [ProjectMapping(planning_project="PLAN", booking_project="BOOK")],
            "shadow_strategy": ShadowTicketStrategy.COLLECTIVE,
            "booking_targets": {"dev": "BOOK-101", "ops": "BOOK-102"},
            "mirror_target": "dev",
            "direct_booking_prefixes": ["MEETING:", "KT:"],
            "daily_cap": "8h",
            "weekdays_only": True,
        }
        base.update(overrides)
        return WorkflowProfile(**base)  # type: ignore[arg-type]

    def test_strategy_value(self) -> None:
        assert ShadowTicketStrategy.COLLECTIVE.value == "collective"

    def test_valid_profile(self) -> None:
        profile = self._profile()
        assert profile.mirror_issue_key == "BOOK-101"
        assert profile.daily_cap_seconds == 8 * 3600
        assert profile.mirror_comment_template == "{date}: {text}"

    def test_requires_booking_targets(self) -> None:
        with pytest.raises(ValidationError, match="booking_targets"):
            self._profile(booking_targets={})

    def test_mirror_target_must_be_a_target(self) -> None:
        with pytest.raises(ValidationError, match="mirror_target"):
            self._profile(mirror_target="qa")

    def test_mirror_target_requires_collective_strategy(self) -> None:
        with pytest.raises(ValidationError, match="collective"):
            self._profile(shadow_strategy=ShadowTicketStrategy.SUMMARY_SEARCH, booking_targets={})

    def test_invalid_daily_cap_rejected(self) -> None:
        with pytest.raises(ValidationError, match="daily_cap"):
            self._profile(daily_cap="soon")

    def test_target_lookup_by_issue_is_case_insensitive(self) -> None:
        profile = self._profile()
        assert profile.target_for_issue("BOOK-102") == "ops"
        assert profile.target_for_issue("book-101") == "dev"
        assert profile.target_for_issue("BOOK-999") is None

    def test_defaults_on_summary_profile(self) -> None:
        profile = WorkflowProfile(
            name="ek-to-k",
            planning_connection="ek",
            booking_connection="k",
            project_mappings=[ProjectMapping(planning_project="EK", booking_project="K")],
        )
        assert profile.booking_targets == {}
        assert profile.mirror_target is None
        assert profile.mirror_issue_key is None
        assert profile.daily_cap_seconds is None
        assert profile.weekdays_only is False
        assert profile.direct_booking_prefixes == []

    def test_roundtrip_through_profile_list(self) -> None:
        data = WorkflowProfileList(profiles=[self._profile()]).model_dump()
        loaded = WorkflowProfileList(**data)
        assert loaded.profiles[0].booking_targets == {"dev": "BOOK-101", "ops": "BOOK-102"}
        assert loaded.profiles[0].shadow_strategy == ShadowTicketStrategy.COLLECTIVE
