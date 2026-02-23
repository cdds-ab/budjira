"""Workflow service for cross-instance Jira operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from budjira.config.credentials import CredentialStore
from budjira.config.settings import get_settings
from budjira.core.jira_client import JiraClient
from budjira.models.workflow import BookingStatus, OverbookingPolicy, WorkflowProfile
from budjira.tempo.client import TempoClient
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import (
    AuthenticationError,
    ConnectionError,
    OverbookingError,
    ShadowTicketAmbiguousError,
    ShadowTicketNotFoundError,
    WorkflowConfigError,
)
from budjira.utils.time_parser import parse_time_string

if TYPE_CHECKING:
    from budjira.tempo.models import TempoWorklog

logger = logging.getLogger(__name__)
console = Console()


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
        shadow_issue = self.booking_jira.client.issue(shadow_key)
        shadow_issue_id = int(shadow_issue.id)

        worklogs = self.tempo_client.get_worklogs(issue_id=shadow_issue_id, limit=1000)
        spent_seconds = sum(w.timeSpentSeconds for w in worklogs)

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
        shadow_issue = self.booking_jira.client.issue(shadow_key)
        shadow_issue_id = int(shadow_issue.id)

        worklogs = self.tempo_client.get_worklogs(issue_id=shadow_issue_id, limit=1000)
        spent_seconds = sum(w.timeSpentSeconds for w in worklogs)

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
