"""CLI commands for querying Jira sprints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.models.sprint import Sprint, SprintState
from budjira.utils.connection import get_active_connection
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import BudjiraError
from budjira.utils.formatter import OutputFormatter

if TYPE_CHECKING:
    from budjira.models.connection import Connection

app = typer.Typer(
    name="sprint",
    help="Query sprints and sprint contents",
    no_args_is_help=True,
)

console = Console()


def _resolve_board_id(
    client: JiraClient,
    board: int | None,
    connection_board_id: int | None,
    project_key: str,
) -> int:
    """Resolve board ID from --board flag, connection config, or auto-detection.

    Args:
        client: Jira client
        board: Explicit --board flag value
        connection_board_id: board_id from connection config
        project_key: Project key for auto-detection

    Returns:
        Board ID
    """
    if board is not None:
        return board
    if connection_board_id is not None:
        return connection_board_id
    detected = client.sprints.detect_board(project_key)
    return detected.id


def _resolve_sprint(
    client: JiraClient,
    board_id: int,
    sprint_name: str | None,
) -> Sprint:
    """Resolve a sprint by name or get the active sprint.

    Args:
        client: Jira client
        board_id: Board ID
        sprint_name: Optional sprint name (None = active sprint)

    Returns:
        Sprint object

    Raises:
        typer.Exit: If sprint not found
    """
    if sprint_name:
        return client.sprints.find_sprint_by_name(board_id, sprint_name)

    active = client.sprints.get_active_sprint(board_id)
    if not active:
        raise BudjiraError(
            f"No active sprint found on board {board_id}. Specify a sprint name or use --state to filter."
        )
    return active


def _resolve_target(
    client: JiraClient,
    conn: Connection,
    board: int | None,
    sprint_name: str | None,
    sprint_id: int | None,
    allow_active: bool,
) -> Sprint:
    """Resolve a target sprint by ID, name, or (optionally) the active sprint.

    Board detection is performed lazily: when an explicit ``sprint_id`` is given
    the sprint is fetched directly via the agile API and no board is resolved at
    all. This is what makes ``--sprint-id`` work for team-managed projects whose
    board type is not auto-detected.

    Args:
        client: Jira client
        conn: Active connection (provides board_id default and project key)
        board: Explicit --board flag value (overrides detection)
        sprint_id: Explicit sprint ID (highest priority; skips board resolution)
        sprint_name: Sprint name (case-insensitive partial match)
        allow_active: If True and neither id nor name given, fall back to the
            active sprint; otherwise require an explicit target

    Returns:
        Resolved Sprint

    Raises:
        BudjiraError: If no target can be resolved
    """
    # --sprint-id needs no board: fetch directly via the agile sprint endpoint.
    if sprint_id is not None:
        return client.sprints.get_sprint(sprint_id)

    board_id = _resolve_board_id(client, board, conn.board_id, conn.project_key)
    if sprint_name:
        return client.sprints.find_sprint_by_name(board_id, sprint_name)
    if allow_active:
        return _resolve_sprint(client, board_id, None)
    raise BudjiraError("No sprint specified. Provide a sprint name or use --sprint-id.")


def _emit_error(ctx: typer.Context, error: BudjiraError) -> None:
    """Render a BudjiraError respecting the active output format."""
    if OutputFormatter.is_json_format(ctx.obj.get("format", "table") if ctx.obj else "table"):
        OutputFormatter.output_json({"error": str(error)})
    else:
        console.print(f"[red]Error:[/red] {error}")


@app.command("list")
def sprint_list(
    ctx: typer.Context,
    state: Annotated[
        str | None,
        typer.Option("--state", "-s", help="Filter by state: active, future, closed"),
    ] = None,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """List sprints for a board.

    Shows all sprints, optionally filtered by state. Auto-detects the board
    from the project if not specified.

    Examples:

        budjira sprint list
        budjira sprint list --state active
        budjira sprint list --board 42 --connection my-jira
        budjira --format json sprint list
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        conn = get_active_connection(connection)
        if not OutputFormatter.is_json_format(output_format):
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        board_id = _resolve_board_id(client, board, conn.board_id, conn.project_key)

        # Validate state filter
        if state:
            try:
                SprintState(state.lower())
            except ValueError:
                valid = ", ".join(s.value for s in SprintState)
                raise BudjiraError(f"Invalid state '{state}'. Valid states: {valid}") from None

        sprints = client.sprints.get_sprints(board_id, state=state)

        if OutputFormatter.is_json_format(output_format):
            sprint_dicts = [
                {
                    "id": s.id,
                    "name": s.name,
                    "state": s.state.value,
                    "start_date": s.start_date.isoformat() if s.start_date else None,
                    "end_date": s.end_date.isoformat() if s.end_date else None,
                    "complete_date": s.complete_date.isoformat() if s.complete_date else None,
                    "board_id": s.board_id,
                }
                for s in sprints
            ]
            OutputFormatter.output_json({"total": len(sprint_dicts), "board_id": board_id, "sprints": sprint_dicts})
            return

        if not sprints:
            state_msg = f" with state '{state}'" if state else ""
            console.print(f"[yellow]No sprints found{state_msg}.[/yellow]")
            return

        table = Table(show_header=True, title=f"Sprints (Board ID: {board_id})")
        table.add_column("Name", style="cyan")
        table.add_column("State")
        table.add_column("Start", style="dim")
        table.add_column("End", style="dim")

        for s in sprints:
            state_style = {
                SprintState.ACTIVE: "[green]active[/green]",
                SprintState.FUTURE: "[yellow]future[/yellow]",
                SprintState.CLOSED: "[dim]closed[/dim]",
            }.get(s.state, s.state.value)

            table.add_row(
                s.name,
                state_style,
                str(s.start_date) if s.start_date else "-",
                str(s.end_date) if s.end_date else "-",
            )

        console.print(table)

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e


