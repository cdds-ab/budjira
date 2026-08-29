"""Tests for billing models (#117)."""

from datetime import date

from budjira.models.billing import (
    UNCATEGORISED_BUCKET,
    BillingGroup,
    BillingLine,
    BillingReport,
    BillingValidation,
    BillingViolation,
)
from budjira.models.workflow import BillingConfig, WorkflowProfile


class TestBillingConfig:
    """Tests for BillingConfig defaults and parsing."""

    def test_defaults(self) -> None:
        """Buckets are free-form; require_exactly_one and the project exclusion are on by default."""
        config = BillingConfig(categories={"analysis": "billable"})

        assert config.require_exactly_one is True
        assert config.exclude_from_total == ["project"]
        assert config.rate is None
        assert config.currency == "EUR"

    def test_full_config(self) -> None:
        """All fields are configurable."""
        config = BillingConfig(
            categories={"analysis": "billable", "warranty": "non-billable"},
            require_exactly_one=False,
            exclude_from_total=["project", "internal"],
            rate=120.0,
            currency="USD",
        )

        assert config.categories["warranty"] == "non-billable"
        assert config.require_exactly_one is False
        assert config.exclude_from_total == ["project", "internal"]
        assert config.rate == 120.0
        assert config.currency == "USD"


class TestWorkflowProfileBilling:
    """Tests for the optional billing block on WorkflowProfile."""

    def test_profile_without_billing(self) -> None:
        """Existing profiles without a billing block load unchanged (migration tolerance)."""
        profile = WorkflowProfile(name="x", planning_connection="a", booking_connection="b")

        assert profile.billing is None
        assert "billing" not in profile.model_dump(exclude_none=True)

    def test_profile_with_billing(self) -> None:
        """A billing block parses from a plain dict (as TOML delivers it)."""
        profile = WorkflowProfile(
            name="x",
            planning_connection="a",
            booking_connection="b",
            billing={"categories": {"analysis": "billable"}, "rate": 0},
        )

        assert profile.billing is not None
        assert profile.billing.categories == {"analysis": "billable"}
        assert profile.billing.rate == 0.0

    def test_billing_toml_roundtrip(self) -> None:
        """A profile with billing survives a TOML save/load roundtrip."""
        import tomli_w

        from budjira.config.settings import tomllib
        from budjira.models.workflow import WorkflowProfileList

        profiles = WorkflowProfileList(
            profiles=[
                WorkflowProfile(
                    name="x",
                    planning_connection="a",
                    booking_connection="b",
                    billing=BillingConfig(categories={"analysis": "billable", "warranty": "non-billable"}, rate=95.0),
                )
            ]
        )
        data = tomllib.loads(tomli_w.dumps(profiles.model_dump(exclude_none=True)))
        loaded = WorkflowProfileList(**data)

        assert loaded.profiles[0].billing is not None
        assert loaded.profiles[0].billing.categories == {"analysis": "billable", "warranty": "non-billable"}
        assert loaded.profiles[0].billing.rate == 95.0


class TestBillingReportModels:
    """Tests for the report model structures."""

    def test_line_derived_fields(self) -> None:
        """BillingLine carries seconds, hours and amount."""
        line = BillingLine(
            issue="EK-1",
            booking_issue="K-9",
            category="analysis",
            bucket="billable",
            summary="Analysis",
            seconds=5400,
            hours=1.5,
            amount=142.5,
        )

        assert line.hours == 1.5
        assert line.amount == 142.5

    def test_report_json_serialization(self) -> None:
        """A report serializes deterministically for --format json consumers."""
        report = BillingReport(
            profile="ek-to-k",
            period_from=date(2026, 8, 1),
            period_to=date(2026, 8, 31),
            rate=95.0,
            groups=[
                BillingGroup(
                    name="billable",
                    bucket="billable",
                    lines=[
                        BillingLine(
                            issue="EK-1",
                            booking_issue="K-9",
                            category="analysis",
                            bucket="billable",
                            summary="Analysis",
                            seconds=7200,
                            hours=2.0,
                            amount=190.0,
                        )
                    ],
                    total_seconds=7200,
                    total_hours=2.0,
                    total_amount=190.0,
                )
            ],
        )

        data = report.model_dump(mode="json")

        assert data["profile"] == "ek-to-k"
        assert data["period_from"] == "2026-08-01"
        assert data["period_to"] == "2026-08-31"
        assert data["grouped_by"] == "bucket"
        assert data["groups"][0]["lines"][0]["issue"] == "EK-1"
        assert data["groups"][0]["lines"][0]["amount"] == 190.0
        assert data["totals"] == {"seconds": 0, "hours": 0.0, "amount": None}
        assert data["warnings"] == []

    def test_hours_only_report_has_no_amounts(self) -> None:
        """Without a rate the report carries no amount fields."""
        report = BillingReport(profile="x", period_from=date(2026, 8, 1), period_to=date(2026, 8, 31))

        assert report.rate is None
        assert report.totals.amount is None

    def test_uncategorised_bucket_constant(self) -> None:
        """The uncategorised bucket name is stable (it is part of the JSON contract)."""
        assert UNCATEGORISED_BUCKET == "uncategorised"


class TestBillingValidationModel:
    """Tests for the --validate result model."""

    def test_violations(self) -> None:
        """Violations carry issue, kind, labels and summary."""
        validation = BillingValidation(
            profile="x",
            issues_checked=3,
            violations=[
                BillingViolation(issue="EK-1", kind="missing", summary="No label"),
                BillingViolation(issue="EK-2", kind="multiple", labels=["analysis", "support"], summary="Two labels"),
            ],
        )

        data = validation.model_dump(mode="json")
        assert data["issues_checked"] == 3
        assert data["violations"][0]["kind"] == "missing"
        assert data["violations"][0]["labels"] == []
        assert data["violations"][1]["labels"] == ["analysis", "support"]
        assert data["truncated"] is False
