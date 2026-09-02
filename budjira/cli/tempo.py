"""Tempo Timesheets integration commands for budjira CLI."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from budjira.config.secrets import resolve_tempo_token
from budjira.config.settings import get_settings
from budjira.core.jira_client import JiraClient
from budjira.tempo.client import TempoClient
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string, parse_jira_timestamp
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    ConnectionError,
    PermissionError,
    ValidationError,
)
from budjira.utils.formatter import OutputFormatter
from budjira.utils.time_parser import parse_time_string

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer(help="Tempo Timesheets integration commands")


def _check_workflow_policy(issue_key: str, connection_name: str | None) -> None:
    """Check if issue belongs to a workflow profile's planning side.

    If the issue's project key matches a planning project in any workflow profile,
    block the direct booking and suggest using 'workflow book' instead.

    Args:
        issue_key: Jira issue key (e.g., PLAN-123)
        connection_name: Active connection name (if specified)

    Raises:
        typer.Exit: If booking is blocked by workflow policy
    """
    settings = get_settings()
    profiles = settings.workflows.profiles
    if not profiles:
        return

    # Extract project key from issue key
    parts = issue_key.split("-", 1)
    if len(parts) != 2:
        return
    project_key = parts[0].upper()

    # Resolve active connection name for comparison
    if connection_name is None:
        try:
            active_conn = get_active_connection()
            connection_name = active_conn.name
        except BudjiraError:
            return

    # Check all workflow profiles
    for profile in profiles:
        if profile.planning_connection != connection_name:
            continue
        for mapping in profile.project_mappings:
            if mapping.planning_project.upper() == project_key:
                console.print(
                    f"[red]⛔[/red] [bold]{issue_key}[/bold] belongs to project "
                    f"[cyan]{project_key}[/cyan] which is the planning side of "
                    f"workflow profile [cyan]'{profile.name}'[/cyan]. "
                    f"Direct booking is not allowed.",
                )
                console.print(
                    f"\n[dim]Use instead:[/dim] "
                    f"[cyan]budjira workflow book {issue_key} <time> "
                    f"--profile {profile.name}[/cyan]",
                )
                raise typer.Exit(1)


def get_tempo_client(connection_name: str | None = None) -> TempoClient:
    """Get initialized Tempo client for active connection.

    Args:
        connection_name: Optional connection name override

    Returns:
        Initialized TempoClient

    Raises:
        ConnectionError: If Tempo is not enabled for this connection
        AuthenticationError: If Tempo token is not configured
    """
    connection = get_active_connection(connection_name)

    if not connection.tempo_enabled:
        raise ConnectionError(
            f"Tempo is not enabled for connection '{connection.name}'. "
            f"Run 'budjira connect tempo-setup' to configure Tempo integration."
        )

    # Resolve Tempo token (ref -> env -> stored)
    tempo_token = resolve_tempo_token(connection)

    if not tempo_token:
        raise AuthenticationError(
            f"Tempo token not found for connection '{connection.name}'. "
            "Set tempo_token_ref (env:/pass:/file:), export BUDJIRA_TEMPO_TOKEN, "
            "or run 'budjira connect tempo-setup' to configure your Tempo API token."
        )

    return TempoClient(tempo_token=tempo_token)


@app.command(name="log")
def tempo_log_worklog(
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
        typer.Option("--comment", "-c", help="Worklog comment/description"),
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
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Bypass workflow policy check (allow direct booking on planning connection)",
        ),
    ] = False,
) -> None:
    """Log work to Tempo Timesheets.

    Create a worklog entry in Tempo with time tracking and optional billing account.
    On connections without Tempo (Tempo: Disabled), a native Jira worklog is
    created instead.

    If the issue belongs to a workflow profile's planning side, direct booking
    is blocked. Use 'budjira workflow book' instead, or --force to bypass.

    Examples:

        # Log 2 hours with comment
        budjira tempo log PROJ-123 2h --comment "Sizing analysis"

        # Log work from yesterday
        budjira tempo log PROJ-456 3h30m --started yesterday --comment "Client meeting"

        # Log work with specific datetime
        budjira tempo log PROJ-123 2h --started "2025-10-24 14:00"

        # Bypass workflow policy
        budjira tempo log PLAN-123 2h --force
    """
    try:
        # Check workflow booking policy (unless --force)
        if not force:
            _check_workflow_policy(issue_key, connection_name)

        # Get active connection
        connection = get_active_connection(connection_name)

        # Connections without Tempo log a native Jira worklog instead
        if not connection.tempo_enabled:
            _log_worklog_native(issue_key, time_spent, comment, started, connection)
            return

        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Get Jira client to retrieve author account ID and issue ID
        jira_client = JiraClient.from_connection(connection)
        myself = jira_client.client.myself()
        author_account_id = myself["accountId"]

        # Get issue from Jira to retrieve numeric ID (Tempo requires issueId, not issueKey)
        issue = jira_client.client.issue(issue_key)
        issue_id = int(issue.id)  # Jira returns as string, Tempo needs int

        # Parse time spent (convert minutes to seconds)
        time_spent_minutes = parse_time_string(time_spent)
        time_spent_seconds = time_spent_minutes * 60

        # Parse started datetime
        started_dt = parse_datetime_string(started) if started else datetime.now()

        # Extract date and time
        start_date = started_dt.strftime("%Y-%m-%d")
        start_time = started_dt.strftime("%H:%M:%S")

        # Create worklog
        worklog = tempo_client.create_worklog(
            issue_id=issue_id,
            time_spent_seconds=time_spent_seconds,
            start_date=start_date,
            start_time=start_time,
            author_account_id=author_account_id,
            description=comment,
        )

        # Success message
        console.print(f"✅ [green]Logged {time_spent} to {issue_key} via Tempo[/green]")
        if comment:
            console.print(f"   Comment: {comment}")
        console.print(f"   Started: {started_dt.strftime('%Y-%m-%d %H:%M')}")
        console.print(f"   Tempo Worklog ID: {worklog.tempoWorklogId}")

    except (ConnectionError, AuthenticationError, PermissionError, ValidationError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        console.print("[yellow]Run with --debug for more details[/yellow]")
        raise typer.Exit(1)  # noqa: B904


@app.command(name="worklogs")
def tempo_list_worklogs(
    ctx: typer.Context,
    issue_key: Annotated[
        str | None,
        typer.Argument(help="Issue key to filter worklogs (optional)"),
    ] = None,
    from_date: Annotated[
        str | None,
        typer.Option("--from", help="Start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        str | None,
        typer.Option("--to", help="End date (YYYY-MM-DD)"),
    ] = None,
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of results"),
    ] = 50,
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
    no_epic: Annotated[
        bool,
        typer.Option("--no-epic", help="Skip epic information (faster, JSON format only)"),
    ] = False,
) -> None:
    """List Tempo worklog entries.

    Display worklog entries from Tempo Timesheets with optional filters.
    On connections without Tempo (Tempo: Disabled), native Jira worklogs are
    listed instead: with an issue key via the issue's worklogs, without one via
    a user-scoped search (worklogAuthor = currentUser(), default range: current
    month).

    Examples:

        # List worklogs for specific issue
        budjira tempo worklogs PROJ-123

        # List worklogs for date range
        budjira tempo worklogs --from 2025-10-01 --to 2025-10-31

        # List recent worklogs (last 50)
        budjira tempo worklogs --max 50
    """
    try:
        connection = get_active_connection(connection_name)

        # Parse dates
        from_date_obj = date.fromisoformat(from_date) if from_date else None
        to_date_obj = date.fromisoformat(to_date) if to_date else None

        # Get format from context
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        # Connections without Tempo read native Jira worklogs instead
        if not connection.tempo_enabled:
            _list_worklogs_native(
                issue_key=issue_key,
                connection=connection,
                output_format=output_format,
                from_date=from_date_obj,
                to_date=to_date_obj,
                max_results=max_results,
                no_epic=no_epic,
            )
            return

        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Get Jira client - needed for:
        # 1. issue_id conversion when filtering by issue_key
        # 2. JSON epic fetching
        # 3. Table output issue_key backfill (Tempo API often returns null issue.key)
        jira_client = JiraClient.from_connection(connection)

        # Convert issue_key to issue_id if provided (Tempo API requires numeric ID)
        issue_id = None
        if issue_key:
            issue = jira_client.client.issue(issue_key)
            issue_id = int(issue.id)

        # Fetch worklogs
        worklogs = tempo_client.get_worklogs(
            from_date=from_date_obj,
            to_date=to_date_obj,
            issue_id=issue_id,
            limit=max_results,
        )

        if not worklogs:
            if OutputFormatter.is_json_format(output_format):
                OutputFormatter.output_json({"total": 0, "worklogs": []})
            else:
                console.print("[yellow]No worklogs found matching the criteria[/yellow]")
            return

        # Cache for issue_key backfill (Tempo API often returns null issue.key)
        # Used by both JSON and table output
        issue_key_cache: dict[int, str | None] = {}  # Cache: issue_id -> issue_key

        if OutputFormatter.is_json_format(output_format):
            # JSON output - fetch epic information if not disabled
            worklog_dicts = []
            epic_cache: dict[str, tuple[str, str] | None] = {}  # Cache: issue_key -> (epic_key, epic_name)

            for worklog in worklogs:
                # Convert seconds to hours/minutes display
                hours = worklog.timeSpentSeconds // 3600
                minutes = (worklog.timeSpentSeconds % 3600) // 60
                time_display = f"{hours}h {minutes}m" if hours else f"{minutes}m"

                # Backfill issue_key from Jira API if Tempo returned null
                issue_key = worklog.issue.key
                if issue_key is None and worklog.issue.id is not None:
                    # Check cache first to minimize API calls
                    if worklog.issue.id not in issue_key_cache:
                        try:
                            # Fetch issue key from Jira using numeric ID (as string)
                            jira_issue = jira_client.client.issue(str(worklog.issue.id), fields="key")
                            issue_key_cache[worklog.issue.id] = jira_issue.key
                        except Exception:
                            # If fetch fails, cache None to avoid retries
                            issue_key_cache[worklog.issue.id] = None

                    # Use cached value (either key or None)
                    issue_key = issue_key_cache.get(worklog.issue.id)

                # Base worklog dict
                worklog_dict = {
                    "id": worklog.tempoWorklogId,
                    "issue_key": issue_key,
                    "time_spent_seconds": worklog.timeSpentSeconds,
                    "time_spent_display": time_display,
                    "date": worklog.startDate.isoformat(),
                    "author_account_id": worklog.author.accountId,
                    "author_display_name": worklog.author.displayName,
                    "description": worklog.description or "",
                }

                # Add epic information if enabled and issue has a key
                if not no_epic and issue_key:
                    if issue_key not in epic_cache:
                        # Fetch epic info and cache it
                        try:
                            epic_info = jira_client.get_issue_epic(issue_key)
                            epic_cache[issue_key] = epic_info
                        except Exception:
                            # If epic fetch fails, cache None
                            epic_cache[issue_key] = None

                    # Add epic fields
                    epic_info = epic_cache.get(issue_key)
                    if epic_info:
                        worklog_dict["epic_key"] = epic_info[0]
                        worklog_dict["epic_name"] = epic_info[1]
                    else:
                        worklog_dict["epic_key"] = None
                        worklog_dict["epic_name"] = None

                worklog_dicts.append(worklog_dict)

            # Output JSON
            output = {"total": len(worklog_dicts), "worklogs": worklog_dicts}
            OutputFormatter.output_json(output)

        else:
            # Table output - with issue_key backfill from Jira API
            table = Table(title=f"Tempo Worklogs ({len(worklogs)} entries)")
            table.add_column("ID", style="cyan")
            table.add_column("Issue", style="magenta")
            table.add_column("Time Spent", style="green")
            table.add_column("Date", style="blue")
            table.add_column("Author", style="yellow")
            table.add_column("Description", style="white", max_width=40)

            for worklog in worklogs:
                # Convert seconds to hours/minutes
                hours = worklog.timeSpentSeconds // 3600
                minutes = (worklog.timeSpentSeconds % 3600) // 60
                time_display = f"{hours}h {minutes}m" if hours else f"{minutes}m"

                # Backfill issue_key from Jira API if Tempo returned null
                display_issue_key = worklog.issue.key
                if display_issue_key is None and worklog.issue.id is not None:
                    # Check cache first to minimize API calls
                    if worklog.issue.id not in issue_key_cache:
                        try:
                            # Fetch issue key from Jira using numeric ID (as string)
                            jira_issue = jira_client.client.issue(str(worklog.issue.id), fields="key")
                            issue_key_cache[worklog.issue.id] = jira_issue.key
                        except Exception:
                            # If fetch fails, cache None to avoid retries
                            issue_key_cache[worklog.issue.id] = None

                    # Use cached value (either key or None)
                    display_issue_key = issue_key_cache.get(worklog.issue.id)

                table.add_row(
                    str(worklog.tempoWorklogId),
                    display_issue_key or "[dim]N/A[/dim]",
                    time_display,
                    worklog.startDate.strftime("%Y-%m-%d"),
                    worklog.author.displayName or worklog.author.accountId[:8],
                    worklog.description or "",
                )

            console.print(table)

    except (ConnectionError, AuthenticationError, PermissionError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except ValueError as e:
        console.print(f"❌ [red]Invalid date format:[/red] {e}")
        console.print("[yellow]Use YYYY-MM-DD format (e.g., 2025-10-25)[/yellow]")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904


@app.command(name="delete-worklog")
def tempo_delete_worklog(
    worklog_id: Annotated[
        int,
        typer.Argument(help="Worklog ID to delete (Tempo or native Jira)"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
    issue_key: Annotated[
        str | None,
        typer.Option(
            "--issue",
            help="Issue key the worklog belongs to (required on connections without Tempo; "
            "native Jira worklog IDs are per-issue)",
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
    """Delete a worklog entry.

    Remove a worklog entry from Tempo Timesheets by its ID. On connections
    without Tempo (Tempo: Disabled), the native Jira worklog is deleted
    instead — pass --issue there, since native worklog IDs are per-issue.

    Examples:

        # Delete worklog with confirmation
        budjira tempo delete-worklog 12345

        # Delete worklog without confirmation
        budjira tempo delete-worklog 12345 --force

        # Delete a native Jira worklog (connection without Tempo)
        budjira tempo delete-worklog 67890 --issue PROJ-123
    """
    try:
        connection = get_active_connection(connection_name)

        # Connections without Tempo delete native Jira worklogs instead
        if not connection.tempo_enabled:
            _delete_worklog_native(worklog_id, issue_key, force, connection)
            return

        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Confirm deletion unless --force is used
        if not force:
            confirm = typer.confirm(f"Delete Tempo worklog {worklog_id}?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Delete worklog
        tempo_client.delete_worklog(worklog_id)
        console.print(f"✅ [green]Deleted Tempo worklog {worklog_id}[/green]")

    except (ConnectionError, AuthenticationError, PermissionError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904


@app.command(name="update-worklog")
def tempo_update_worklog(
    worklog_id: Annotated[
        int,
        typer.Argument(help="Tempo worklog ID to update"),
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
    issue_key: Annotated[
        str | None,
        typer.Option(
            "--issue",
            help="Issue key the worklog belongs to (required on connections without Tempo; "
            "native Jira worklog IDs are per-issue)",
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
    """Update an existing worklog entry.

    Modify time, date, or comment without deleting and recreating.
    Preserves worklog ID and audit trail. On connections without Tempo
    (Tempo: Disabled), the native Jira worklog is updated instead — pass
    --issue there, since native worklog IDs are per-issue.

    Examples:

        # Update only the date
        budjira tempo update-worklog 642 --started 2025-10-28

        # Update time and comment
        budjira tempo update-worklog 642 --time-spent 4h --comment "Revised estimate"

        # Update all fields
        budjira tempo update-worklog 642 --started "2025-10-28 14:00" --time-spent 3h30m --comment "Final"

        # Force update (no confirmation)
        budjira tempo update-worklog 642 --started yesterday --force

        # Update a native Jira worklog (connection without Tempo)
        budjira tempo update-worklog 67890 --issue PROJ-123 --time-spent 3h
    """
    try:
        # Check if at least one field is being updated
        if not any([time_spent, started, comment is not None]):
            console.print(
                "[yellow]No updates specified. Use --time-spent, --started, or --comment to update fields.[/yellow]"
            )
            raise typer.Exit(1)

        connection = get_active_connection(connection_name)

        # Connections without Tempo update native Jira worklogs instead
        if not connection.tempo_enabled:
            _update_worklog_native(worklog_id, issue_key, time_spent, started, comment, force, connection)
            return

        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Fetch current worklog to get existing values
        current_worklog = tempo_client.get_worklog(worklog_id)

        # Resolve issue ID: prefer Jira API lookup over Tempo's stored ID
        issue_id = current_worklog.issue.id
        if issue_id is None and current_worklog.issue.key:
            jira_client = JiraClient.from_connection(connection)
            jira_issue = jira_client.client.issue(current_worklog.issue.key)
            issue_id = int(jira_issue.id)
        elif issue_id is None:
            console.print("[red]Error:[/red] Worklog has no associated issue. Cannot update.")
            raise typer.Exit(1)

        # Prepare update data (only changed fields)
        update_data: dict[str, str | int] = {}

        # Parse and prepare time_spent if provided
        if time_spent is not None:
            time_spent_minutes = parse_time_string(time_spent)
            time_spent_seconds = time_spent_minutes * 60
            update_data["time_spent_seconds"] = time_spent_seconds
        else:
            time_spent_seconds = current_worklog.timeSpentSeconds

        # Parse and prepare started datetime if provided
        if started is not None:
            started_dt = parse_datetime_string(started)
            update_data["start_date"] = started_dt.strftime("%Y-%m-%d")
            update_data["start_time"] = started_dt.strftime("%H:%M:%S")
        else:
            # Preserve existing values
            update_data["start_date"] = current_worklog.startDate.strftime("%Y-%m-%d")
            update_data["start_time"] = current_worklog.startTime or "09:00:00"
            started_dt = datetime.combine(
                current_worklog.startDate,
                datetime.strptime(current_worklog.startTime or "09:00:00", "%H:%M:%S").time(),
            )

        # Prepare comment if provided
        if comment is not None:
            update_data["description"] = comment
        else:
            # Preserve existing description
            if current_worklog.description:
                update_data["description"] = current_worklog.description

        # Show confirmation unless --force is used
        if not force:
            console.print("\n[bold]Worklog Update Preview:[/bold]")
            console.print(f"  Worklog ID: {worklog_id}")
            console.print(f"  Issue: {current_worklog.issue.key}")

            # Show what's changing
            if time_spent is not None:
                old_hours = current_worklog.timeSpentSeconds / 3600
                new_hours = time_spent_seconds / 3600
                console.print(f"  Time: {old_hours:.2f}h → [cyan]{new_hours:.2f}h[/cyan]")
            else:
                hours = current_worklog.timeSpentSeconds / 3600
                console.print(f"  Time: {hours:.2f}h (unchanged)")

            if started is not None:
                console.print(
                    f"  Started: {current_worklog.startDate} {current_worklog.startTime} → "
                    f"[cyan]{started_dt.strftime('%Y-%m-%d %H:%M:%S')}[/cyan]"
                )
            else:
                console.print(f"  Started: {current_worklog.startDate} {current_worklog.startTime} (unchanged)")

            if comment is not None:
                old_comment = current_worklog.description or "(none)"
                console.print(f"  Comment: {old_comment} → [cyan]{comment}[/cyan]")
            elif current_worklog.description:
                console.print(f"  Comment: {current_worklog.description} (unchanged)")

            console.print()
            confirm = typer.confirm("Update this worklog?")
            if not confirm:
                console.print("[yellow]Update cancelled[/yellow]")
                return

        # Perform update (always preserve issueId and authorAccountId)
        updated_worklog = tempo_client.update_worklog(
            worklog_id=worklog_id,
            issue_id=issue_id,
            author_account_id=current_worklog.author.accountId,
            **update_data,  # type: ignore[arg-type]
        )

        # Success message
        console.print(f"✅ [green]Updated Tempo worklog {worklog_id}[/green]")
        console.print(f"   Issue: {updated_worklog.issue.key}")
        console.print(f"   Time: {updated_worklog.timeSpentSeconds / 3600:.2f}h")
        console.print(f"   Started: {updated_worklog.startDate} {updated_worklog.startTime}")
        if updated_worklog.description:
            console.print(f"   Comment: {updated_worklog.description}")

    except (ConnectionError, AuthenticationError, PermissionError, ValidationError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        console.print("[yellow]Run with --debug for more details[/yellow]")
        raise typer.Exit(1)  # noqa: B904


@app.command(name="accounts")
def tempo_list_accounts(
    max_results: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of results"),
    ] = 50,
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
) -> None:
    """List Tempo accounts for billing and project tracking.

    Display available Tempo accounts that can be used when logging work.

    Examples:

        # List all Tempo accounts
        budjira tempo accounts

        # Limit results
        budjira tempo accounts --max 20
    """
    try:
        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Fetch accounts
        accounts = tempo_client.get_accounts(limit=max_results)

        if not accounts:
            console.print("[yellow]No Tempo accounts found[/yellow]")
            return

        # Create table
        table = Table(title=f"Tempo Accounts ({len(accounts)} entries)")
        table.add_column("Key", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Global", style="yellow")

        for account in accounts:
            table.add_row(
                account.key,
                account.name,
                account.status,
                "Yes" if account.global_ else "No",
            )

        console.print(table)

    except (ConnectionError, AuthenticationError, PermissionError) as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except BudjiraError as e:
        console.print(f"❌ [red]Error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904
    except Exception as e:
        console.print(f"❌ [red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)  # noqa: B904


# --- Native Jira worklog fallbacks (connections without Tempo) ---

if TYPE_CHECKING:
    from budjira.models.connection import Connection


def _log_worklog_native(
    issue_key: str,
    time_spent: str,
    comment: str | None,
    started: str | None,
    connection: Connection,
) -> None:
    """Log a native Jira worklog (fallback for connections without Tempo)."""
    jira_client = JiraClient.from_connection(connection)

    time_spent_minutes = parse_time_string(time_spent)
    started_dt = parse_datetime_string(started) if started else datetime.now()

    worklog_id = jira_client.worklogs.add(issue_key, time_spent_minutes, comment, started_dt)

    console.print(f"✅ [green]Logged {time_spent} to {issue_key} (native Jira worklog)[/green]")
    if comment:
        console.print(f"   Comment: {comment}")
    console.print(f"   Started: {started_dt.strftime('%Y-%m-%d %H:%M')}")
    console.print(f"   Worklog ID: {worklog_id}")


def _list_worklogs_native(
    *,
    issue_key: str | None,
    connection: Connection,
    output_format: str,
    from_date: date | None,
    to_date: date | None,
    max_results: int,
    no_epic: bool,
) -> None:
    """List native Jira worklogs (fallback for connections without Tempo).

    With an issue key, the issue's worklogs are read directly. Without one, a
    user-scoped JQL search (worklogAuthor = currentUser()) finds the issues —
    the date range defaults to the current month when --from is not given.
    Only worklogs authored by the current user are shown.
    """
    jira_client = JiraClient.from_connection(connection)
    myself = jira_client.client.myself()
    account_id = myself["accountId"]

    if issue_key:
        worklogs_by_issue = {issue_key: jira_client.worklogs.list(issue_key)}
    else:
        # User-scoped: find issues with my worklogs via JQL
        effective_from = from_date or date.today().replace(day=1)
        jql = f"worklogAuthor = currentUser() AND worklogDate >= '{effective_from.isoformat()}'"
        if to_date:
            jql += f" AND worklogDate <= '{to_date.isoformat()}'"
        logger.debug(f"Native worklog search JQL: {jql}")

        issues = jira_client.client.search_issues(jql, fields="key", maxResults=200)
        logger.debug(f"Native worklog search: {len(issues)} issue(s) to scan")
        worklogs_by_issue = {}
        for issue in issues:
            entries = jira_client.worklogs.list(issue.key)
            if entries:
                worklogs_by_issue[issue.key] = entries

    # Flatten, filter by author + date range, newest first
    records: list[tuple[str, dict[str, Any], datetime]] = []
    for key, worklogs in worklogs_by_issue.items():
        for worklog in worklogs:
            if worklog.get("authorAccountId") and worklog["authorAccountId"] != account_id:
                continue
            started_dt = parse_jira_timestamp(worklog.get("started"))
            if started_dt is None:
                continue
            started_date = started_dt.date()
            if from_date and started_date < from_date:
                continue
            if to_date and started_date > to_date:
                continue
            records.append((key, worklog, started_dt))

    records.sort(key=lambda record: record[2], reverse=True)
    records = records[:max_results]

    if not records:
        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json({"total": 0, "worklogs": []})
        else:
            console.print("[yellow]No worklogs found matching the criteria[/yellow]")
        return

    if OutputFormatter.is_json_format(output_format):
        epic_cache: dict[str, tuple[str, str] | None] = {}
        worklog_dicts = []
        for key, worklog, started_dt in records:
            hours, remainder = divmod(worklog["timeSpentSeconds"], 3600)
            worklog_dict = {
                "id": worklog["id"],
                "issue_key": key,
                "time_spent_seconds": worklog["timeSpentSeconds"],
                "time_spent_display": f"{hours}h {remainder // 60}m" if hours else f"{remainder // 60}m",
                "date": started_dt.date().isoformat(),
                "author_account_id": worklog.get("authorAccountId"),
                "author_display_name": worklog["author"],
                "description": worklog.get("comment", ""),
            }

            if not no_epic:
                if key not in epic_cache:
                    try:
                        epic_cache[key] = jira_client.get_issue_epic(key)
                    except Exception:
                        epic_cache[key] = None
                epic_info = epic_cache[key]
                worklog_dict["epic_key"] = epic_info[0] if epic_info else None
                worklog_dict["epic_name"] = epic_info[1] if epic_info else None

            worklog_dicts.append(worklog_dict)

        OutputFormatter.output_json({"total": len(worklog_dicts), "worklogs": worklog_dicts})
        return

    table = Table(title=f"Jira Worklogs ({len(records)} entries)")
    table.add_column("ID", style="cyan")
    table.add_column("Issue", style="magenta")
    table.add_column("Time Spent", style="green")
    table.add_column("Date", style="blue")
    table.add_column("Author", style="yellow")
    table.add_column("Description", style="white", max_width=40)

    for key, worklog, started_dt in records:
        hours, remainder = divmod(worklog["timeSpentSeconds"], 3600)
        time_display = f"{hours}h {remainder // 60}m" if hours else f"{remainder // 60}m"
        table.add_row(
            str(worklog["id"]),
            key,
            time_display,
            started_dt.strftime("%Y-%m-%d"),
            worklog["author"],
            worklog.get("comment", ""),
        )

    console.print(table)


def _delete_worklog_native(
    worklog_id: int,
    issue_key: str | None,
    force: bool,
    connection: Connection,
) -> None:
    """Delete a native Jira worklog (fallback for connections without Tempo)."""
    if not issue_key:
        raise ValidationError(
            "--issue is required on connections without Tempo: native worklog IDs are per-issue. "
            "Use 'budjira worklog list <KEY>' to find the worklog ID."
        )

    jira_client = JiraClient.from_connection(connection)

    if not force:
        confirm = typer.confirm(f"Delete worklog {worklog_id} on {issue_key}?")
        if not confirm:
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    jira_client.worklogs.delete(issue_key, str(worklog_id))
    console.print(f"✅ [green]Deleted worklog {worklog_id} from {issue_key} (native Jira)[/green]")


def _update_worklog_native(
    worklog_id: int,
    issue_key: str | None,
    time_spent: str | None,
    started: str | None,
    comment: str | None,
    force: bool,
    connection: Connection,
) -> None:
    """Update a native Jira worklog (fallback for connections without Tempo)."""
    if not issue_key:
        raise ValidationError(
            "--issue is required on connections without Tempo: native worklog IDs are per-issue. "
            "Use 'budjira worklog list <KEY>' to find the worklog ID."
        )

    jira_client = JiraClient.from_connection(connection)
    current = jira_client.worklogs.get(issue_key, str(worklog_id))

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
        str(worklog_id),
        time_spent_minutes=time_spent_minutes,
        comment=comment,
        started=started_dt,
    )

    console.print(f"✅ [green]Updated worklog {worklog_id} on {issue_key} (native Jira)[/green]")
    console.print(f"   Time: {updated['timeSpentSeconds'] / 3600:.2f}h")
    if updated.get("started"):
        console.print(f"   Started: {updated['started']}")
    if updated.get("comment"):
        console.print(f"   Comment: {updated['comment']}")
