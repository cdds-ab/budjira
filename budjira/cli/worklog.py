"""Worklog management commands for budjira CLI."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    ConnectionError,
    InvalidIssueError,
    PermissionError,
    ValidationError,
)
from budjira.utils.time_parser import parse_time_string

console = Console()
app = typer.Typer(help="Manage work log entries for issues")


@app.command(name="add")
def add_worklog(
    issue_key: Annotated[
        str,
        typer.Argument(help="Issue key (e.g., PROJ-123)"),
    ],
    time_spent: Annotated[
        str,
        typer.Argument(help="Time spent (e.g., 2h, 30m, 2h30m, 1.5h)"),
    ],
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-c", help="Work log comment"),
    ] = None,
    started: Annotated[
        str | None,
        typer.Option(
            "--started",
            "-s",
            help="When work started (YYYY-MM-DD HH:MM, YYYY-MM-DD, today, yesterday)",
        ),
    ] = None,
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
) -> None:
    """Add a work log entry to an issue.

    Log time spent on an issue with optional comment and start time.

    Examples:

        # Log 2 hours with comment
        budjira worklog add PROJ-123 2h --comment "Implemented feature X"

        # Log work from yesterday
        budjira worklog add PROJ-456 3h30m --started yesterday --comment "Bug fixing"

        # Log work with specific datetime
        budjira worklog add PROJ-789 1h --started "2025-10-24 14:00"
    """
    try:
        # Get active connection
        connection = get_active_connection(connection_name)

        # Parse time spent
        time_spent_minutes = parse_time_string(time_spent)

        # Parse started datetime if provided
        started_datetime = None
        if started:
            started_datetime = parse_datetime_string(started)

        # Create Jira client and add worklog
        client = JiraClient.from_connection(connection)
        client.add_worklog(
            issue_key=issue_key,
            time_spent_minutes=time_spent_minutes,
            comment=comment,
            started=started_datetime,
        )

        # Success message
        console.print(f"✅ [green]Logged {time_spent} to {issue_key}[/green]")
        if comment:
            console.print(f"   Comment: {comment}")
        if started_datetime:
            console.print(f"   Started: {started_datetime.strftime('%Y-%m-%d %H:%M')}")

    except ConnectionError as e:
        console.print(f"[red]Connection Error:[/red] {e}")
        raise typer.Exit(1) from e
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error:[/red] {e}")
        raise typer.Exit(1) from e
    except InvalidIssueError as e:
        console.print(f"[red]Invalid Issue:[/red] {e}")
        raise typer.Exit(1) from e
    except PermissionError as e:
        console.print(f"[red]Permission Denied:[/red] {e}")
        raise typer.Exit(1) from e
    except ValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1) from e
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="list")
def list_worklogs(
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
    """List work log entries for an issue.

    Display all work logs for the specified issue in a table.

    Example:

        budjira worklog list PROJ-123
    """
    try:
        # Get active connection
        connection = get_active_connection(connection_name)

        # Create Jira client and fetch worklogs
        client = JiraClient.from_connection(connection)
        worklogs = client.get_worklogs(issue_key)

        if not worklogs:
            console.print(f"[yellow]No work logs found for {issue_key}[/yellow]")
            return

        # Create table
        table = Table(title=f"Work Logs for {issue_key}", show_header=True)
        table.add_column("Author", style="cyan")
        table.add_column("Time Spent", style="green")
        table.add_column("Started", style="blue")
        table.add_column("Comment", style="white", no_wrap=False)

        # Add rows
        for wl in worklogs:
            author = wl.get("author", "Unknown")
            time_spent = wl.get("timeSpent", "0m")
            started = wl.get("started", "")

            # Format started datetime
            if started:
                # Parse and format: "2025-10-25T14:30:00.000+0000" -> "2025-10-25 14:30"
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    started_fmt = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    started_fmt = started[:16] if len(started) > 16 else started
            else:
                started_fmt = "-"

            comment = wl.get("comment", "")

            table.add_row(author, time_spent, started_fmt, comment)

        console.print(table)
        console.print(f"\n[green]Total: {len(worklogs)} work log(s)[/green]")

    except ConnectionError as e:
        console.print(f"[red]Connection Error:[/red] {e}")
        raise typer.Exit(1) from e
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error:[/red] {e}")
        raise typer.Exit(1) from e
    except InvalidIssueError as e:
        console.print(f"[red]Invalid Issue:[/red] {e}")
        raise typer.Exit(1) from e
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
