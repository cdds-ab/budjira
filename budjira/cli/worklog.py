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


@app.command(name="update")
def update_worklog(
    issue_key: Annotated[
        str,
        typer.Argument(help="Issue key the worklog belongs to (e.g., PROJ-123)"),
    ],
    worklog_id: Annotated[
        str,
        typer.Argument(help="Worklog ID to update (use 'worklog list' to find IDs)"),
    ],
    time_spent: Annotated[
        str | None,
        typer.Option("--time-spent", "-t", help="Update time spent (e.g., 2h, 30m, 2h30m)"),
    ] = None,
    started: Annotated[
        str | None,
        typer.Option(
            "--started",
            "-s",
            help="Update when work started (YYYY-MM-DD HH:MM, YYYY-MM-DD, today, yesterday)",
        ),
    ] = None,
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-c", help="Update worklog comment/description"),
    ] = None,
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
    """Update an existing work log entry on an issue.

    Modify time, date, or comment without deleting and recreating — the worklog
    ID and audit trail are preserved. Only the given fields change; everything
    else stays as is. On Tempo-enabled connections the Tempo worklog is updated
    (use the Tempo worklog ID from 'worklog list'), otherwise the native Jira
    worklog. You can only update your own worklogs.

    Examples:

        # Fix a wrong duration
        budjira worklog update PROJ-123 12345 --time-spent 6h

        # Move a booking to another day and fix the comment
        budjira worklog update PROJ-123 12345 --started yesterday --comment "Re-balanced estimate"

        # Skip the confirmation prompt
        budjira worklog update PROJ-123 12345 --time-spent 2h15m --force
    """
    try:
        if not any([time_spent, started, comment is not None]):
            console.print(
                "[yellow]No updates specified. Use --time-spent, --started, or --comment to update fields.[/yellow]"
            )
            raise typer.Exit(1)

        connection = get_active_connection(connection_name)

        if connection.tempo_enabled:
            _update_worklog_tempo(
                issue_key=issue_key,
                worklog_id=worklog_id,
                connection_name=connection_name,
                connection=connection,
                time_spent=time_spent,
                started=started,
                comment=comment,
                force=force,
            )
        else:
            _update_worklog_jira(
                issue_key=issue_key,
                worklog_id=worklog_id,
                connection=connection,
                time_spent=time_spent,
                started=started,
                comment=comment,
                force=force,
            )

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


def _check_worklog_ownership(
    jira_client: JiraClient, worklog_id: str, author_account_id: str | None, author_name: str
) -> None:
    """Refuse to update a worklog owned by someone else (pre-flight, clearer than the API 403)."""
    account_id = jira_client.client.myself()["accountId"]
    if author_account_id and author_account_id != account_id:
        raise PermissionError(f"Worklog {worklog_id} belongs to {author_name}. You may only update your own worklogs.")


def _update_worklog_jira(
    *,
    issue_key: str,
    worklog_id: str,
    connection: Connection,
    time_spent: str | None,
    started: str | None,
    comment: str | None,
    force: bool,
) -> None:
    """Update a native Jira worklog (non-Tempo connections)."""
    jira_client = JiraClient.from_connection(connection)
    current = jira_client.worklogs.get(issue_key, worklog_id)

    _check_worklog_ownership(
        jira_client,
        worklog_id,
        current.get("authorAccountId"),
        current.get("author") or "Unknown",
    )

    time_spent_minutes = parse_time_string(time_spent) if time_spent is not None else None
    started_dt = parse_datetime_string(started) if started is not None else None

    if not force:
        console.print("\n[bold]Worklog Update Preview:[/bold]")
        console.print(f"  Worklog ID: {worklog_id}")
        console.print(f"  Issue: {issue_key}")

        if time_spent_minutes is not None:
            console.print(
                f"  Time: {current['timeSpentSeconds'] / 3600:.2f}h → [cyan]{time_spent_minutes / 60:.2f}h[/cyan]"
            )
        else:
            console.print(f"  Time: {current['timeSpentSeconds'] / 3600:.2f}h (unchanged)")

        if started_dt is not None:
            console.print(f"  Started: {current.get('started')} → [cyan]{started_dt.strftime('%Y-%m-%d %H:%M')}[/cyan]")
        elif current.get("started"):
            console.print(f"  Started: {current['started']} (unchanged)")

        if comment is not None:
            console.print(f"  Comment: {current.get('comment') or '(none)'} → [cyan]{comment}[/cyan]")
        elif current.get("comment"):
            console.print(f"  Comment: {current['comment']} (unchanged)")

        console.print()
        confirm = typer.confirm("Update this worklog?")
        if not confirm:
            console.print("[yellow]Update cancelled[/yellow]")
            return

    updated = jira_client.worklogs.update(
        issue_key,
        worklog_id,
        time_spent_minutes=time_spent_minutes,
        comment=comment,
        started=started_dt,
    )

    console.print(f"✅ [green]Updated worklog {worklog_id} on {issue_key}[/green]")
    console.print(f"   Time: {updated['timeSpentSeconds'] / 3600:.2f}h")
    if updated.get("started"):
        console.print(f"   Started: {updated['started']}")
    if updated.get("comment"):
        console.print(f"   Comment: {updated['comment']}")


