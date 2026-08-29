"""Workflow profile models for cross-instance Jira workflows."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ShadowTicketStrategy(str, Enum):
    """Strategy for resolving shadow tickets across instances."""

    SUMMARY_SEARCH = "summary"
    CUSTOM_FIELD = "custom_field"
    ISSUE_LINK = "issue_link"


class OverbookingPolicy(str, Enum):
    """Policy for handling overbooking (estimate exceeded)."""

    WARN = "warn"
    CONFIRM = "confirm"
    BLOCK = "block"


class ProjectMapping(BaseModel):
    """Maps a planning project to a booking project."""

    planning_project: str = Field(
        description="Planning instance project key (e.g., EK)",
        min_length=1,
    )
    booking_project: str = Field(
        description="Booking instance project key (e.g., K)",
        min_length=1,
    )


class BillingConfig(BaseModel):
    """Billing report configuration for a workflow profile.

    Maps issue labels to free-form billing buckets. Buckets are configuration,
    not code: every customer contract names them differently, and the report
    groups by whatever values are configured here.
    """

    categories: dict[str, str] = Field(
        default_factory=dict,
        description="Issue label -> billing bucket (e.g., {'analysis': 'billable', 'warranty': 'non-billable'})",
    )
    issue_categories: dict[str, str] = Field(
        default_factory=dict,
        description="Booking issue key -> billing bucket, for collective-ticket booking where the ticket "
        "itself is the category (e.g., {'ACME-101': 'billable'}). Wins over the label path, and named "
        "issues are in scope regardless of project mapping.",
    )
    require_exactly_one: bool = Field(
        default=True,
        description="Fail loudly when an issue carries more than one category label (Jira cannot enforce this)",
    )
    exclude_from_total: list[str] = Field(
        default_factory=lambda: ["project"],
        description="Buckets shown in the report but excluded from the grand total (e.g., fixed-fee work)",
    )
    chargeable_buckets: list[str] = Field(
        default_factory=lambda: ["billable"],
        description="Buckets that are actually charged to the customer — amounts and the money total "
        "cover only these. Invariant: no single currency figure may span buckets with different "
        "billing semantics, so non-chargeable buckets render hours-only even when a rate is set.",
    )
    rate: float | None = Field(
        default=None,
        description="Hourly rate for amount columns; absent or 0 produces an hours-only report",
    )
    currency: str = Field(
        default="EUR",
        description="Currency for amounts (display only, no conversion)",
    )


class WorkflowProfile(BaseModel):
    """A workflow profile defining cross-instance relationships."""

    name: str = Field(
        description="Unique name for this workflow profile",
        min_length=1,
    )
    planning_connection: str = Field(
        description="Connection name for the planning instance",
        min_length=1,
    )
    booking_connection: str = Field(
        description="Connection name for the booking instance",
        min_length=1,
    )
    project_mappings: list[ProjectMapping] = Field(
        default_factory=list,
        description="Project mappings from planning to booking",
    )
    shadow_strategy: ShadowTicketStrategy = Field(
        default=ShadowTicketStrategy.SUMMARY_SEARCH,
        description="Strategy for finding shadow tickets",
    )
    shadow_custom_field: str | None = Field(
        default=None,
        description="Custom field ID for shadow ticket lookup (only with custom_field strategy)",
    )
    overbooking_policy: OverbookingPolicy = Field(
        default=OverbookingPolicy.WARN,
        description="Policy when booking would exceed estimate",
    )
    billing: BillingConfig | None = Field(
        default=None,
        description="Billing report configuration (label -> bucket mapping, rate); None disables 'workflow billing'",
    )


class WorkflowProfileList(BaseModel):
    """List of all configured workflow profiles."""

    profiles: list[WorkflowProfile] = Field(
        default_factory=list,
        description="List of workflow profiles",
    )

    def find_by_name(self, name: str) -> WorkflowProfile | None:
        """Find profile by name.

        Args:
            name: Profile name to search for

        Returns:
            Profile if found, None otherwise
        """
        for profile in self.profiles:
            if profile.name == name:
                return profile
        return None

    def add(self, profile: WorkflowProfile) -> None:
        """Add a new profile.

        Args:
            profile: Profile to add

        Raises:
            ValueError: If profile with same name already exists
        """
        if self.find_by_name(profile.name):
            raise ValueError(
                f"Workflow profile '{profile.name}' already exists. "
                f"Use a different name or remove the existing profile first."
            )
        self.profiles.append(profile)

    def remove(self, name: str) -> bool:
        """Remove profile by name.

        Args:
            name: Name of profile to remove

        Returns:
            True if profile was removed, False if not found
        """
        profile = self.find_by_name(name)
        if profile:
            self.profiles.remove(profile)
            return True
        return False


class BookingStatus(BaseModel):
    """Status of time booking for a planning issue."""

    planning_issue_key: str = Field(
        description="Issue key in the planning instance (e.g., EK-123)",
    )
    planning_summary: str = Field(
        description="Summary of the planning issue",
    )
    booking_issue_key: str | None = Field(
        default=None,
        description="Issue key in the booking instance (None if shadow not found)",
    )
    estimate_seconds: int | None = Field(
        default=None,
        description="Original estimate from planning issue (seconds)",
    )
    spent_seconds: int = Field(
        default=0,
        description="Total time spent on booking issue (seconds)",
    )
    remaining_seconds: int | None = Field(
        default=None,
        description="Remaining time (estimate - spent), None if no estimate",
    )
    is_overbooked: bool = Field(
        default=False,
        description="Whether spent exceeds estimate",
    )
    overbooking_seconds: int = Field(
        default=0,
        description="Amount over estimate (0 if not overbooked)",
    )
