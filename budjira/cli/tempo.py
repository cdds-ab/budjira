"""Tempo Timesheets integration commands for budjira CLI."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.config.credentials import CredentialStore
from budjira.core.jira_client import JiraClient
from budjira.tempo.client import TempoClient
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    ConnectionError,
    PermissionError,
    ValidationError,
)
from budjira.utils.formatter import OutputFormatter
from budjira.utils.time_parser import parse_time_string

console = Console()
app = typer.Typer(help="Tempo Timesheets integration commands")


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

    # Get Tempo token from credential store
    cred_store = CredentialStore()
    tempo_token = cred_store.get_credential(connection.get_tempo_credential_key())

    if not tempo_token:
        raise AuthenticationError(
            f"Tempo token not found for connection '{connection.name}'. "
            f"Run 'budjira connect tempo-setup' to configure your Tempo API token."
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
) -> None:
    """Log work to Tempo Timesheets.

    Create a worklog entry in Tempo with time tracking and optional billing account.

    Examples:

        # Log 2 hours with comment
        budjira tempo log PROJ-123 2h --comment "Sizing analysis"

        # Log work from yesterday
        budjira tempo log PROJ-456 3h30m --started yesterday --comment "Client meeting"

        # Log work with specific datetime
        budjira tempo log PROJ-123 2h --started "2025-10-24 14:00"
    """
    try:
        # Get active connection
        connection = get_active_connection(connection_name)

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

    Examples:

        # List worklogs for specific issue
        budjira tempo worklogs PROJ-123

        # List worklogs for date range
        budjira tempo worklogs --from 2025-10-01 --to 2025-10-31

        # List recent worklogs (last 50)
        budjira tempo worklogs --max 50
    """
    try:
        # Get Tempo client
        tempo_client = get_tempo_client(connection_name)

        # Parse dates
        from_date_obj = date.fromisoformat(from_date) if from_date else None
        to_date_obj = date.fromisoformat(to_date) if to_date else None

        # Get format from context
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        # Get Jira client only if needed (for issue_id conversion or JSON epic fetching)
        jira_client = None
        if issue_key or OutputFormatter.is_json_format(output_format):
            connection = get_active_connection(connection_name)
            jira_client = JiraClient.from_connection(connection)

        # Convert issue_key to issue_id if provided (Tempo API requires numeric ID)
        issue_id = None
        if issue_key and jira_client:
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

        if OutputFormatter.is_json_format(output_format) and jira_client:
            # JSON output - fetch epic information if not disabled
            worklog_dicts = []
            epic_cache: dict[str, tuple[str, str] | None] = {}  # Cache: issue_key -> (epic_key, epic_name)
            issue_key_cache: dict[int, str | None] = {}  # Cache: issue_id -> issue_key (backfill)

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
                            # Fetch issue key from Jira using numeric ID
                            jira_issue = jira_client.client.issue(worklog.issue.id, fields="key")
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
            # Table output (existing behavior)
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

                table.add_row(
                    str(worklog.tempoWorklogId),
                    worklog.issue.key or "[dim]N/A[/dim]",
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
        typer.Argument(help="Tempo worklog ID to delete"),
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
    """Delete a Tempo worklog entry.

    Remove a worklog entry from Tempo Timesheets by its ID.

    Examples:

        # Delete worklog with confirmation
        budjira tempo delete-worklog 12345

        # Delete worklog without confirmation
        budjira tempo delete-worklog 12345 --force
    """
    try:
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