def _update_worklog_tempo(
    *,
    issue_key: str,
    worklog_id: str,
    connection_name: str | None,
    connection: Connection,
    time_spent: str | None,
    started: str | None,
    comment: str | None,
    force: bool,
) -> None:
    """Update a Tempo-managed worklog (Tempo-enabled connections)."""
    try:
        tempo_worklog_id = int(worklog_id)
    except ValueError:
        raise ValidationError(
            f"Invalid Tempo worklog ID: '{worklog_id}' (expected a number). "
            f"Use 'budjira worklog list {issue_key}' to find the ID."
        ) from None

    tempo_client = get_tempo_client(connection_name)
    jira_client = JiraClient.from_connection(connection)

    current_worklog = tempo_client.get_worklog(tempo_worklog_id)

    if current_worklog.issue.key and current_worklog.issue.key != issue_key:
        raise ValidationError(f"Worklog {worklog_id} belongs to {current_worklog.issue.key}, not {issue_key}.")

    _check_worklog_ownership(
        jira_client,
        worklog_id,
        current_worklog.author.accountId,
        current_worklog.author.displayName or current_worklog.author.accountId,
    )

    # Resolve issue ID: prefer Tempo's stored ID over a Jira API lookup
    issue_id = current_worklog.issue.id
    if issue_id is None:
        issue_id = int(jira_client.client.issue(issue_key).id)

    # Prepare update data (only changed fields); Tempo's PUT replaces the entry,
    # so unchanged fields are preserved from the current worklog.
    update_data: dict[str, str | int] = {}

    if time_spent is not None:
        time_spent_seconds = parse_time_string(time_spent) * 60
        update_data["time_spent_seconds"] = time_spent_seconds
    else:
        time_spent_seconds = current_worklog.timeSpentSeconds

    if started is not None:
        started_dt = parse_datetime_string(started)
        update_data["start_date"] = started_dt.strftime("%Y-%m-%d")
        update_data["start_time"] = started_dt.strftime("%H:%M:%S")
    else:
        update_data["start_date"] = current_worklog.startDate.strftime("%Y-%m-%d")
        update_data["start_time"] = current_worklog.startTime or "09:00:00"
        started_dt = datetime.combine(
            current_worklog.startDate,
            datetime.strptime(current_worklog.startTime or "09:00:00", "%H:%M:%S").time(),
        )

    if comment is not None:
        update_data["description"] = comment
    elif current_worklog.description:
        update_data["description"] = current_worklog.description

    if not force:
        console.print("\n[bold]Worklog Update Preview:[/bold]")
        console.print(f"  Worklog ID: {worklog_id}")
        console.print(f"  Issue: {issue_key}")

        if time_spent is not None:
            console.print(
                f"  Time: {current_worklog.timeSpentSeconds / 3600:.2f}h → [cyan]{time_spent_seconds / 3600:.2f}h[/cyan]"
            )
        else:
            console.print(f"  Time: {current_worklog.timeSpentSeconds / 3600:.2f}h (unchanged)")

        if started is not None:
            console.print(
                f"  Started: {current_worklog.startDate} {current_worklog.startTime} → "
                f"[cyan]{started_dt.strftime('%Y-%m-%d %H:%M:%S')}[/cyan]"
            )
        else:
            console.print(f"  Started: {current_worklog.startDate} {current_worklog.startTime} (unchanged)")

        if comment is not None:
            console.print(f"  Comment: {current_worklog.description or '(none)'} → [cyan]{comment}[/cyan]")
        elif current_worklog.description:
            console.print(f"  Comment: {current_worklog.description} (unchanged)")

        console.print()
        confirm = typer.confirm("Update this worklog?")
        if not confirm:
            console.print("[yellow]Update cancelled[/yellow]")
            return

    # Always preserve issueId and authorAccountId (Tempo's PUT replaces the entry)
    updated_worklog = tempo_client.update_worklog(
        worklog_id=tempo_worklog_id,
        issue_id=issue_id,
        author_account_id=current_worklog.author.accountId,
        **update_data,  # type: ignore[arg-type]
    )

    console.print(f"✅ [green]Updated worklog {worklog_id} on {issue_key}[/green]")
    console.print(f"   Time: {updated_worklog.timeSpentSeconds / 3600:.2f}h")
    console.print(f"   Started: {updated_worklog.startDate} {updated_worklog.startTime}")
    if updated_worklog.description:
        console.print(f"   Comment: {updated_worklog.description}")