@app.command("show")
def sprint_show(
    ctx: typer.Context,
    sprint_name: Annotated[
        str | None,
        typer.Argument(help="Sprint name (default: active sprint)"),
    ] = None,
    mine: Annotated[
        bool,
        typer.Option("--mine", "-m", help="Show only issues assigned to me"),
    ] = False,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Filter by issue status (e.g., 'In Progress')"),
    ] = None,
    issue_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter by issue type (e.g., Story, Bug)"),
    ] = None,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """Show sprint contents (issues).

    Displays issues in the active sprint (or a named sprint). Supports
    filtering by assignee, status, and issue type.

    Examples:

        budjira sprint show
        budjira sprint show --mine
        budjira sprint show "Sprint 42" --status "In Progress"
        budjira sprint show --type Bug --connection my-jira
        budjira --format json sprint show
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        conn = get_active_connection(connection)
        if not OutputFormatter.is_json_format(output_format):
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        board_id = _resolve_board_id(client, board, conn.board_id, conn.project_key)
        sprint = _resolve_sprint(client, board_id, sprint_name)

        # Build JQL filter
        filters: list[str] = []
        if mine:
            filters.append("assignee = currentUser()")
        if status:
            filters.append(f'status = "{status}"')
        if issue_type:
            filters.append(f'issuetype = "{issue_type}"')

        jql_filter = " AND ".join(filters) if filters else None
        issues = client.sprints.get_sprint_issues(sprint.id, jql_filter=jql_filter)

        if OutputFormatter.is_json_format(output_format):
            issue_dicts = [
                {
                    "key": i.key,
                    "summary": i.summary,
                    "issue_type": i.issue_type,
                    "status": i.status,
                    "priority": i.priority,
                    "assignee": i.assignee,
                    "time_original_estimate": i.time_original_estimate,
                    "time_spent": i.time_spent,
                }
                for i in issues
            ]
            OutputFormatter.output_json(
                {
                    "sprint": {
                        "id": sprint.id,
                        "name": sprint.name,
                        "state": sprint.state.value,
                        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
                        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
                    },
                    "total_issues": len(issue_dicts),
                    "issues": issue_dicts,
                }
            )
            return

        # Sprint header
        console.print(f"[cyan bold]Sprint: {sprint.name}[/cyan bold]")
        date_info = ""
        if sprint.start_date and sprint.end_date:
            date_info = f" ({sprint.start_date} - {sprint.end_date})"
        console.print(f"[dim]State: {sprint.state.value}{date_info}[/dim]")

        if not issues:
            filter_msg = " matching your filters" if filters else ""
            console.print(f"\n[yellow]No issues{filter_msg} in this sprint.[/yellow]")
            return

        console.print(f"\n[bold]Issues ({len(issues)}):[/bold]\n")

        table = Table(show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Type", style="dim", width=8)
        table.add_column("Status")
        table.add_column("Priority", style="dim", width=8)
        table.add_column("Summary")
        table.add_column("Assignee", style="dim")

        for issue in issues:
            # Status styling
            status_lower = issue.status.lower()
            if status_lower in ["done", "closed", "resolved"]:
                status_display = f"[green]{issue.status}[/green]"
            elif status_lower in ["in progress", "in review"]:
                status_display = f"[yellow]{issue.status}[/yellow]"
            else:
                status_display = issue.status

            table.add_row(
                issue.key,
                issue.issue_type,
                status_display,
                issue.priority or "-",
                issue.summary[:55] + "..." if len(issue.summary) > 55 else issue.summary,
                issue.assignee or "Unassigned",
            )

        console.print(table)

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e


def _sprint_result(sprint: Sprint) -> dict[str, object]:
    """Build a JSON-serializable result dict for a sprint write operation."""
    return {
        "id": sprint.id,
        "name": sprint.name,
        "state": sprint.state.value,
        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
        "board_id": sprint.board_id,
    }


@app.command("move")
def sprint_move(
    ctx: typer.Context,
    issue_keys: Annotated[
        list[str],
        typer.Argument(help="One or more issue keys to move (e.g., PROJ-1 PROJ-2)"),
    ],
    to: Annotated[
        str | None,
        typer.Option("--to", "-t", help="Target sprint name (case-insensitive)"),
    ] = None,
    sprint_id: Annotated[
        int | None,
        typer.Option("--sprint-id", help="Target sprint ID (alternative to --to)"),
    ] = None,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """Move issues into a sprint.

    Assigns one or more issues to a target sprint, identified by name (--to)
    or ID (--sprint-id). The operation is additive (no confirmation needed).

    Examples:

        budjira sprint move PROJ-123 --to "Sprint 42"
        budjira sprint move PROJ-1 PROJ-2 PROJ-3 --to "Sprint 42"
        budjira sprint move PROJ-123 --sprint-id 100
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"
        is_json = OutputFormatter.is_json_format(output_format)

        if to is None and sprint_id is None:
            raise BudjiraError("Specify a target sprint with --to NAME or --sprint-id ID.")

        conn = get_active_connection(connection)
        if not is_json:
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        sprint = _resolve_target(client, conn, board, to, sprint_id, allow_active=False)

        client.sprints.move_issues(sprint.id, issue_keys)

        if is_json:
            OutputFormatter.output_json(
                {"moved": issue_keys, "sprint": _sprint_result(sprint)},
            )
            return

        moved = ", ".join(issue_keys)
        console.print(f"[green]Moved {len(issue_keys)} issue(s) into '{sprint.name}':[/green] {moved}")

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e


