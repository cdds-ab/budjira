"""Epic service for managing Jira epics and epic relationships."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jira.exceptions import JIRAError

from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError

if TYPE_CHECKING:
    from budjira.models.issue import Issue


class EpicService(BaseJiraService):
    """Service for managing Jira epics and issue-epic relationships."""

    def get_epic_issues(self, epic_key: str) -> list[Issue]:
        """Get all issues linked to an epic.

        Queries both modern (parent field) and legacy (Epic Link) approaches
        to support hybrid Jira environments where issues may be linked via
        either method.

        Args:
            epic_key: Epic key (e.g., PROJ-100)

        Returns:
            List of Issue objects (deduplicated by key)

        Raises:
            InvalidIssueError: If epic not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch epic issues", epic_key=epic_key)

            # Import IssueService to avoid circular dependency
            from budjira.services.issues import IssueService

            issue_service = IssueService(self.client)

            # Collect issues from both query methods
            all_issues: dict[str, Issue] = {}

            # Try modern approach (parent field - Jira Cloud team-managed projects)
            try:
                jql_modern = f"parent = {epic_key}"
                modern_issues = issue_service.search(jql_modern, max_results=100)
                for issue in modern_issues:
                    all_issues[issue.key] = issue
                self._logger.debug(f"Found {len(modern_issues)} issues using parent field")
            except Exception as e:
                self._logger.debug(f"Modern parent query failed: {e}")

            # Also try legacy Epic Link custom field (company-managed projects)
            try:
                jql_legacy = f'"Epic Link" = {epic_key}'
                legacy_issues = issue_service.search(jql_legacy, max_results=100)
                for issue in legacy_issues:
                    if issue.key not in all_issues:
                        all_issues[issue.key] = issue
                self._logger.debug(f"Found {len(legacy_issues)} issues using Epic Link field")
            except Exception as e:
                self._logger.debug(f"Legacy Epic Link query failed: {e}")

            result = list(all_issues.values())
            self._logger.debug(f"Total unique issues linked to epic: {len(result)}")
            return result

        except Exception as e:
            raise JiraAPIError(f"Failed to fetch epic issues: {e}") from e

    def get_issue_epic(self, issue_key: str) -> tuple[str, str] | None:
        """Get epic information for an issue.

        Fetches the parent epic key and name for a given issue.
        Supports both modern (parent field) and legacy (Epic Link) approaches.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            Tuple of (epic_key, epic_name) if issue has an epic, None otherwise

        Raises:
            InvalidIssueError: If issue not found
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Fetch issue epic", issue_key=issue_key)

            # Get issue with parent and epic link fields
            jira_issue = self.client.issue(issue_key, fields="parent,customfield_*,summary")

            # Try modern approach first (parent field)
            if hasattr(jira_issue.fields, "parent") and jira_issue.fields.parent:
                parent = jira_issue.fields.parent
                epic_key = parent.key
                epic_name = parent.fields.summary if hasattr(parent.fields, "summary") else epic_key
                self._logger.debug(f"Found epic via parent field: {epic_key}")
                return (epic_key, epic_name)

            # Try legacy Epic Link custom field
            for field_name in dir(jira_issue.fields):
                if "epic" in field_name.lower() and "link" in field_name.lower():
                    epic_key = getattr(jira_issue.fields, field_name, None)
                    if epic_key:
                        # Fetch epic details for name
                        try:
                            epic_issue = self.client.issue(epic_key, fields="summary")
                            epic_name = epic_issue.fields.summary
                        except Exception:
                            epic_name = epic_key  # Fallback to key if fetch fails
                        self._logger.debug(f"Found epic via Epic Link field: {epic_key}")
                        return (epic_key, epic_name)

            # No epic found
            self._logger.debug(f"No epic found for issue {issue_key}")
            return None

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Issue '{issue_key}' not found. Check that the issue exists and you have permission to view it."
                ) from e
            else:
                self._handle_jira_error(e, "Fetch issue epic", issue_key=issue_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to fetch epic for issue {issue_key}: {e}") from e

    def link_to_epic(self, issue_key: str, epic_key: str) -> None:
        """Link an issue to an epic.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            epic_key: Epic key (e.g., PROJ-100)

        Raises:
            InvalidIssueError: If issue or epic not found
            JiraAPIError: If linking fails
        """
        try:
            self._log_operation("Link to epic", issue_key=issue_key, epic_key=epic_key)

            issue = self.client.issue(issue_key)

            # Try modern approach first (parent field - used in Jira Cloud team-managed projects)
            try:
                issue.update(fields={"parent": {"key": epic_key}})
                self._logger.info(f"Successfully linked {issue_key} to epic {epic_key} using parent field")
                return
            except JIRAError as e:
                # If parent field fails, try legacy Epic Link field
                self._logger.debug(f"Parent field failed, trying legacy Epic Link: {e}")

            # Fallback to legacy Epic Link custom field (company-managed projects)
            # Epic Link is usually customfield_10014, but can vary
            epic_link_field = None
            fields = self.client.fields()
            for field in fields:
                if field["name"].lower() == "epic link":
                    epic_link_field = field["id"]
                    break

            if not epic_link_field:
                raise JiraAPIError(
                    "Epic linking failed. Neither 'parent' field nor 'Epic Link' custom field found. "
                    "Your Jira instance may not have epics enabled, or you may lack permission."
                )

            issue.update(fields={epic_link_field: epic_key})
            self._logger.info(f"Successfully linked {issue_key} to epic {epic_key} using Epic Link field")

        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError("Issue or epic not found") from e
            else:
                self._handle_jira_error(e, "Link to epic", issue_key=issue_key, epic_key=epic_key)
                raise  # Ensure type checker knows this path raises
        except (InvalidIssueError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Unexpected error linking to epic: {e}") from e
