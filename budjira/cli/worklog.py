"""Worklog management commands for budjira CLI."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from budjira.cli.tempo import get_tempo_client
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
from budjira.utils.formatter import OutputFormatter
from budjira.utils.time_parser import parse_time_string

if TYPE_CHECKING:
    from budjira.models.connection import Connection
    from budjira.tempo.models import TempoWorklog

console = Console()
app = typer.Typer(help="Manage work log entries for issues")

# Tempo API hard cap per request; results at exactly this size may be incomplete.
_TEMPO_WORKLOG_LIMIT = 1000


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


@app.command(name="delete")
def delete_worklog(
    issue_key: Annotated[
        str,
        typer.Argument(help="Issue key (e.g., PROJ-123)"),
    ],
    worklog_id: Annotated[
        str,
        typer.Argument(help="Worklog ID to delete (use 'worklog list' to find IDs)"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
) -> None:
    """Delete a work log entry from an issue.

    Remove a worklog entry by its ID. Use 'budjira worklog list' to find worklog IDs.

    Examples:

        # Delete worklog with confirmation
        budjira worklog delete PROJ-123 12345

        # Delete worklog without confirmation
        budjira worklog delete PROJ-123 12345 --force
    """
    try:
        connection = get_active_connection(connection_name)
        client = JiraClient.from_connection(connection)

        # Show worklog details before confirmation
        if not force:
            worklogs = client.get_worklogs(issue_key)
            target = next((wl for wl in worklogs if str(wl.get("id")) == str(worklog_id)), None)
            if target:
                console.print(f"Worklog [cyan]{worklog_id}[/cyan] on [cyan]{issue_key}[/cyan]:")
                console.print(f"  Author: {target.get('author', 'Unknown')}")
                console.print(f"  Time:   {target.get('timeSpent', '?')}")
                if target.get("comment"):
                    console.print(f"  Comment: {target['comment']}")
            confirm = typer.confirm("Delete this worklog?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        client.delete_worklog(issue_key, worklog_id)
        console.print(f"✅ [green]Deleted worklog {worklog_id} from {issue_key}[/green]")

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
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="list")
def list_worklogs(
    ctx: typer.Context,
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
    mine: Annotated[
        bool,
        typer.Option("--mine", help="Only worklogs authored by the current user (Tempo connections only)"),
    ] = False,
    author: Annotated[
        str | None,
        typer.Option("--author", help="Filter by author accountId (Tempo connections only)"),
    ] = None,
    from_date: Annotated[
        str | None,
        typer.Option("--from", help="Only worklogs on/after this date, YYYY-MM-DD (Tempo connections only)"),
    ] = None,
    to_date: Annotated[
        str | None,
        typer.Option("--to", help="Only worklogs on/before this date, YYYY-MM-DD (Tempo connections only)"),
    ] = None,
) -> None:
    """List work log entries for an issue.

    On Tempo-enabled connections the worklogs are fetched via the Tempo API so the
    real author is shown (the Jira worklog API reports only the Tempo sync account),
    and the --mine/--author/--from/--to filters are available. On non-Tempo
    connections the Jira worklog API is used.

    Examples:

        budjira worklog list PROJ-123
        budjira worklog list PROJ-123 --mine
        budjira worklog list PROJ-123 --author 557058:abc --from 2025-10-01 --to 2025-10-31
        budjira -f json worklog list PROJ-123
    """
    output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

    if mine and author:
        console.print("[red]Error:[/red] --mine and --author cannot be used together.")
        raise typer.Exit(1)

    from_date_obj = _parse_date_option(from_date, "--from")
    to_date_obj = _parse_date_option(to_date, "--to")

    try:
        connection = get_active_connection(connection_name)
        filters_requested = mine or author is not None or from_date is not None or to_date is not None

        if connection.tempo_enabled:
            _list_worklogs_tempo(
                issue_key=issue_key,
                connection_name=connection_name,
                connection=connection,
                output_format=output_format,
                mine=mine,
                author=author,
                from_date=from_date_obj,
                to_date=to_date_obj,
            )
        else:
            if filters_requested:
                console.print(
                    "[red]Error:[/red] --mine/--author/--from/--to require a Tempo-enabled "
                    "connection. Run 'budjira connect tempo-setup' to enable Tempo."
                )
                raise typer.Exit(1)
            _list_worklogs_jira(issue_key, connection, output_format)

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


def _parse_date_option(value: str | None, option: str) -> date | None:
    """Parse a YYYY-MM-DD option value, exiting with a usage error if invalid."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid date for {option}: '{value}' (expected YYYY-MM-DD).")
        raise typer.Exit(1) from None


def _worklog_table(issue_key: str) -> Table:
    """Build the shared worklog table skeleton."""
    table = Table(title=f"Work Logs for {issue_key}", show_header=True)
    table.add_column("ID", style="dim")
    table.add_column("Author", style="cyan")
    table.add_column("Time Spent", style="green")
    table.add_column("Started", style="blue")
    table.add_column("Comment", style="white", no_wrap=False)
    return table