@app.command("create")
def sprint_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Sprint name")],
    start: Annotated[
        str | None,
        typer.Option("--start", help="Start date (ISO, 'today', 'yesterday')"),
    ] = None,
    end: Annotated[
        str | None,
        typer.Option("--end", help="End date (ISO, 'today', 'yesterday')"),
    ] = None,
    goal: Annotated[
        str | None,
        typer.Option("--goal", "-g", help="Sprint goal"),
    ] = None,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """Create a new (future) sprint on a board.

    Dates are optional and can be set later when starting the sprint.

    Examples:

        budjira sprint create "Sprint 43"
        budjira sprint create "Sprint 43" --start today --end 2026-06-14
        budjira sprint create "Sprint 43" --goal "Ship the API"
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"
        is_json = OutputFormatter.is_json_format(output_format)

        conn = get_active_connection(connection)
        if not is_json:
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        board_id = _resolve_board_id(client, board, conn.board_id, conn.project_key)

        start_dt = parse_datetime_string(start, allow_future=True) if start else None
        end_dt = parse_datetime_string(end, allow_future=True) if end else None

        sprint = client.sprints.create_sprint(
            board_id=board_id,
            name=name,
            start_date=start_dt,
            end_date=end_dt,
            goal=goal,
        )

        if is_json:
            OutputFormatter.output_json(_sprint_result(sprint))
            return

        console.print(f"[green]Created sprint '{sprint.name}' (ID: {sprint.id}) on board {board_id}.[/green]")

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e


@app.command("start")
def sprint_start(
    ctx: typer.Context,
    sprint_name: Annotated[
        str | None,
        typer.Argument(help="Sprint name to start"),
    ] = None,
    sprint_id: Annotated[
        int | None,
        typer.Option("--sprint-id", help="Sprint ID (alternative to name)"),
    ] = None,
    start: Annotated[
        str | None,
        typer.Option("--start", help="Start date (required if the sprint has none)"),
    ] = None,
    end: Annotated[
        str | None,
        typer.Option("--end", help="End date (required if the sprint has none)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """Start a sprint (transition it to the active state).

    Jira requires the sprint to have a start and end date. Provide --start and
    --end if the sprint does not have them yet.

    Examples:

        budjira sprint start "Sprint 43" --start today --end 2026-06-14
        budjira sprint start --sprint-id 100 --force
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"
        is_json = OutputFormatter.is_json_format(output_format)

        conn = get_active_connection(connection)
        if not is_json:
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        sprint = _resolve_target(client, conn, board, sprint_name, sprint_id, allow_active=False)

        if not force:
            if is_json:
                raise BudjiraError("Confirmation required. Re-run with --force in JSON mode.")
            if not typer.confirm(f"Start sprint '{sprint.name}' (ID: {sprint.id})?"):
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

        start_dt = parse_datetime_string(start, allow_future=True) if start else None
        end_dt = parse_datetime_string(end, allow_future=True) if end else None
        updated = client.sprints.start_sprint(sprint.id, start_date=start_dt, end_date=end_dt)

        if is_json:
            OutputFormatter.output_json(_sprint_result(updated))
            return

        console.print(f"[green]Started sprint '{updated.name}' (ID: {updated.id}).[/green]")

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e


