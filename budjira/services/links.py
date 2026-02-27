"""Service for managing Jira issue links."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from jira.exceptions import JIRAError

from budjira.models.issue import Issue, IssueLink
from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError

if TYPE_CHECKING:
    from jira import JIRA


class LinkService(BaseJiraService):
    """Service for managing Jira issue links."""

    def __init__(self, client: JIRA) -> None:
        """Initialize link service.

        Args:
            client: JIRA client instance
        """
        super().__init__(client)
        self._link_types_cache: dict[str, Any] | None = None
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = timedelta(hours=24)

    def get_link_types(self) -> dict[str, Any]:
        """Get available issue link types from Jira (cached 24h).

        Returns:
            Dictionary mapping link type names to link type info

        Raises:
            JiraAPIError: If fetching link types fails
        """
        # Check cache validity
        if (
            self._link_types_cache is not None
            and self._cache_timestamp is not None
            and datetime.now() - self._cache_timestamp < self._cache_ttl
        ):
            self._logger.debug("Returning cached link types")
            return self._link_types_cache

        # Fetch link types from Jira
        try:
            self._logger.debug("Fetching issue link types from Jira")
            link_types_list = self.client.issue_link_types()

            # Convert to dictionary for easy lookup
            link_types = {}
            for lt in link_types_list:
                link_types[lt.name] = {
                    "id": lt.id,
                    "name": lt.name,
                    "inward": lt.inward,
                    "outward": lt.outward,
                }

            # Update cache
            self._link_types_cache = link_types
            self._cache_timestamp = datetime.now()

            self._logger.info(f"Fetched {len(link_types)} link types")
            return link_types

        except JIRAError as e:
            raise JiraAPIError(f"Failed to fetch issue link types: {e}") from e

    def create_link(
        self,
        link_type: str,
        outward_issue: str,
        inward_issue: str,
        comment: str | None = None,
    ) -> None:
        """Create an issue link.

        Args:
            link_type: Link type name (e.g., "Relates", "Blocks")
            outward_issue: Issue key for outward side (FROM)
            inward_issue: Issue key for inward side (TO)
            comment: Optional comment for the link

        Raises:
            ValueError: If link type is invalid
            InvalidIssueError: If issue not found (404)
            PermissionError: If insufficient permissions (403)
            JiraAPIError: If API call fails
        """
        # Validate link type
        link_types = self.get_link_types()
        if link_type not in link_types:
            available = ", ".join(link_types.keys())
            raise ValueError(f"Invalid link type '{link_type}'. Available types: {available}")

        # Prepare link data
        link_data: dict[str, Any] = {
            "type": link_type,
            "outwardIssue": inward_issue,  # Note: Jira's naming is confusing
            "inwardIssue": outward_issue,
        }

        if comment:
            link_data["comment"] = {"body": comment}

        # Create link
        try:
            self._log_operation(
                "Create issue link",
                link_type=link_type,
                from_issue=outward_issue,
                to_issue=inward_issue,
            )
            self.client.create_issue_link(**link_data)
            self._logger.info(f"Created {link_type} link: {outward_issue} -> {inward_issue}")

        except JIRAError as e:
            self._handle_jira_error(
                e,
                "Create issue link",
                from_issue=outward_issue,
                to_issue=inward_issue,
            )

    def get_issue_links(self, issue_key: str) -> list[IssueLink]:
        """Get all issue links for an issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            List of IssueLink objects

        Raises:
            InvalidIssueError: If issue not found
        """
        try:
            self._log_operation("Get issue links", issue_key=issue_key)
            jira_issue = self.client.issue(issue_key, fields="issuelinks")

            # Parse links using Issue model
            if hasattr(jira_issue.fields, "issuelinks") and jira_issue.fields.issuelinks:
                links = Issue._parse_issue_links(jira_issue.fields.issuelinks)
                self._logger.info(f"Found {len(links)} links for {issue_key}")
                return links

            self._logger.info(f"No links found for {issue_key}")
            return []

        except JIRAError as e:
            self._handle_jira_error(e, "Get issue links", issue_key=issue_key)
            return []  # Unreachable, but makes mypy happy

    def delete_link(self, link_id: str) -> None:
        """Delete an issue link.

        Args:
            link_id: Link ID to delete

        Raises:
            InvalidIssueError: If link not found (404)
            JiraAPIError: If API call fails
        """
        try:
            self._log_operation("Delete issue link", link_id=link_id)
            self.client.delete_issue_link(link_id)
            self._logger.info(f"Deleted link {link_id}")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue link '{link_id}' not found") from e
            self._handle_jira_error(e, "Delete issue link", link_id=link_id)
