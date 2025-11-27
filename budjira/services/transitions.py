"""Transition service for managing issue status changes."""

from __future__ import annotations

from jira.exceptions import JIRAError

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

    def transition(self, issue_key: str, transition_name: str) -> None:
        """Transition an issue to a new status.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            transition_name: Name of the transition (e.g., "In Progress", "Done")

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

            self.client.transition_issue(issue_key, transition_id)
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
