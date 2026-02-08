"""Show command for displaying issue details."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    ConnectionError,
    InvalidIssueError,
    PermissionError,
)

console = Console()


def format_time_seconds(seconds: int | None) -> str:
    """Format time in seconds to human-readable format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "2h 30m", "45m", "0m")
    """
    if seconds is None:
        return "Not set"

    if seconds == 0:
        return "0m"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    return f"{minutes}m"


def show_issue(
    issue_key: Annotated[
        str,
        typer.Argument(help="Issue key (e.g., PROJ-123)"),
    ],
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
) -> None:
    """Show detailed information about an issue.

    Display comprehensive issue details including description, comments,
    time tracking, epic information, attachments, and more.

    Examples:

        # Show issue details
        budjira show PROJ-123

        # Show issue from specific connection
        budjira show PROJ-456 --connection my-connection
    """
    try:
        # Get active connection
        connection = get_active_connection(connection_name)

        # Get Jira client
        jira_client = JiraClient.from_connection(connection)

        # Fetch issue details
        issue = jira_client.get_issue_details(issue_key)

        # Print header
        console.print()
        header = Text()
        header.append(issue.key, style="bold cyan")
        header.append(" - ", style="dim")
        header.append(issue.summary, style="bold")
        console.print(Panel(header, border_style="cyan"))

        # Basic info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="bold yellow", width=20)
        info_table.add_column("Value")

        info_table.add_row("Type", issue.issue_type)
        info_table.add_row("Status", f"[bold]{issue.status}[/bold]")
        if issue.priority:
            info_table.add_row("Priority", issue.priority)
        info_table.add_row("Assignee", issue.assignee or "[dim]Unassigned[/dim]")
        info_table.add_row("Reporter", issue.reporter or "[dim]Unknown[/dim]")

        if issue.epic_key:
            epic_display = f"{issue.epic_key}"
            if issue.epic_name and issue.epic_name != issue.epic_key:
                epic_display += f" - {issue.epic_name}"
            info_table.add_row("Epic", epic_display)

        if issue.labels:
            info_table.add_row("Labels", ", ".join(issue.labels))

        if issue.components:
            info_table.add_row("Components", ", ".join(issue.components))

        if issue.created:
            info_table.add_row("Created", issue.created.strftime("%Y-%m-%d %H:%M"))

        if issue.updated:
            info_table.add_row("Updated", issue.updated.strftime("%Y-%m-%d %H:%M"))

        console.print(info_table)
        console.print()

        # Time tracking
        if issue.time_original_estimate or issue.time_remaining_estimate or issue.time_spent:
            console.print("[bold yellow]⏱  Time Tracking[/bold yellow]")
            time_table = Table(show_header=False, box=None, padding=(0, 2))
            time_table.add_column("Field", style="bold", width=20)
            time_table.add_column("Value")

            if issue.time_original_estimate:
                time_table.add_row("Original Estimate", format_time_seconds(issue.time_original_estimate))
            if issue.time_remaining_estimate:
                time_table.add_row("Remaining", format_time_seconds(issue.time_remaining_estimate))
            if issue.time_spent:
                time_table.add_row("Time Spent", format_time_seconds(issue.time_spent))

            console.print(time_table)
            console.print()

        # Description
        if issue.description:
            console.print("[bold yellow]📝 Description[/bold yellow]")
            console.print()
            # Render as Markdown if it looks like Markdown, otherwise plain text
            if any(marker in issue.description for marker in ["##", "###", "- [", "```"]):
                md = Markdown(issue.description)
                console.print(md)
            else:
                console.print(issue.description)
            console.print()

        # Comments
        if issue.comments:
            console.print(f"[bold yellow]💬 Comments ({len(issue.comments)})[/bold yellow]")
            console.print()

            for comment in issue.comments:
                comment_header = Text()
                comment_header.append(comment.author, style="bold cyan")
                if comment.created:
                    comment_header.append(" • ", style="dim")
                    comment_header.append(comment.created.strftime("%Y-%m-%d %H:%M"), style="dim")

                console.print(comment_header)
                console.print(comment.body)
                console.print()

        # Attachments
        if issue.attachments:
            console.print(f"[bold yellow]📎 Attachments ({len(issue.attachments)})[/bold yellow]")

            att_table = Table(show_header=True)
            att_table.add_column("Filename", style="cyan")
            att_table.add_column("Size", justify="right")
            att_table.add_column("Type", style="dim")
            att_table.add_column("Uploaded", style="dim")

            for att in issue.attachments:
                # Format file size
                size_kb = att.size / 1024
                size_display = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

                att_table.add_row(
                    att.filename,
                    size_display,
                    att.mime_type or "unknown",
                    att.created.strftime("%Y-%m-%d") if att.created else "unknown",
                )

            console.print(att_table)
            console.print()

        # Issue Links
        if issue.issuelinks:
            console.print(f"[bold yellow]🔗 Issue Links ({len(issue.issuelinks)})[/bold yellow]")

            link_table = Table(show_header=True)
            link_table.add_column("Type", style="cyan")
            link_table.add_column("Direction", style="dim")
            link_table.add_column("Issue", style="bold")
            link_table.add_column("Summary", style="dim")

            for link in issue.issuelinks:
                link_table.add_row(
                    link.link_type,
                    link.direction,
                    link.issue_key,
                    link.issue_summary or "",
                )

            console.print(link_table)
            console.print()

    except InvalidIssueError as e:
        console.print(f"❌ [red]Issue not found:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except (ConnectionError, AuthenticationError, PermissionError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        console.print("[yellow]Run with --debug for more details[/yellow]")
        raise typer.Exit(1)  # noqa: B904
