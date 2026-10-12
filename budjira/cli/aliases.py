"""Quick alias commands for common status transitions."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from budjira.cli.issue import _collect_transition_fields, _execute_transition
from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError

console = Console()


def _transition_alias(issue_key: str, status: str, connection: str | None = None) -> None:
    """Transition an issue to a fixed status via the update-issue machinery.

    Uses the same transition resolution as ``budjira issue update --status``:
    the transition is matched case-insensitively against the issue's available
    transitions and required screen fields are reported, not swallowed.

    Raises:
        typer.Exit: If the transition fails
    """
    try:
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]")

        client = JiraClient.from_connection(conn)
        matched, resolved = _collect_transition_fields(
            client, issue_key, status, None, interactive=False, dry_run=False
        )
        _execute_transition(client, issue_key, matched, resolved, interactive=False)

        console.print(f"\n[green]✓[/green] {issue_key} → [cyan]{matched.to_status or status}[/cyan]")
        console.print(f"[dim]View: {conn.url}/browse/{issue_key}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        if "requires field values" in str(e):
            console.print(f'[dim]Supply fields via: budjira issue update {issue_key} --status "{status}"[/dim]')
        else:
            console.print(f"[dim]See available transitions: budjira issue transitions {issue_key}[/dim]")
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
    _transition_alias(issue_key, "In Progress", connection)


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
    _transition_alias(issue_key, "Done", connection)


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
    _transition_alias(issue_key, "Blocked", connection)


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
    _transition_alias(issue_key, "In Review", connection)