def _list_worklogs_tempo(
    *,
    issue_key: str,
    connection_name: str | None,
    connection: Connection,
    output_format: str,
    mine: bool,
    author: str | None,
    from_date: date | None,
    to_date: date | None,
) -> None:
    """List worklogs via the Tempo API (real author + filters)."""
    tempo_client = get_tempo_client(connection_name)
    jira_client = JiraClient.from_connection(connection)

    # Tempo requires the numeric issue ID, not the key.
    issue_id = int(jira_client.client.issue(issue_key).id)

    # Resolve the author filter to an accountId.
    account_id = author
    if mine:
        account_id = jira_client.client.myself()["accountId"]

    worklogs = tempo_client.get_worklogs(
        issue_id=issue_id,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        limit=_TEMPO_WORKLOG_LIMIT,
    )
    truncated = len(worklogs) >= _TEMPO_WORKLOG_LIMIT

    if OutputFormatter.is_json_format(output_format):
        OutputFormatter.output_json(
            {
                "issue": issue_key,
                "total": len(worklogs),
                "truncated": truncated,
                "worklogs": [_tempo_worklog_to_dict(wl) for wl in worklogs],
            }
        )
        return

    if not worklogs:
        console.print(f"[yellow]No work logs found for {issue_key}[/yellow]")
        return

    table = _worklog_table(issue_key)

    for wl in worklogs:
        hours, remainder = divmod(wl.timeSpentSeconds, 3600)
        minutes = remainder // 60
        time_spent = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        started = f"{wl.startDate.isoformat()} {(wl.startTime or '')[:5]}".strip()
        author_name = wl.author.displayName or wl.author.accountId
        table.add_row(str(wl.tempoWorklogId), author_name, time_spent, started, wl.description or "")

    console.print(table)
    console.print(f"\n[green]Total: {len(worklogs)} work log(s)[/green]")
    if truncated:
        console.print(
            f"[yellow]Result truncated at {_TEMPO_WORKLOG_LIMIT} entries; "
            "narrow the range with --from/--to to see the rest.[/yellow]"
        )


def _tempo_worklog_to_dict(wl: TempoWorklog) -> dict[str, Any]:
    """Serialize a Tempo worklog for JSON output."""
    return {
        "id": wl.tempoWorklogId,
        "author": {"accountId": wl.author.accountId, "displayName": wl.author.displayName},
        "timeSpentSeconds": wl.timeSpentSeconds,
        "startDate": wl.startDate.isoformat(),
        "startTime": wl.startTime,
        "description": wl.description,
    }


def _split_jira_started(started: str | None) -> tuple[str | None, str | None]:
    """Split a Jira 'started' timestamp into (date, time) ISO parts for JSON parity with Tempo."""
    if not started:
        return None, None
    # Normalize "+0000"-style offsets so Python 3.10's fromisoformat accepts them.
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", started.replace("Z", "+00:00"))
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return started, None
    return dt.date().isoformat(), dt.time().replace(microsecond=0).isoformat()


def _list_worklogs_jira(issue_key: str, connection: Connection, output_format: str) -> None:
    """List worklogs via the Jira worklog API (non-Tempo connections)."""
    client = JiraClient.from_connection(connection)
    worklogs = client.get_worklogs(issue_key)

    if OutputFormatter.is_json_format(output_format):
        records = []
        for wl in worklogs:
            start_date, start_time = _split_jira_started(wl.get("started"))
            records.append(
                {
                    "id": wl.get("id"),
                    "author": {"accountId": None, "displayName": wl.get("author")},
                    "timeSpentSeconds": wl.get("timeSpentSeconds"),
                    "startDate": start_date,
                    "startTime": start_time,
                    "description": wl.get("comment"),
                }
            )
        OutputFormatter.output_json(
            {
                "issue": issue_key,
                "total": len(worklogs),
                "truncated": False,
                "worklogs": records,
            }
        )
        return

    if not worklogs:
        console.print(f"[yellow]No work logs found for {issue_key}[/yellow]")
        return

    table = _worklog_table(issue_key)

    for wl in worklogs:
        wl_id = str(wl.get("id", ""))
        author = wl.get("author", "Unknown")
        time_spent = wl.get("timeSpent", "0m")
        started = wl.get("started", "")

        if started:
            start_date, start_time = _split_jira_started(started)
            if start_time:
                started_fmt = f"{start_date} {start_time[:5]}"
            else:
                started_fmt = started[:16] if len(started) > 16 else started
        else:
            started_fmt = "-"

        comment = wl.get("comment", "")
        table.add_row(wl_id, author, time_spent, started_fmt, comment)

    console.print(table)
    console.print(f"\n[green]Total: {len(worklogs)} work log(s)[/green]")
