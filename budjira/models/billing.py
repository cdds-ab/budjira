"""Billing report models for workflow profiles.

Deterministic, JSON-serializable report structures produced by
``WorkflowService.get_billing_report`` — consumed both by the Rich table
renderer and by the global ``--format json`` output.
"""

from datetime import date

from pydantic import BaseModel, Field

# Bucket for lines whose issue carries no configured category label (or whose
# shadow ticket could not be resolved back to a planning issue).
UNCATEGORISED_BUCKET = "uncategorised"


class BillingLine(BaseModel):
    """One booked issue within a billing report."""

    issue: str = Field(
        description="Planning issue key (equals the booking key when the shadow could not be resolved)",
    )
    booking_issue: str = Field(
        description="Issue key in the booking instance the worklogs were booked on",
    )
    category: str | None = Field(
        default=None,
        description="Category label that determined the bucket (None when uncategorised)",
    )
    bucket: str = Field(
        description="Billing bucket this line is grouped under",
    )
    summary: str = Field(
        default="",
        description="Planning issue summary",
    )
    seconds: int = Field(
        description="Booked time in the report period (seconds)",
    )
    hours: float = Field(
        description="Booked time in hours (seconds / 3600, 2 decimals)",
    )
    amount: float | None = Field(
        default=None,
        description="hours * rate when the profile configures a rate, else None",
    )


class BillingGroup(BaseModel):
    """A group of billing lines (by bucket or by category, depending on --group)."""

    name: str = Field(
        description="Group name (bucket or category label)",
    )
    bucket: str = Field(
        description="Bucket the group belongs to (equals name when grouped by bucket)",
    )
    lines: list[BillingLine] = Field(
        default_factory=list,
        description="Lines in this group, sorted by issue key",
    )
    total_seconds: int = Field(
        default=0,
        description="Sum of line seconds",
    )
    total_hours: float = Field(
        default=0.0,
        description="Sum of line hours (2 decimals)",
    )
    total_amount: float | None = Field(
        default=None,
        description="Sum of line amounts when a rate is configured, else None",
    )


class BillingTotals(BaseModel):
    """Grand totals over all non-excluded buckets."""

    seconds: int = 0
    hours: float = 0.0
    amount: float | None = None


class BillingReport(BaseModel):
    """A billing report over a period for a workflow profile."""

    profile: str = Field(
        description="Workflow profile name",
    )
    period_from: date = Field(
        description="First day of the report period (inclusive)",
    )
    period_to: date = Field(
        description="Last day of the report period (inclusive)",
    )
    rate: float | None = Field(
        default=None,
        description="Configured hourly rate (None or 0 => hours-only report)",
    )
    currency: str = Field(
        default="EUR",
        description="Currency for amounts",
    )
    grouped_by: str = Field(
        default="bucket",
        description="Grouping applied to the lines (bucket or category)",
    )
    groups: list[BillingGroup] = Field(
        default_factory=list,
        description="Groups with lines; 'uncategorised' sorts last",
    )
    excluded_from_total: list[str] = Field(
        default_factory=list,
        description="Buckets excluded from the grand total",
    )
    totals: BillingTotals = Field(
        default_factory=BillingTotals,
        description="Grand totals over non-excluded buckets",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues found while building the report (e.g., unresolvable shadow tickets)",
    )


class BillingViolation(BaseModel):
    """A label-hygiene violation found by 'workflow billing --validate'."""

    issue: str = Field(
        description="Planning issue key",
    )
    kind: str = Field(
        description="Violation kind: 'missing' (no category label) or 'multiple' (more than one)",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Category labels found on the issue (empty for 'missing')",
    )
    summary: str = Field(
        default="",
        description="Issue summary",
    )


class BillingValidation(BaseModel):
    """Result of 'workflow billing --validate'."""

    profile: str = Field(
        description="Workflow profile name",
    )
    issues_checked: int = Field(
        default=0,
        description="Number of planning issues inspected",
    )
    violations: list[BillingViolation] = Field(
        default_factory=list,
        description="Issues with missing or ambiguous category labels",
    )
    truncated: bool = Field(
        default=False,
        description="True when a planning project has more issues than the fetch limit",
    )