@app.command("close")
def sprint_close(
    ctx: typer.Context,
    sprint_name: Annotated[
        str | None,
        typer.Argument(help="Sprint name to close (default: active sprint)"),
    ] = None,
    sprint_id: Annotated[
        int | None,
        typer.Option("--sprint-id", help="Sprint ID (alternative to name)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
    board: Annotated[
        int | None,
        typer.Option("--board", "-b", help="Board ID (auto-detected if not provided)"),
    ] = None,
    connection: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name"),
    ] = None,
) -> None:
    """Close a sprint (transition it to the closed state).

    Defaults to the active sprint when no name or ID is given.

    Examples:

        budjira sprint close
        budjira sprint close "Sprint 42"
        budjira sprint close --sprint-id 100 --force
    """
    try:
        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"
        is_json = OutputFormatter.is_json_format(output_format)

        conn = get_active_connection(connection)
        if not is_json:
            console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        client = JiraClient.from_connection(conn)
        sprint = _resolve_target(client, conn, board, sprint_name, sprint_id, allow_active=True)

        if not force:
            if is_json:
                raise BudjiraError("Confirmation required. Re-run with --force in JSON mode.")
            if not typer.confirm(f"Close sprint '{sprint.name}' (ID: {sprint.id})?"):
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)

        updated = client.sprints.close_sprint(sprint.id)

        if is_json:
            OutputFormatter.output_json(_sprint_result(updated))
            return

        console.print(f"[green]Closed sprint '{updated.name}' (ID: {updated.id}).[/green]")

    except BudjiraError as e:
        _emit_error(ctx, e)
        raise typer.Exit(1) from e
