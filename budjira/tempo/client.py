"""Tempo Timesheets API client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests

from budjira.tempo.models import (
    TempoAccount,
    TempoAccountList,
    TempoTimesheetApproval,
    TempoWorklog,
    TempoWorklogCreate,
    TempoWorklogList,
    TempoWorklogUpdate,
)
from budjira.utils.errors import AuthenticationError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from datetime import date

logger = logging.getLogger(__name__)


class TempoClient:
    """Client for Tempo Timesheets Cloud API.

    Tempo is a popular time tracking add-on for Jira Cloud.
    API Documentation: https://apidocs.tempo.io/
    """

    BASE_URL = "https://api.tempo.io"
    API_VERSION = "4"

    def __init__(self, tempo_token: str) -> None:
        """Initialize Tempo client.

        Args:
            tempo_token: Tempo API token (create at Tempo → Settings → API Integration)

        Raises:
            AuthenticationError: If authentication fails
        """
        self.tempo_token = tempo_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {tempo_token}",
                "Content-Type": "application/json",
            }
        )
        logger.info("Tempo client initialized")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Make HTTP request to Tempo API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /worklogs)
            params: Query parameters
            json_data: JSON request body

        Returns:
            API response data, or None for 204 No Content responses

        Raises:
            AuthenticationError: If authentication fails (401)
            PermissionError: If access is denied (403)
            JiraAPIError: For other API errors
        """
        url = f"{self.BASE_URL}/{self.API_VERSION}{endpoint}"
        logger.debug(f"Tempo API request: {method} {url}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()

            # Handle 204 No Content (successful DELETE)
            if response.status_code == 204:
                return None

            # Parse JSON response for other success codes
            if response.content:
                return response.json()  # type: ignore[no-any-return]

            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Tempo authentication failed. Check your Tempo API token at "
                    "Tempo → Settings → API Integration → Tokens"
                ) from e
            elif e.response.status_code == 403:
                raise PermissionError("Access denied. Your Tempo API token lacks required permissions.") from e
            elif e.response.status_code == 404:
                # Safely parse error message from JSON (if present)
                try:
                    error_data = e.response.json() if e.response.content else {}
                    error_msg = error_data.get("message", "Resource not found")
                except ValueError:
                    error_msg = "Resource not found"
                raise JiraAPIError(f"Tempo API error: {error_msg}") from e
            else:
                # Safely parse error data
                try:
                    error_data = e.response.json() if e.response.content else {}
                    error_msg = error_data.get("message", str(e))
                except ValueError:
                    error_msg = str(e)
                logger.debug(
                    "Tempo API %s %s failed (%d): %s | params=%s body=%s",
                    method,
                    endpoint,
                    e.response.status_code,
                    error_msg,
                    params,
                    json_data,
                )
                raise JiraAPIError(f"Tempo API error: {error_msg}") from e
        except requests.exceptions.RequestException as e:
            raise JiraAPIError(f"Failed to connect to Tempo API: {e}") from e

    def create_worklog(
        self,
        issue_id: int,
        time_spent_seconds: int,
        start_date: str,
        author_account_id: str,
        start_time: str = "09:00:00",
        description: str | None = None,
        billable_seconds: int | None = None,
        remaining_estimate_seconds: int | None = None,
    ) -> TempoWorklog:
        """Create a new worklog entry.

        Args:
            issue_id: Numeric Jira issue ID (e.g., 12345, NOT "PROJ-123")
            time_spent_seconds: Time spent in seconds
            start_date: Start date (YYYY-MM-DD)
            author_account_id: Jira account ID of the author
            start_time: Start time (HH:MM:SS, default: 09:00:00)
            description: Worklog comment/description
            billable_seconds: Billable time in seconds
            remaining_estimate_seconds: Remaining estimate after logging work

        Returns:
            Created worklog entry

        Raises:
            JiraAPIError: If worklog creation fails
        """
        worklog_data = TempoWorklogCreate(
            issueId=issue_id,
            timeSpentSeconds=time_spent_seconds,
            startDate=start_date,
            startTime=start_time,
            description=description,
            authorAccountId=author_account_id,
            billableSeconds=billable_seconds,
            remainingEstimateSeconds=remaining_estimate_seconds,
        )

        logger.info(f"Creating Tempo worklog for issue ID {issue_id}: {time_spent_seconds}s")
        response = self._make_request(
            method="POST",
            endpoint="/worklogs",
            json_data=worklog_data.model_dump(exclude_none=True),
        )
        return TempoWorklog(**response)  # type: ignore[arg-type]

    def get_worklogs(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
        issue_id: int | None = None,
        account_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TempoWorklog]:
        """Get worklog entries.

        Note: the Tempo v4 ``GET /worklogs`` endpoint has no project filter
        (a ``project`` parameter is rejected with 400). Callers needing a
        project scope must filter the returned worklogs client-side by their
        issue keys.

        Args:
            from_date: Start date filter (inclusive)
            to_date: End date filter (inclusive)
            issue_id: Filter by numeric issue ID (e.g., 12345, NOT "PROJ-123")
            account_id: Filter by author account ID
            limit: Maximum number of results (default: 50, max: 1000)
            offset: Pagination offset

        Returns:
            List of worklog entries

        Raises:
            JiraAPIError: If retrieval fails
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        if issue_id:
            params["issueId"] = issue_id
        if account_id:
            params["accountId"] = account_id

        logger.info(f"Fetching Tempo worklogs with params: {params}")
        response = self._make_request(
            method="GET",
            endpoint="/worklogs",
            params=params,
        )

        worklog_list = TempoWorklogList(**response)  # type: ignore[arg-type]
        return worklog_list.results

    def get_worklog(self, worklog_id: int) -> TempoWorklog:
        """Get a specific worklog by ID.

        Args:
            worklog_id: Tempo worklog ID

        Returns:
            Worklog entry

        Raises:
            JiraAPIError: If worklog not found
        """
        logger.info(f"Fetching Tempo worklog {worklog_id}")
        response = self._make_request(
            method="GET",
            endpoint=f"/worklogs/{worklog_id}",
        )
        return TempoWorklog(**response)  # type: ignore[arg-type]

    def delete_worklog(self, worklog_id: int) -> None:
        """Delete a worklog entry.

        Args:
            worklog_id: Tempo worklog ID

        Raises:
            JiraAPIError: If deletion fails
        """
        logger.info(f"Deleting Tempo worklog {worklog_id}")
        self._make_request(
            method="DELETE",
            endpoint=f"/worklogs/{worklog_id}",
        )

    def update_worklog(
        self,
        worklog_id: int,
        issue_id: int | None = None,
        time_spent_seconds: int | None = None,
        start_date: str | None = None,
        start_time: str | None = None,
        description: str | None = None,
        author_account_id: str | None = None,
        billable_seconds: int | None = None,
        remaining_estimate_seconds: int | None = None,
    ) -> TempoWorklog:
        """Update an existing worklog entry.

        Args:
            worklog_id: Tempo worklog ID to update
            issue_id: Numeric Jira issue ID (e.g., 12345, NOT "PROJ-123")
            time_spent_seconds: Time spent in seconds
            start_date: Start date (YYYY-MM-DD)
            start_time: Start time (HH:MM:SS)
            description: Worklog comment/description
            author_account_id: Jira account ID of the author
            billable_seconds: Billable time in seconds
            remaining_estimate_seconds: Remaining estimate after logging work

        Returns:
            Updated worklog entry

        Raises:
            JiraAPIError: If worklog update fails
        """
        worklog_data = TempoWorklogUpdate(
            issueId=issue_id,
            timeSpentSeconds=time_spent_seconds,
            startDate=start_date,
            startTime=start_time,
            description=description,
            authorAccountId=author_account_id,
            billableSeconds=billable_seconds,
            remainingEstimateSeconds=remaining_estimate_seconds,
        )

        logger.info(f"Updating Tempo worklog {worklog_id}")
        response = self._make_request(
            method="PUT",
            endpoint=f"/worklogs/{worklog_id}",
            json_data=worklog_data.model_dump(exclude_none=True),
        )
        return TempoWorklog(**response)  # type: ignore[arg-type]

    def get_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TempoAccount]:
        """Get Tempo accounts (for billing/project tracking).

        Args:
            limit: Maximum number of results (default: 50)
            offset: Pagination offset

        Returns:
            List of Tempo accounts

        Raises:
            JiraAPIError: If retrieval fails
        """
        params = {
            "limit": limit,
            "offset": offset,
        }

        logger.info("Fetching Tempo accounts")
        response = self._make_request(
            method="GET",
            endpoint="/accounts",
            params=params,
        )

        account_list = TempoAccountList(**response)  # type: ignore[arg-type]
        return account_list.results

    def get_account(self, account_key: str) -> TempoAccount:
        """Get a specific Tempo account by key.

        Args:
            account_key: Tempo account key

        Returns:
            Tempo account

        Raises:
            JiraAPIError: If account not found
        """
        logger.info(f"Fetching Tempo account {account_key}")
        response = self._make_request(
            method="GET",
            endpoint=f"/accounts/{account_key}",
        )
        return TempoAccount(**response)  # type: ignore[arg-type]

    def get_timesheet_approval(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
    ) -> TempoTimesheetApproval:
        """Get the timesheet approval status of a user for a period.

        Args:
            account_id: Jira account ID of the user
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)

        Returns:
            Timesheet approval with status, required/spent seconds and the
            actions map of the actions the caller may currently perform

        Raises:
            JiraAPIError: If retrieval fails
        """
        params = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }

        logger.info(f"Fetching timesheet approval for user {account_id}: {params['from']} → {params['to']}")
        response = self._make_request(
            method="GET",
            endpoint=f"/timesheet-approvals/user/{account_id}",
            params=params,
        )
        return TempoTimesheetApproval(**response)  # type: ignore[arg-type]

    def _timesheet_approval_action(
        self,
        action: str,
        account_id: str,
        from_date: date,
        to_date: date,
        comment: str | None = None,
    ) -> TempoTimesheetApproval:
        """Perform a timesheet approval action (submit/approve/reject/reopen).

        Args:
            action: Approval action name
            account_id: Jira account ID of the timesheet owner
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)
            comment: Optional comment attached to the action

        Returns:
            Resulting timesheet approval state

        Raises:
            JiraAPIError: If the action fails
        """
        params = {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        }
        json_data = {"comment": comment} if comment is not None else None

        logger.info(f"Timesheet approval action '{action}' for user {account_id}: {params['from']} → {params['to']}")
        response = self._make_request(
            method="POST",
            endpoint=f"/timesheet-approvals/user/{account_id}/{action}",
            params=params,
            json_data=json_data,
        )
        return TempoTimesheetApproval(**response)  # type: ignore[arg-type]

    def submit_timesheet(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        comment: str | None = None,
    ) -> TempoTimesheetApproval:
        """Submit a timesheet period for review (owner action).

        Args:
            account_id: Jira account ID of the timesheet owner
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)
            comment: Optional submission comment

        Returns:
            Resulting timesheet approval state

        Raises:
            JiraAPIError: If submission fails
        """
        return self._timesheet_approval_action("submit", account_id, from_date, to_date, comment)

    def approve_timesheet(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        comment: str | None = None,
    ) -> TempoTimesheetApproval:
        """Approve a submitted timesheet period (approver action).

        An approved timesheet is locked against further bookings in that
        period. Requires the approver role for the user's Tempo team.

        Args:
            account_id: Jira account ID of the timesheet owner
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)
            comment: Optional approval comment

        Returns:
            Resulting timesheet approval state

        Raises:
            JiraAPIError: If approval fails
        """
        return self._timesheet_approval_action("approve", account_id, from_date, to_date, comment)

    def reject_timesheet(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        comment: str | None = None,
    ) -> TempoTimesheetApproval:
        """Reject a submitted timesheet period (approver action).

        Args:
            account_id: Jira account ID of the timesheet owner
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)
            comment: Optional rejection comment

        Returns:
            Resulting timesheet approval state

        Raises:
            JiraAPIError: If rejection fails
        """
        return self._timesheet_approval_action("reject", account_id, from_date, to_date, comment)

    def reopen_timesheet(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        comment: str | None = None,
    ) -> TempoTimesheetApproval:
        """Reopen a submitted or approved timesheet period.

        Args:
            account_id: Jira account ID of the timesheet owner
            from_date: Period start (inclusive)
            to_date: Period end (inclusive)
            comment: Optional comment

        Returns:
            Resulting timesheet approval state

        Raises:
            JiraAPIError: If reopening fails
        """
        return self._timesheet_approval_action("reopen", account_id, from_date, to_date, comment)
