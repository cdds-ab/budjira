"""Transition service for managing issue status changes."""

from __future__ import annotations

from typing import Any

from jira.exceptions import JIRAError

from budjira.models.transition import Transition, TransitionField
from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError


class TransitionService(BaseJiraService):
    """Service for managing issue status transitions."""

    def get_transitions(self, issue_key: str) -> list[dict[str, str]]:
        """Get available transitions for an issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of dicts with 'id' and 'name' keys

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch transitions", issue_key=issue_key)
            transitions = self.client.transitions(issue_key)
            return [{"id": t["id"], "name": t["name"]} for t in transitions]
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                self._handle_jira_error(e, "Fetch transitions", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching transitions: {e}") from e

    def get_transition_details(self, issue_key: str) -> list[Transition]:
        """Get available transitions including their screen fields.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            List of transitions with typed screen field metadata

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch transition details", issue_key=issue_key)
            raw_transitions = self.client.transitions(issue_key, expand="transitions.fields")
            return [self._parse_transition(raw) for raw in raw_transitions]
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            self._handle_jira_error(e, "Fetch transition details", issue_key=issue_key)
            raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error fetching transition details: {e}") from e

    @staticmethod
    def _parse_transition(raw: dict[str, Any]) -> Transition:
        """Map one raw Jira transition dict into a Transition model."""
        fields = [
            TransitionField(
                field_id=field_id,
                name=meta.get("name", field_id),
                required=bool(meta.get("required", False)),
                field_type=(meta.get("schema") or {}).get("type"),
                allowed_values=TransitionService._parse_allowed_values(meta),
            )
            for field_id, meta in (raw.get("fields") or {}).items()
        ]
        return Transition(
            id=str(raw["id"]),
            name=raw["name"],
            to_status=(raw.get("to") or {}).get("name"),
            fields=fields,
        )

    @staticmethod
    def _parse_allowed_values(meta: dict[str, Any]) -> list[str] | None:
        """Extract allowed values; entries carry 'name' or 'value' depending on field type."""
        raw_values = meta.get("allowedValues")
        if not raw_values:
            return None
        values = [v.get("name") or v.get("value") for v in raw_values if isinstance(v, dict)]
        return [v for v in values if v] or None

    def transition(self, issue_key: str, transition_name: str, fields: dict[str, Any] | None = None) -> None:
        """Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            transition_name: Name of the transition (e.g., "In Progress", "Done")
            fields: Optional transition screen field values, keyed by Jira field id

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If transition fails or is invalid
        """
        try:
            self._log_operation("Transition issue", issue_key=issue_key, transition=transition_name)

            # Get available transitions
            transitions = self.get_transitions(issue_key)

            # Find matching transition (case-insensitive)
            transition_id = None
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = ", ".join([t["name"] for t in transitions])
                raise JiraAPIError(
                    f"Invalid transition '{transition_name}' for {issue_key}. Available transitions: {available}"
                )

            self.client.transition_issue(issue_key, transition_id, fields=fields)
            self._logger.info(f"Successfully transitioned {issue_key} to '{transition_name}'")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(f"Issue '{issue_key}' not found") from e
            else:
                self._handle_jira_error(e, "Transition issue", issue_key=issue_key, transition=transition_name)
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error transitioning issue: {e}") from e
