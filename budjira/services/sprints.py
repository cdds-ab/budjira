"""Sprint service for managing Jira sprints and boards."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jira.exceptions import JIRAError

from budjira.models.sprint import Board, Sprint, SprintState
from budjira.services.base import BaseJiraService
from budjira.utils.errors import InvalidIssueError, JiraAPIError, PermissionError

if TYPE_CHECKING:
    from datetime import datetime

    from budjira.models.issue import Issue


class SprintService(BaseJiraService):
    """Service for querying Jira sprints and boards."""

    # Board types that support sprints: 'scrum' (company-managed) and
    # 'simple' (team-managed / next-gen). 'kanban' boards have no sprints.
    SPRINT_BOARD_TYPES = ("scrum", "simple")

    def get_boards(self, project_key: str) -> list[Board]:
        """Get all boards for a project.

        Returns boards of every type (scrum, simple, kanban). Filtering to
        sprint-capable boards is done by the caller (see ``detect_board``).

        Args:
            project_key: Jira project key (e.g., PROJ)

        Returns:
            List of Board objects

        Raises:
            JiraAPIError: If board retrieval fails
        """
        try:
            self._log_operation("Get boards", project_key=project_key)
            # No server-side type filter: team-managed boards report type
            # 'simple' and would be hidden by type='scrum'.
            jira_boards = self._client.boards(projectKeyOrID=project_key)
            boards = [Board.from_jira_board(b) for b in jira_boards]
            self._logger.info(f"Found {len(boards)} boards for project {project_key}")
            return boards
        except JIRAError as e:
            self._handle_jira_error(e, "Get boards", project_key=project_key)
            raise  # unreachable, satisfies type checker
        except Exception as e:
            raise JiraAPIError(f"Failed to get boards for project {project_key}: {e}") from e

    def detect_board(self, project_key: str) -> Board:
        """Auto-detect the sprint-capable board for a project.

        Accepts both company-managed (``scrum``) and team-managed (``simple``)
        boards. Works when there is exactly one such board; raises otherwise
        with guidance to use --board.

        Args:
            project_key: Jira project key

        Returns:
            Detected Board object

        Raises:
            JiraAPIError: If no sprint-capable board or multiple are found
        """
        boards = [b for b in self.get_boards(project_key) if b.board_type in self.SPRINT_BOARD_TYPES]

        if len(boards) == 0:
            raise JiraAPIError(
                f"No sprint-capable board found for project '{project_key}'. Ensure the project has a "
                f"Scrum (company-managed) or team-managed board with sprints enabled. "
                f"For team-managed projects you can also pass --sprint-id directly."
            )

        if len(boards) > 1:
            board_list = ", ".join(f"{b.name} (ID: {b.id})" for b in boards)
            raise JiraAPIError(
                f"Multiple sprint-capable boards found for project '{project_key}': {board_list}. "
                f"Use --board to specify which board to use."
            )

        return boards[0]

    def get_sprints(self, board_id: int, state: str | None = None) -> list[Sprint]:
        """Get sprints for a board.

        Args:
            board_id: Board ID
            state: Optional state filter (active, future, closed)

        Returns:
            List of Sprint objects

        Raises:
            JiraAPIError: If sprint retrieval fails
        """
        try:
            self._log_operation("Get sprints", board_id=board_id, state=state)
            jira_sprints = self._client.sprints(board_id, state=state)
            sprints = [Sprint.from_jira_sprint(s) for s in jira_sprints]
            self._logger.info(f"Found {len(sprints)} sprints for board {board_id}")
            return sprints
        except JIRAError as e:
            self._handle_jira_error(e, "Get sprints", board_id=board_id)
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get sprints for board {board_id}: {e}") from e

    def get_active_sprint(self, board_id: int) -> Sprint | None:
        """Get the active sprint for a board.

        Args:
            board_id: Board ID

        Returns:
            Active Sprint object, or None if no active sprint
        """
        sprints = self.get_sprints(board_id, state=SprintState.ACTIVE.value)
        return sprints[0] if sprints else None

    def get_sprint_issues(self, sprint_id: int, jql_filter: str | None = None, max_results: int = 200) -> list[Issue]:
        """Get issues in a sprint via JQL.

        Args:
            sprint_id: Sprint ID
            jql_filter: Optional additional JQL filter to AND with sprint filter
            max_results: Maximum number of results

        Returns:
            List of Issue objects

        Raises:
            JiraAPIError: If issue retrieval fails
        """
        from budjira.services.issues import IssueService

        jql = f"sprint = {sprint_id}"
        if jql_filter:
            jql += f" AND {jql_filter}"

        self._log_operation("Get sprint issues", sprint_id=sprint_id, jql=jql)

        issue_service = IssueService(self._client)
        return issue_service.search(jql, max_results=max_results)

    def find_sprint_by_name(self, board_id: int, name: str) -> Sprint:
        """Find a sprint by name.

        Args:
            board_id: Board ID to search in
            name: Sprint name to find (case-insensitive partial match)

        Returns:
            Sprint object

        Raises:
            JiraAPIError: If sprint not found
        """
        sprints = self.get_sprints(board_id)
        name_lower = name.lower()

        matches = [s for s in sprints if name_lower in s.name.lower()]

        if len(matches) == 0:
            raise JiraAPIError(
                f"Sprint '{name}' not found on board {board_id}. Use 'budjira sprint list' to see available sprints."
            )

        if len(matches) == 1:
            return matches[0]

        # Multiple matches - try exact match first
        exact = [s for s in matches if s.name.lower() == name_lower]
        if len(exact) == 1:
            return exact[0]

        sprint_list = ", ".join(f"'{s.name}'" for s in matches)
        raise JiraAPIError(f"Multiple sprints match '{name}': {sprint_list}. Please provide a more specific name.")

    def get_sprint(self, sprint_id: int) -> Sprint:
        """Get a single sprint by ID.

        Args:
            sprint_id: Sprint ID

        Returns:
            Sprint object

        Raises:
            InvalidIssueError: If the sprint does not exist
            JiraAPIError: If retrieval fails
        """
        try:
            self._log_operation("Get sprint", sprint_id=sprint_id)
            jira_sprint = self._client.sprint(sprint_id)
            return Sprint.from_jira_sprint(jira_sprint)
        except JIRAError as e:
            if e.status_code == 404:
                raise InvalidIssueError(
                    f"Sprint '{sprint_id}' not found. Use 'budjira sprint list' to see available sprints."
                ) from e
            self._handle_jira_error(e, "Get sprint", sprint_id=sprint_id)
            raise
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to get sprint {sprint_id}: {e}") from e

    def move_issues(self, sprint_id: int, issue_keys: list[str]) -> None:
        """Move issues into a sprint.

        Assigns one or more issues to the target sprint. Issues already in
        another sprint are moved; the operation is additive and does not
        remove issues from the sprint.

        Args:
            sprint_id: Target sprint ID
            issue_keys: Issue keys to move (e.g., ["PROJ-1", "PROJ-2"])

        Raises:
            InvalidIssueError: If the sprint or an issue does not exist
            PermissionError: If the user lacks permission to manage sprints
            JiraAPIError: If the move fails
        """
        try:
            self._log_operation("Move issues to sprint", sprint_id=sprint_id, issue_keys=issue_keys)
            self._client.add_issues_to_sprint(sprint_id=sprint_id, issue_keys=issue_keys)
            self._logger.info(f"Moved {len(issue_keys)} issue(s) into sprint {sprint_id}")
        except JIRAError as e:
            self._handle_jira_error(e, "Move issues to sprint", sprint_id=sprint_id)
            raise
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to move issues into sprint {sprint_id}: {e}") from e

    def create_sprint(
        self,
        board_id: int,
        name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        goal: str | None = None,
    ) -> Sprint:
        """Create a new sprint on a board.

        The sprint is created in the ``future`` state. Start and end dates are
        optional; they can be set later when starting the sprint.

        Args:
            board_id: Board ID to create the sprint on
            name: Sprint name
            start_date: Optional planned start date
            end_date: Optional planned end date
            goal: Optional sprint goal

        Returns:
            The created Sprint

        Raises:
            PermissionError: If the user lacks permission to manage sprints
            JiraAPIError: If creation fails
        """
        try:
            self._log_operation("Create sprint", board_id=board_id, name=name)
            jira_sprint = self._client.create_sprint(
                name=name,
                board_id=board_id,
                startDate=start_date.isoformat() if start_date else None,
                endDate=end_date.isoformat() if end_date else None,
                goal=goal,
            )
            sprint = Sprint.from_jira_sprint(jira_sprint)
            self._logger.info(f"Created sprint '{name}' (ID: {sprint.id}) on board {board_id}")
            return sprint
        except JIRAError as e:
            self._handle_jira_error(e, "Create sprint", board_id=board_id, name=name)
            raise
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to create sprint '{name}' on board {board_id}: {e}") from e

    def start_sprint(
        self,
        sprint_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Sprint:
        """Start a sprint (transition to the ``active`` state).

        Jira requires a future sprint to have a start and end date before it
        can be started. Provide them here if the sprint does not have them set.

        Args:
            sprint_id: Sprint ID
            start_date: Optional start date (required if the sprint has none)
            end_date: Optional end date (required if the sprint has none)

        Returns:
            The updated Sprint

        Raises:
            InvalidIssueError: If the sprint does not exist
            PermissionError: If the user lacks permission to manage sprints
            JiraAPIError: If the sprint cannot be started
        """
        return self._set_state(
            sprint_id,
            SprintState.ACTIVE,
            start_date=start_date,
            end_date=end_date,
        )

    def close_sprint(self, sprint_id: int) -> Sprint:
        """Close a sprint (transition to the ``closed`` state).

        Args:
            sprint_id: Sprint ID

        Returns:
            The updated Sprint

        Raises:
            InvalidIssueError: If the sprint does not exist
            PermissionError: If the user lacks permission to manage sprints
            JiraAPIError: If the sprint cannot be closed
        """
        return self._set_state(sprint_id, SprintState.CLOSED)

    def _set_state(
        self,
        sprint_id: int,
        state: SprintState,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Sprint:
        """Transition a sprint to a new state.

        Args:
            sprint_id: Sprint ID
            state: Target state
            start_date: Optional start date (used when starting a sprint)
            end_date: Optional end date (used when starting a sprint)

        Returns:
            The updated Sprint (re-fetched after the update)

        Raises:
            InvalidIssueError: If the sprint does not exist
            PermissionError: If the user lacks permission to manage sprints
            JiraAPIError: If the transition fails
        """
        try:
            self._log_operation("Set sprint state", sprint_id=sprint_id, state=state.value)
            self._client.update_sprint(
                id=sprint_id,
                state=state.value,
                startDate=start_date.isoformat() if start_date else None,
                endDate=end_date.isoformat() if end_date else None,
            )
            self._logger.info(f"Sprint {sprint_id} transitioned to '{state.value}'")
            return self.get_sprint(sprint_id)
        except JIRAError as e:
            self._handle_jira_error(e, "Set sprint state", sprint_id=sprint_id, state=state.value)
            raise
        except (InvalidIssueError, PermissionError, JiraAPIError):
            raise
        except Exception as e:
            raise JiraAPIError(f"Failed to set sprint {sprint_id} to '{state.value}': {e}") from e
