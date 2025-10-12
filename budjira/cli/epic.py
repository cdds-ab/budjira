"""CLI commands for managing Jira epics."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError

app = typer.Typer(
    name="epic",
    help="Manage and view Jira epics",
    no_args_is_help=True,
)

console = Console()


@app.command("show")
def show_epic(
    epic_key: Annotated[str, typer.Argument(help="Epic key (e.g., PROJ-100)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Show epic details with all child stories.

    Displays the epic summary, status, and progress along with a table
    of all issues linked to the epic.

    Example:

        budjira epic show PROJ-100
    """
    try:
        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        # Create client
        client = JiraClient.from_connection(conn)

        # Get epic details
        epic_issues = client.search_issues(f'key = "{epic_key}"', max_results=1)
        if not epic_issues:
            console.print(f"[red]Epic '{epic_key}' not found[/red]")
            raise typer.Exit(1)

        epic = epic_issues[0]

        # Get child issues
        child_issues = client.get_epic_issues(epic_key)

        # Calculate progress
        total_issues = len(child_issues)
        done_issues = sum(1 for issue in child_issues if issue.status.lower() in ["done", "closed", "resolved"])
        progress_percent = int(done_issues / total_issues * 100) if total_issues > 0 else 0

        # Display epic header
        console.print(f"[cyan bold]Epic: {epic_key} - {epic.summary}[/cyan bold]")
        console.print(f"[dim]Status:[/dim] {epic.status}")
        console.print(f"[dim]Progress:[/dim] {done_issues}/{total_issues} issues done ({progress_percent}%)")

        if not child_issues:
            console.print("\n[yellow]No issues linked to this epic[/yellow]")
            return

        # Display child issues in table
        console.print(f"\n[bold]Linked Issues ({total_issues}):[/bold]\n")

        table = Table(show_header=True)
        table.add_column("Status", style="dim", width=3)
        table.add_column("Key", style="cyan")
        table.add_column("Summary")
        table.add_column("Assignee", style="dim")
        table.add_column("Type", style="dim")

        for issue in child_issues:
            # Status icon
            status_lower = issue.status.lower()
            if status_lower in ["done", "closed", "resolved"]:
                status_icon = "✅"
            elif status_lower in ["in progress", "in review"]:
                status_icon = "🔄"
            else:
                status_icon = "📋"

            table.add_row(
                status_icon,
                issue.key,
                issue.summary[:60] + "..." if len(issue.summary) > 60 else issue.summary,
                issue.assignee or "Unassigned",
                issue.issue_type,
            )

        console.print(table)

        # Show epic URL
        epic_url = f"{conn.url}/browse/{epic_key}"
        console.print(f"\n[dim]View: {epic_url}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
