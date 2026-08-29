"""Workflow service for cross-instance Jira operations."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console

from budjira.config.credentials import CredentialStore
from budjira.config.settings import get_settings
from budjira.core.jira_client import JiraClient
from budjira.models.billing import (
    UNCATEGORISED_BUCKET,
    BillingGroup,
    BillingLine,
    BillingReport,
    BillingTotals,
    BillingValidation,
    BillingViolation,
)
from budjira.models.workflow import (
    BillingConfig,
    BookingStatus,
    OverbookingPolicy,
    ShadowTicketStrategy,
    WorkflowProfile,
)
from budjira.tempo.client import TempoClient
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import (
    AuthenticationError,
    BillingValidationError,
    ConnectionError,
    JiraAPIError,
    OverbookingError,
    ShadowTicketAmbiguousError,
    ShadowTicketNotFoundError,
    ValidationError,
    WorkflowConfigError,
)
from budjira.utils.time_parser import parse_time_string

if TYPE_CHECKING:
    from budjira.tempo.models import TempoWorklog

logger = logging.getLogger(__name__)
console = Console()

# Tempo API hard cap per request; billing pages through results at this size.
_BILLING_PAGE_LIMIT = 1000

# Jira search single-page cap for batch fetches (issues per planning project / batch).
_BILLING_SEARCH_LIMIT = 1000


class WorkflowService:
    """Coordinates cross-instance workflow operations.

    This service manages workflows between a planning Jira instance and a
    booking Jira instance with Tempo integration. It handles shadow ticket
    resolution, booking status checks, and time logging with overbooking protection.
    """

    def __init__(
        self,
        profile: WorkflowProfile,
        planning_jira: JiraClient,
        booking_jira: JiraClient,
        tempo_client: TempoClient,
    ) -> None:
        """Initialize workflow service.

        Args:
            profile: Workflow profile configuration
            planning_jira: Jira client for the planning instance
            booking_jira: Jira client for the booking instance
            tempo_client: Tempo client for the booking instance
        """
        self.profile = profile
        self.planning_jira = planning_jira
        self.booking_jira = booking_jira
        self.tempo_client = tempo_client

    @classmethod
    def from_profile(cls, profile_name: str) -> WorkflowService:
        """Create WorkflowService from a saved profile.

        Args:
            profile_name: Name of the workflow profile

        Returns:
            Initialized WorkflowService

        Raises:
            WorkflowConfigError: If profile not found or connections invalid
            AuthenticationError: If credentials missing
            ConnectionError: If Tempo not enabled on booking connection
        """
        settings = get_settings()
        profile = settings.workflows.find_by_name(profile_name)
        if not profile:
            available = ", ".join(p.name for p in settings.workflows.profiles)
            raise WorkflowConfigError(
                f"Workflow profile '{profile_name}' not found. Available profiles: {available or '(none)'}"
            )

        # Resolve planning connection
        planning_conn = get_active_connection(profile.planning_connection)
        planning_jira = JiraClient.from_connection(planning_conn)

        # Resolve booking connection
        booking_conn = get_active_connection(profile.booking_connection)
        if not booking_conn.tempo_enabled:
            raise ConnectionError(
                f"Tempo is not enabled for booking connection '{booking_conn.name}'. "
                f"Run 'budjira connect tempo-setup' to configure Tempo integration."
            )

        booking_jira = JiraClient.from_connection(booking_conn)

        # Create Tempo client for booking connection
        cred_store = CredentialStore()
        tempo_token = cred_store.get_credential(booking_conn.get_tempo_credential_key())
        if not tempo_token:
            raise AuthenticationError(
                f"Tempo token not found for connection '{booking_conn.name}'. "
                f"Run 'budjira connect tempo-setup' to configure your Tempo API token."
            )
        tempo_client = TempoClient(tempo_token=tempo_token)

        return cls(profile, planning_jira, booking_jira, tempo_client)

    def _get_booking_project(self, planning_project: str) -> str:
        """Look up booking project for a planning project.

        Args:
            planning_project: Planning project key (e.g., EK)

        Returns:
            Booking project key (e.g., K)

        Raises:
            WorkflowConfigError: If no mapping found
        """
        for mapping in self.profile.project_mappings:
            if mapping.planning_project == planning_project:
                return mapping.booking_project

        available = ", ".join(f"{m.planning_project} -> {m.booking_project}" for m in self.profile.project_mappings)
        raise WorkflowConfigError(
            f"No project mapping found for planning project '{planning_project}'. "
            f"Configured mappings: {available or '(none)'}"
        )

    def _get_booking_issue_id(self, shadow_key: str) -> int:
        """Fetch the internal Jira issue ID from the booking instance.

        Validates the response to ensure we got the expected issue.

        Args:
            shadow_key: Issue key on the booking instance (e.g., K-456)

        Returns:
            Internal numeric Jira issue ID

        Raises:
            JiraAPIError: If the issue cannot be fetched
        """
        shadow_issue = self.booking_jira.client.issue(shadow_key)
        shadow_issue_id = int(shadow_issue.id)
        if hasattr(shadow_issue, "key") and shadow_issue.key != shadow_key:
            logger.warning(
                "Requested %s but got %s (ID: %d) from %s",
                shadow_key,
                shadow_issue.key,
                shadow_issue_id,
                self.booking_jira.connection.url,
            )
        logger.debug(
            "Resolved %s → internal ID %d on %s",
            shadow_key,
            shadow_issue_id,
            self.booking_jira.connection.url,
        )
        return shadow_issue_id

    def resolve_shadow_ticket(self, planning_issue_key: str) -> str:
        """Find the shadow ticket in the booking instance.

        Uses the configured shadow strategy to find the corresponding
        ticket in the booking instance.

        Args:
            planning_issue_key: Issue key in planning instance (e.g., EK-123)

        Returns:
            Issue key in booking instance (e.g., K-456)

        Raises:
            ShadowTicketNotFoundError: If no shadow ticket found
            ShadowTicketAmbiguousError: If multiple matches found
            WorkflowConfigError: If no project mapping exists
        """
        # Extract project key from issue key
        parts = planning_issue_key.split("-")
        if len(parts) < 2:
            raise ShadowTicketNotFoundError(
                f"Invalid issue key format: '{planning_issue_key}'. Expected format: PROJECT-123"
            )
        planning_project = parts[0]

        # Look up booking project
        booking_project = self._get_booking_project(planning_project)

        # Use JQL summary search (default strategy)
        jql = f'project = {booking_project} AND summary ~ "{planning_issue_key}"'
        logger.info(f"Searching for shadow ticket: {jql}")

        results = self.booking_jira.search_issues(jql, max_results=10)

        if len(results) == 0:
            raise ShadowTicketNotFoundError(
                f"Shadow ticket not found for {planning_issue_key} in project {booking_project}. "
                f"The shadow ticket may not have been synced yet. "
                f"Create it manually or wait for sync, then try again."
            )

        if len(results) > 1:
            matches = ", ".join(r.key for r in results)
            raise ShadowTicketAmbiguousError(
                f"Multiple shadow tickets found for {planning_issue_key} in project {booking_project}: {matches}. "
                f"Please resolve the ambiguity manually."
            )

        shadow_key = results[0].key
        logger.info(f"Resolved shadow ticket: {planning_issue_key} -> {shadow_key}")
        return shadow_key

    def get_booking_status(self, planning_issue_key: str) -> BookingStatus:
        """Get booking status for a planning issue.

        Fetches the estimate from the planning instance and the spent time
        from the booking instance (via Tempo).

        Args:
            planning_issue_key: Issue key in planning instance

        Returns:
            BookingStatus with estimate, spent, remaining info

        Raises:
            ShadowTicketNotFoundError: If shadow ticket not found
            ShadowTicketAmbiguousError: If multiple shadows found
        """
        # Fetch planning issue for estimate and summary
        planning_issue = self.planning_jira.get_issue(planning_issue_key)
        estimate_seconds = planning_issue.time_original_estimate
        planning_summary = planning_issue.summary

        # Resolve shadow ticket
        try:
            shadow_key = self.resolve_shadow_ticket(planning_issue_key)
        except ShadowTicketNotFoundError:
            return BookingStatus(
                planning_issue_key=planning_issue_key,
                planning_summary=planning_summary,
                booking_issue_key=None,
                estimate_seconds=estimate_seconds,
                spent_seconds=0,
                remaining_seconds=estimate_seconds,
                is_overbooked=False,
            )

        # Fetch Tempo worklogs for shadow ticket
        shadow_issue_id = self._get_booking_issue_id(shadow_key)

        try:
            worklogs = self.tempo_client.get_worklogs(issue_id=shadow_issue_id, limit=1000)
            spent_seconds = sum(w.timeSpentSeconds for w in worklogs)
        except JiraAPIError as e:
            logger.warning(
                "Could not fetch Tempo worklogs for %s (ID: %d) on %s: %s",
                shadow_key,
                shadow_issue_id,
                self.booking_jira.connection.url,
                e,
            )
            spent_seconds = 0

        # Calculate remaining and overbooking
        remaining_seconds: int | None = None
        is_overbooked = False
        overbooking_seconds = 0

        if estimate_seconds is not None:
            remaining_seconds = estimate_seconds - spent_seconds
            if remaining_seconds < 0:
                is_overbooked = True
                overbooking_seconds = abs(remaining_seconds)
                remaining_seconds = 0

        return BookingStatus(
            planning_issue_key=planning_issue_key,
            planning_summary=planning_summary,
            booking_issue_key=shadow_key,
            estimate_seconds=estimate_seconds,
            spent_seconds=spent_seconds,
            remaining_seconds=remaining_seconds,
            is_overbooked=is_overbooked,
            overbooking_seconds=overbooking_seconds,
        )

    def get_sprint_booking_overview(
        self,
        sprint_id: int,
        mine_only: bool = False,
    ) -> list[BookingStatus]:
        """Get booking status for all issues in a sprint.

        Fetches sprint issues from the planning instance and resolves
        booking status for each via the shadow ticket + Tempo.

        Args:
            sprint_id: Sprint ID to query
            mine_only: If True, only return issues assigned to current user

        Returns:
            List of BookingStatus for each sprint issue
        """
        jql_filter = "assignee = currentUser()" if mine_only else None
        issues = self.planning_jira.sprints.get_sprint_issues(sprint_id, jql_filter=jql_filter)

        statuses: list[BookingStatus] = []
        for issue in issues:
            try:
                status = self.get_booking_status(issue.key)
                statuses.append(status)
            except Exception as e:
                logger.warning(f"Could not get booking status for {issue.key}: {e}")
                statuses.append(
                    BookingStatus(
                        planning_issue_key=issue.key,
                        planning_summary=issue.summary,
                        booking_issue_key=None,
                        estimate_seconds=issue.time_original_estimate,
                        spent_seconds=0,
                        remaining_seconds=issue.time_original_estimate,
                        is_overbooked=False,
                    )
                )

        return statuses

    def _require_billing_config(self) -> BillingConfig:
        """Return the profile's billing config, or raise with a TOML hint.

        Raises:
            WorkflowConfigError: If the profile has no billing block
        """
        if self.profile.billing is None:
            raise WorkflowConfigError(
                f"Workflow profile '{self.profile.name}' has no billing configuration. "
                "Add a billing block to the profile in workflows.toml, e.g.:\n"
                "  [profiles.billing]\n"
                '  categories = { analysis = "billable", warranty = "non-billable" }'
            )
        return self.profile.billing

    def get_billing_report(self, from_date: date, to_date: date, group_by: str = "bucket") -> BillingReport:
        """Build a billing report over a period by joining Tempo worklogs back to planning issues.

        Inverted join (a handful of API calls regardless of issue count):
        1. Fetch all Tempo worklogs in the period for each mapped booking project
        2. Batch-fetch the booking issues (summaries carry the planning key)
        3. Extract the planning key from each booking summary (summary strategy, read backwards)
        4. Batch-fetch the planning issues for labels and summaries
        5. Categorize by label, group by bucket (or category), total

        Args:
            from_date: First day of the period (inclusive)
            to_date: Last day of the period (inclusive)
            group_by: Group lines by "bucket" (default) or "category"

        Returns:
            BillingReport with groups, totals (excluding configured buckets) and warnings

        Raises:
            WorkflowConfigError: If no billing block is configured or the shadow
                strategy is not 'summary'
            ValidationError: If group_by is invalid
            BillingValidationError: If require_exactly_one is set and issues carry
                multiple category labels
        """
        billing = self._require_billing_config()

        if group_by not in ("bucket", "category"):
            raise ValidationError(f"Invalid group_by: '{group_by}'. Expected 'bucket' or 'category'.")

        if self.profile.shadow_strategy != ShadowTicketStrategy.SUMMARY_SEARCH:
            raise WorkflowConfigError(
                f"workflow billing requires shadow_strategy = 'summary', but profile '{self.profile.name}' "
                f"uses '{self.profile.shadow_strategy}'."
            )

        # A configured rate of 0 means hours-only, same as absent
        rate = billing.rate if billing.rate else None
        warnings: list[str] = []

        # 1) Booked seconds per booking issue, paged per booking project
        seconds_by_issue_id: dict[int, int] = {}
        issue_keys: dict[int, str] = {}
        for mapping in self.profile.project_mappings:
            offset = 0
            while True:
                page = self.tempo_client.get_worklogs(
                    from_date=from_date,
                    to_date=to_date,
                    project_key=mapping.booking_project,
                    limit=_BILLING_PAGE_LIMIT,
                    offset=offset,
                )
                for worklog in page:
                    if worklog.issue.id is None:
                        continue
                    seconds_by_issue_id[worklog.issue.id] = (
                        seconds_by_issue_id.get(worklog.issue.id, 0) + worklog.timeSpentSeconds
                    )
                    if worklog.issue.key:
                        issue_keys[worklog.issue.id] = worklog.issue.key
                if len(page) < _BILLING_PAGE_LIMIT:
                    break
                offset += _BILLING_PAGE_LIMIT

        if not seconds_by_issue_id:
            return BillingReport(
                profile=self.profile.name,
                period_from=from_date,
                period_to=to_date,
                rate=rate,
                currency=billing.currency,
                grouped_by=group_by,
                excluded_from_total=list(billing.exclude_from_total),
                warnings=warnings,
            )

        # 2) Backfill booking issue keys Tempo omitted (rare; per-issue lookup)
        for issue_id in seconds_by_issue_id:
            if issue_id not in issue_keys:
                try:
                    issue_keys[issue_id] = self.booking_jira.client.issue(str(issue_id)).key
                except JiraAPIError as e:
                    warnings.append(f"Booking issue ID {issue_id} could not be resolved ({e}); skipped")

        # 3) Batch-fetch booking issue summaries and extract planning keys
        booking_keys = sorted(issue_keys.values())
        booking_summaries: dict[str, str] = {}
        if booking_keys:
            jql = f"key in ({', '.join(booking_keys)})"
            for issue in self.booking_jira.search_issues(jql, max_results=max(len(booking_keys), 1)):
                booking_summaries[issue.key] = issue.summary

        planning_projects = sorted({m.planning_project for m in self.profile.project_mappings})
        planning_key_pattern = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in planning_projects) + r")-\d+\b")

        # 4) Batch-fetch planning issues for labels and summaries
        planning_keys_found = {
            match.group(0) for summary in booking_summaries.values() if (match := planning_key_pattern.search(summary))
        }
        planning_issues: dict[str, Any] = {}
        if planning_keys_found:
            jql = f"key in ({', '.join(sorted(planning_keys_found))})"
            for issue in self.planning_jira.search_issues(jql, max_results=max(len(planning_keys_found), 1)):
                planning_issues[issue.key] = issue

        # 5) Build lines
        lines: list[BillingLine] = []
        multi_label_violations: list[str] = []
        for issue_id, seconds in seconds_by_issue_id.items():
            booking_key = issue_keys.get(issue_id)
            if booking_key is None:
                continue  # already reported in warnings

            booking_summary = booking_summaries.get(booking_key, "")
            match = planning_key_pattern.search(booking_summary)
            planning_key = match.group(0) if match else None
            planning_issue = planning_issues.get(planning_key) if planning_key else None

            if planning_key is None or planning_issue is None:
                reason = "no planning key in its summary" if planning_key is None else "planning issue not found"
                warnings.append(f"{booking_key}: {reason}; counted as uncategorised")
                lines.append(
                    self._billing_line(
                        issue=planning_key or booking_key,
                        booking_issue=booking_key,
                        category=None,
                        bucket=UNCATEGORISED_BUCKET,
                        summary=booking_summary,
                        seconds=seconds,
                        rate=rate,
                    )
                )
                continue

            matching = sorted(label for label in planning_issue.labels if label in billing.categories)
            if len(matching) > 1:
                if billing.require_exactly_one:
                    multi_label_violations.append(f"{planning_key} ({', '.join(matching)})")
                    continue
                warnings.append(
                    f"{planning_key} carries multiple category labels ({', '.join(matching)}); using '{matching[0]}'"
                )
            category = matching[0] if matching else None
            bucket = billing.categories[category] if category else UNCATEGORISED_BUCKET
            lines.append(
                self._billing_line(
                    issue=planning_key,
                    booking_issue=booking_key,
                    category=category,
                    bucket=bucket,
                    summary=planning_issue.summary,
                    seconds=seconds,
                    rate=rate,
                )
            )

        if multi_label_violations:
            raise BillingValidationError(
                f"Issues with multiple category labels: {'; '.join(multi_label_violations)}. "
                "A report cannot decide between them — fix the labels or set require_exactly_one = false "
                f"in profile '{self.profile.name}'. "
                f"Run 'budjira workflow billing --profile {self.profile.name} --validate' to find all violations."
            )

        # 6) Group, order, total
        groups = self._group_billing_lines(lines, billing, group_by, rate)
        included = [line for line in lines if line.bucket not in billing.exclude_from_total]
        totals = BillingTotals(
            seconds=sum(line.seconds for line in included),
            hours=round(sum(line.seconds for line in included) / 3600, 2),
            amount=round(sum(line.seconds for line in included) / 3600 * rate, 2) if rate else None,
        )

        return BillingReport(
            profile=self.profile.name,
            period_from=from_date,
            period_to=to_date,
            rate=rate,
            currency=billing.currency,
            grouped_by=group_by,
            groups=groups,
            excluded_from_total=list(billing.exclude_from_total),
            totals=totals,
            warnings=warnings,
        )

    @staticmethod
    def _billing_line(
        *,
        issue: str,
        booking_issue: str,
        category: str | None,
        bucket: str,
        summary: str,
        seconds: int,
        rate: float | None,
    ) -> BillingLine:
        """Build a BillingLine with derived hours/amount."""
        return BillingLine(
            issue=issue,
            booking_issue=booking_issue,
            category=category,
            bucket=bucket,
            summary=summary,
            seconds=seconds,
            hours=round(seconds / 3600, 2),
            amount=round(seconds / 3600 * rate, 2) if rate else None,
        )

    @staticmethod
    def _group_billing_lines(
        lines: list[BillingLine],
        billing: BillingConfig,
        group_by: str,
        rate: float | None,
    ) -> list[BillingGroup]:
        """Group lines by bucket or category, in config order with uncategorised last."""
        groups: dict[str, BillingGroup] = {}
        for line in sorted(lines, key=lambda line_: line_.issue):
            name = line.bucket if group_by == "bucket" else (line.category or UNCATEGORISED_BUCKET)
            group = groups.setdefault(name, BillingGroup(name=name, bucket=line.bucket))
            group.lines.append(line)
        for group in groups.values():
            group.total_seconds = sum(line.seconds for line in group.lines)
            group.total_hours = round(group.total_seconds / 3600, 2)
            group.total_amount = round(sum(line.amount or 0.0 for line in group.lines), 2) if rate else None

        order = list(dict.fromkeys(billing.categories.values())) if group_by == "bucket" else list(billing.categories)
        return sorted(
            groups.values(),
            key=lambda g: (
                g.name == UNCATEGORISED_BUCKET,
                order.index(g.name) if g.name in order else len(order),
                g.name,
            ),
        )

    def validate_billing_labels(self) -> BillingValidation:
        """Check category-label hygiene across the profile's planning projects.

        Finds issues with no category label ('missing') and issues with more
        than one ('multiple'), without producing a report.

        Returns:
            BillingValidation with all violations found

        Raises:
            WorkflowConfigError: If the profile has no billing block
        """
        billing = self._require_billing_config()

        violations: list[BillingViolation] = []
        issues_checked = 0
        truncated = False
        for mapping in self.profile.project_mappings:
            issues = self.planning_jira.search_issues(
                f"project = {mapping.planning_project}",
                max_results=_BILLING_SEARCH_LIMIT,
            )
            if len(issues) >= _BILLING_SEARCH_LIMIT:
                truncated = True
            for issue in issues:
                issues_checked += 1
                matching = sorted(label for label in issue.labels if label in billing.categories)
                if not matching:
                    violations.append(BillingViolation(issue=issue.key, kind="missing", summary=issue.summary))
                elif len(matching) > 1:
                    violations.append(
                        BillingViolation(issue=issue.key, kind="multiple", labels=matching, summary=issue.summary)
                    )

        return BillingValidation(
            profile=self.profile.name,
            issues_checked=issues_checked,
            violations=violations,
            truncated=truncated,
        )

    def _check_overbooking(
        self,
        estimate_seconds: int | None,
        spent_seconds: int,
        new_seconds: int,
        planning_issue_key: str,
    ) -> None:
        """Check overbooking policy and act accordingly.

        Args:
            estimate_seconds: Original estimate (None = skip check)
            spent_seconds: Already spent time
            new_seconds: Time being added
            planning_issue_key: For error messages

        Raises:
            OverbookingError: If policy is BLOCK and would overbook
        """
        if estimate_seconds is None:
            return

        total_after = spent_seconds + new_seconds
        if total_after <= estimate_seconds:
            return

        overbooking = total_after - estimate_seconds
        estimate_display = _format_seconds(estimate_seconds)
        spent_display = _format_seconds(spent_seconds)
        new_display = _format_seconds(new_seconds)
        total_display = _format_seconds(total_after)
        over_display = _format_seconds(overbooking)

        warning_msg = (
            f"This booking ({new_display}) would exceed the estimate on {planning_issue_key}.\n"
            f"   Estimate: {estimate_display} | Already spent: {spent_display} | "
            f"After booking: {total_display} (+{over_display} over)"
        )

        policy = self.profile.overbooking_policy

        if policy == OverbookingPolicy.WARN:
            console.print(f"[yellow]Warning:[/yellow] {warning_msg}")
        elif policy == OverbookingPolicy.CONFIRM:
            console.print(f"[yellow]Warning:[/yellow] {warning_msg}")
            if not typer.confirm("Continue with booking?"):
                raise OverbookingError("Booking cancelled by user due to overbooking.")
        elif policy == OverbookingPolicy.BLOCK:
            raise OverbookingError(f"Booking blocked by overbooking policy. {warning_msg}")

    def book_time(
        self,
        planning_issue_key: str,
        time_spent: str,
        comment: str | None = None,
        started: str | None = None,
    ) -> TempoWorklog:
        """Book time via workflow (resolve shadow, check overbooking, log to Tempo).

        Args:
            planning_issue_key: Issue key in planning instance
            time_spent: Time to book (e.g., 2h, 30m, 2h30m)
            comment: Optional worklog comment
            started: Optional start datetime string

        Returns:
            Created Tempo worklog

        Raises:
            ShadowTicketNotFoundError: If shadow ticket not found
            OverbookingError: If overbooking policy blocks
        """
        # Resolve shadow ticket
        shadow_key = self.resolve_shadow_ticket(planning_issue_key)
        console.print(f"Resolving shadow ticket for {planning_issue_key}... [cyan]{shadow_key}[/cyan]")

        # Fetch planning issue for estimate
        planning_issue = self.planning_jira.get_issue(planning_issue_key)
        estimate_seconds = planning_issue.time_original_estimate

        # Fetch current Tempo spent on shadow
        shadow_issue_id = self._get_booking_issue_id(shadow_key)

        try:
            worklogs = self.tempo_client.get_worklogs(issue_id=shadow_issue_id, limit=1000)
            spent_seconds = sum(w.timeSpentSeconds for w in worklogs)
        except JiraAPIError as e:
            logger.warning(
                "Could not fetch Tempo worklogs for %s (ID: %d) on %s: %s",
                shadow_key,
                shadow_issue_id,
                self.booking_jira.connection.url,
                e,
            )
            spent_seconds = 0

        # Parse time
        time_spent_minutes = parse_time_string(time_spent)
        new_seconds = time_spent_minutes * 60

        # Show current status
        if estimate_seconds is not None:
            console.print(
                f"Estimate: {_format_seconds(estimate_seconds)} | "
                f"Spent: {_format_seconds(spent_seconds)} | "
                f"This booking: {_format_seconds(new_seconds)}"
            )

        # Check overbooking
        self._check_overbooking(estimate_seconds, spent_seconds, new_seconds, planning_issue_key)

        # Get author account ID from booking connection
        myself = self.booking_jira.client.myself()
        author_account_id = myself["accountId"]

        # Parse started datetime
        started_dt = parse_datetime_string(started) if started else datetime.now()
        start_date = started_dt.strftime("%Y-%m-%d")
        start_time = started_dt.strftime("%H:%M:%S")

        # Create Tempo worklog
        console.print(f"Logging {time_spent} to {shadow_key} via Tempo...")
        worklog = self.tempo_client.create_worklog(
            issue_id=shadow_issue_id,
            time_spent_seconds=new_seconds,
            start_date=start_date,
            start_time=start_time,
            author_account_id=author_account_id,
            description=comment,
        )

        # Validate Tempo-returned issue ID matches what we sent
        if worklog.issue.id is not None and worklog.issue.id != shadow_issue_id:
            logger.warning(
                "Tempo stored issue ID %d but we sent %d for %s — subsequent queries may fail",
                worklog.issue.id,
                shadow_issue_id,
                shadow_key,
            )

        console.print(
            f"[green]Logged {time_spent} to {shadow_key} via Tempo (Worklog ID: {worklog.tempoWorklogId})[/green]"
        )
        return worklog


def _format_seconds(seconds: int) -> str:
    """Format seconds into human-readable time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string (e.g., "2h 30m")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{minutes}m"
