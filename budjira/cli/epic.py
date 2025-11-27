"""CLI commands for managing Jira epics."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError
from budjira.utils.formatter import OutputFormatter

app = typer.Typer(
    name="epic",
    help="Manage and view Jira epics",
    no_args_is_help=True,
)

console = Console()


def _format_time_seconds(seconds: int | None) -> str | None:
    """Format time in seconds to human-readable string (e.g., '2h 30m').

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string or None if input is None
    """
    if seconds is None:
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h"
    if minutes > 0:
        return f"{minutes}m"
    return "0m"


@app.command("show")
def show_epic(
    ctx: typer.Context,
    epic_key: Annotated[str, typer.Argument(help="Epic key (e.g., PROJ-100)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Show epic details with all child stories.

    Displays the epic summary, status, and progress along with a table
    of all issues linked to the epic. Use --format json for machine-readable output.

    Examples:

        budjira epic show PROJ-100
        budjira --format json epic show PROJ-100
    """
    try:
        # Get format from context
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        # Get active connection
        conn = get_active_connection(connection)
        if not OutputFormatter.is_json_format(output_format):
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        # Create client
        client = JiraClient.from_connection(conn)

        # Get epic details
        epic_issues = client.search_issues(f'key = "{epic_key}"', max_results=1)
        if not epic_issues:
            if OutputFormatter.is_json_format(output_format):
                OutputFormatter.output_json({"error": "Epic not found", "epic_key": epic_key})
            else:
                console.print(f"[red]Epic '{epic_key}' not found[/red]")
            raise typer.Exit(1)

        epic = epic_issues[0]

        # Get child issues
        child_issues = client.get_epic_issues(epic_key)

        # Calculate progress
        total_issues = len(child_issues)
        done_issues = sum(1 for issue in child_issues if issue.status.lower() in ["done", "closed", "resolved"])
        progress_percent = int(done_issues / total_issues * 100) if total_issues > 0 else 0

        # JSON output
        if OutputFormatter.is_json_format(output_format):
            # Build epic data with time tracking
            base_url = str(conn.url).rstrip("/")
            epic_data: dict[str, str | int | None | dict[str, str | int | None]] = {
                "key": epic.key,
                "summary": epic.summary,
                "status": epic.status,
                "assignee": epic.assignee,
                "priority": epic.priority,
                "issue_type": epic.issue_type,
                "url": f"{base_url}/browse/{epic_key}",
            }

            # Add time tracking if available
            if epic.time_original_estimate or epic.time_remaining_estimate or epic.time_spent:
                epic_data["timetracking"] = {
                    "originalEstimateSeconds": epic.time_original_estimate,
                    "remainingEstimateSeconds": epic.time_remaining_estimate,
                    "timeSpentSeconds": epic.time_spent,
                    "originalEstimate": _format_time_seconds(epic.time_original_estimate),
                    "remainingEstimate": _format_time_seconds(epic.time_remaining_estimate),
                    "timeSpent": _format_time_seconds(epic.time_spent),
                }

            # Build stories data with time tracking
            stories: list[dict[str, str | int | None | dict[str, str | int | None]]] = []
            for issue in child_issues:
                story_data: dict[str, str | int | None | dict[str, str | int | None]] = {
                    "key": issue.key,
                    "summary": issue.summary,
                    "status": issue.status,
                    "assignee": issue.assignee,
                    "issue_type": issue.issue_type,
                    "priority": issue.priority,
                    "url": f"{base_url}/browse/{issue.key}",
                }

                # Add time tracking if available
                if issue.time_original_estimate or issue.time_remaining_estimate or issue.time_spent:
                    story_data["timetracking"] = {
                        "originalEstimateSeconds": issue.time_original_estimate,
                        "remainingEstimateSeconds": issue.time_remaining_estimate,
                        "timeSpentSeconds": issue.time_spent,
                        "originalEstimate": _format_time_seconds(issue.time_original_estimate),
                        "remainingEstimate": _format_time_seconds(issue.time_remaining_estimate),
                        "timeSpent": _format_time_seconds(issue.time_spent),
                    }

                stories.append(story_data)

            # Build progress data
            progress = {
                "total_issues": total_issues,
                "done_issues": done_issues,
                "in_progress_issues": sum(
                    1 for issue in child_issues if issue.status.lower() in ["in progress", "in review"]
                ),
                "todo_issues": total_issues - done_issues,
                "progress_percent": progress_percent,
            }

            # Output JSON
            OutputFormatter.output_json(
                {
                    "epic": epic_data,
                    "stories": stories,
                    "progress": progress,
                }
            )
            return

        # Table output (existing behavior)
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
        base_url = str(conn.url).rstrip("/")
        epic_url = f"{base_url}/browse/{epic_key}"
        console.print(f"\n[dim]View: {epic_url}[/dim]")

    except BudjiraError as e:
        if OutputFormatter.is_json_format(ctx.obj.get("format", "table") if ctx.obj else "table"):
            OutputFormatter.output_json({"error": str(e)})
        else:
            console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
