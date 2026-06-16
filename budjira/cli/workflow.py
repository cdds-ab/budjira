"""Quick workflow alias commands for common status transitions."""

from typing import Annotated

import typer
from rich.console import Console

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError

console = Console()


def _transition_issue(issue_key: str, status: str, connection: str | None = None) -> None:
    """Helper function to transition an issue to a specific status.

    Args:
        issue_key: Issue key (e.g., PROJ-123)
        status: Target status name
        connection: Optional connection name

    Raises:
        typer.Exit: If the transition fails
    """
    try:
        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]")

        # Create client
        client = JiraClient.from_connection(conn)

        # Perform status transition
        client.transition_issue(issue_key, status)

        # Display success message
        console.print(f"\n[green]✓[/green] {issue_key} → [cyan]{status}[/cyan]")

        # Show issue URL
        issue_url = f"{conn.url}/browse/{issue_key}"
        console.print(f"[dim]View: {issue_url}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


def start_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Start working on an issue (transition to In Progress).

    Quick alias for: budjira issue update ISSUE-KEY --status "In Progress"

    Example:

        budjira start PROJ-123
    """
    _transition_issue(issue_key, "In Progress", connection)


def done_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Mark an issue as done (transition to Done).

    Quick alias for: budjira issue update ISSUE-KEY --status "Done"

    Example:

        budjira done PROJ-123
    """
    _transition_issue(issue_key, "Done", connection)


def block_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Block an issue (transition to Blocked).

    Quick alias for: budjira issue update ISSUE-KEY --status "Blocked"

    Example:

        budjira block PROJ-123
    """
    _transition_issue(issue_key, "Blocked", connection)


def review_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Send an issue to review (transition to In Review).

    Quick alias for: budjira issue update ISSUE-KEY --status "In Review"

    Example:

        budjira review PROJ-123
    """
    _transition_issue(issue_key, "In Review", connection)
