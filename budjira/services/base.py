"""Base service class for all Jira services."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from jira.exceptions import JIRAError  # noqa: TC002 - needed at runtime for method signature

from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from jira import JIRA


class BaseJiraService:
    """Base class for all Jira services providing common functionality.

    This class provides:
    - Access to the JIRA client
    - Standardized error handling with context
    - Structured logging
    - Common patterns for API operations

    All service classes should inherit from this base and focus on a single
    domain (issues, worklogs, epics, etc.) following Single Responsibility Principle.
    """

    def __init__(self, client: JIRA) -> None:
        """Initialize service with JIRA client.

        Args:
            client: Authenticated JIRA client instance
        """
        self._client = client
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    def client(self) -> JIRA:
        """Get the underlying JIRA client.

        Returns:
            Authenticated JIRA client instance
        """
        return self._client

    def _handle_jira_error(self, error: JIRAError, operation: str, **context: Any) -> None:
        """Handle JIRA API errors with context-aware exception mapping.

        Maps JIRA HTTP status codes to appropriate domain exceptions:
        - 404 → InvalidIssueError (resource not found)
        - 403 → PermissionError (access denied)
        - Other → JiraAPIError (general API error)

        Args:
            error: JIRA API error from jira library
            operation: Human-readable operation description (e.g., "Fetch issue")
            **context: Additional context to log (e.g., issue_key="PROJ-123")

        Raises:
            InvalidIssueError: When resource not found (404)
            PermissionError: When access denied (403)
            JiraAPIError: For all other API errors
        """
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        log_msg = f"{operation} failed ({context_str}): {error.text}"

        if error.status_code == 404:
            self._logger.warning(log_msg)
            raise InvalidIssueError(f"{operation} failed: Resource not found. {context_str}") from error
        elif error.status_code == 403:
            self._logger.warning(log_msg)
            raise PermissionError(f"{operation} failed: Access denied. {context_str}") from error
        else:
            self._logger.error(log_msg)
            raise JiraAPIError(f"{operation} failed: {error.text}") from error

    def _log_operation(self, operation: str, **context: Any) -> None:
        """Log an operation with structured context.

        Args:
            operation: Human-readable operation description
            **context: Additional context to log (e.g., issue_key="PROJ-123", fields=["summary", "status"])
        """
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        self._logger.info(f"{operation} ({context_str})")
