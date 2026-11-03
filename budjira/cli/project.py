"""Project commands: metadata cache (sync/show/clear) and administration (list/create)."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from budjira.config import get_settings
from budjira.config.metadata_cache import MetadataCache
from budjira.services.projects import build_board_payload, build_filter_payload, build_project_payload
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError, ValidationError
from budjira.utils.formatter import OutputFormatter

if TYPE_CHECKING:
    from budjira.models.project import ReferenceProject

app = typer.Typer(
    name="project",
    help="Manage Jira projects: list and create projects, cache project metadata",
    no_args_is_help=True,
)
console = Console()

# Jira Cloud's default key rule: a letter, then letters/digits/underscore, 2-10 chars.
_PROJECT_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")


class BoardChoice(str, Enum):
    """Board to create for a new project."""

    KANBAN = "kanban"
    SCRUM = "scrum"
    NONE = "none"


def _get_metadata_cache() -> MetadataCache:
    """Get metadata cache instance.

    Returns:
        MetadataCache using the settings cache directory
    """
    settings = get_settings()
    return MetadataCache(settings.cache_dir)


@app.command("sync")
def sync_metadata(
    connection_name: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name (uses active connection if not specified)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force refresh even if cache is still valid",
    ),
) -> None:
    """Fetch and cache project metadata from Jira.

    Discovers issue types, priorities, and components for the project
    configured in the connection. Cached locally for use in issue creation
    and AI prompts.

    Examples:
        budjira project sync
        budjira project sync --connection work --force
    """
    try:
        from budjira.core.jira_client import JiraClient

        connection = get_active_connection(connection_name)
        cache = _get_metadata_cache()

        # Check if cache is still valid
        if not force and cache.is_valid(connection):
            console.print(f"[dim]Metadata cache for '{connection.name}' is still fresh.[/dim]")
            console.print("[dim]Use --force to refresh.[/dim]")
            return

        console.print(f"Syncing project metadata for [cyan]{connection.name}[/cyan]...")

        client = JiraClient.from_connection(connection)
        metadata = client.metadata.fetch_project_metadata(connection.project_key)

        cache.save(connection, metadata)

        # Show summary
        type_count = len(metadata.issue_types)
        priority_count = len(metadata.priorities)
        component_count = len(metadata.components)
        console.print(
            f"[green]✓[/green] Project metadata synced: "
            f"{type_count} issue types, {priority_count} priorities, {component_count} components"
        )

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None


@app.command("show")
def show_metadata(
    connection_name: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name (uses active connection if not specified)",
    ),
) -> None:
    """Display cached project metadata.

    Shows issue types, priorities, and components from the local cache.
    Run 'budjira project sync' first to populate the cache.

    Examples:
        budjira project show
        budjira project show --connection work
    """
    try:
        connection = get_active_connection(connection_name)
        cache = _get_metadata_cache()

        metadata = cache.load(connection)
        if metadata is None:
            console.print(f"[yellow]No cached metadata for connection '{connection.name}'[/yellow]")
            console.print("[dim]Run 'budjira project sync' to fetch metadata.[/dim]")
            raise typer.Exit(1)

        # Header
        console.print(f"\n[bold cyan]{metadata.project_name}[/bold cyan] ({metadata.project_key})")
        stale = metadata.is_stale(connection.cache_ttl_hours)
        freshness = "[red]stale[/red]" if stale else "[green]fresh[/green]"
        console.print(f"[dim]Fetched: {metadata.fetched_at:%Y-%m-%d %H:%M UTC} ({freshness})[/dim]")

        # Issue Types
        if metadata.issue_types:
            console.print("\n[bold]Issue Types:[/bold]")
            type_table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
            type_table.add_column("Name", style="cyan")
            type_table.add_column("Subtask", justify="center")
            type_table.add_column("Required Fields")

            for it in metadata.issue_types:
                required = [f.name for f in it.fields if f.required]
                required_str = ", ".join(required) if required else "[dim]none[/dim]"
                subtask_icon = "yes" if it.subtask else ""
                type_table.add_row(it.name, subtask_icon, required_str)

            console.print(type_table)

        # Priorities
        if metadata.priorities:
            console.print(f"\n[bold]Priorities:[/bold] {', '.join(metadata.priorities)}")

        # Components
        if metadata.components:
            console.print(f"\n[bold]Components:[/bold] {', '.join(metadata.components)}")

        console.print()

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None


@app.command("clear")
def clear_metadata(
    connection_name: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name (uses active connection if not specified)",
    ),
) -> None:
    """Delete cached project metadata.

    Examples:
        budjira project clear
        budjira project clear --connection work
    """
    try:
        connection = get_active_connection(connection_name)
        cache = _get_metadata_cache()

        if cache.clear(connection):
            console.print(f"[green]✓[/green] Cleared metadata cache for '{connection.name}'")
        else:
            console.print(f"[dim]No cached metadata for '{connection.name}'[/dim]")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None


def _is_json(ctx: typer.Context) -> bool:
    return OutputFormatter.is_json_format(ctx.obj.get("format", "table") if ctx.obj else "table")


@app.command("list")
def list_projects(
    ctx: typer.Context,
    connection_name: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name (uses active connection if not specified)"),
    ] = None,
) -> None:
    """List all projects of the instance the token can see.

    Shows key, name, id, management style (company-/team-managed) and lead.
    Answers "does project KEY exist?" — which a search cannot, since an empty
    project and a missing one both return no issues.

    Examples:
        budjira project list
        budjira --format json project list --connection work
    """
    try:
        from budjira.core.jira_client import JiraClient

        connection = get_active_connection(connection_name)
        projects = JiraClient.from_connection(connection).projects.list_projects()

        if _is_json(ctx):
            OutputFormatter.output_json(
                {
                    "total": len(projects),
                    "projects": [{**p.model_dump(), "management": p.management} for p in projects],
                }
            )
            return

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("Key", style="cyan")
        table.add_column("Name")
        table.add_column("ID", style="dim")
        table.add_column("Style")
        table.add_column("Lead")
        for p in projects:
            table.add_row(p.key, p.name, p.id, p.management, p.lead or "[dim]-[/dim]")
        console.print(table)
        console.print(f"\n[dim]{len(projects)} projects on {connection.name}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None


def _print_plan(key: str, reference: ReferenceProject, plan: dict[str, Any]) -> None:
    """Show the payloads a create would send."""
    console.print(
        f"\n[cyan]Dry run:[/cyan] would create project {key} like {reference.key} — read calls only, nothing created"
    )
    for label in ("project", "filter", "board"):
        if plan.get(label) is not None:
            console.print(f"[cyan]{label} payload:[/cyan]")
            console.print(Syntax(json.dumps(plan[label], indent=2, ensure_ascii=False), "json", word_wrap=True))


def _scheme_summary(reference: ReferenceProject) -> str:
    def show(value: object) -> str:
        return "default" if value is None else str(value)

    return (
        f"issue type scheme {show(reference.issue_type_scheme)}, "
        f"screen scheme {show(reference.issue_type_screen_scheme)}, "
        f"workflow scheme {show(reference.workflow_scheme)}"
    )


@app.command("create")
def create_project(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Key of the new project (e.g. APX)")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name of the new project")],
    like: Annotated[
        str,
        typer.Option("--like", help="Company-managed project whose issue type, screen and workflow schemes to reuse"),
    ],
    board: Annotated[
        BoardChoice,
        typer.Option("--board", "-b", help="Board to create on the new project ('none' to skip)"),
    ] = BoardChoice.KANBAN,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Read the reference and print the payloads; create nothing"),
    ] = False,
    connection_name: Annotated[
        str | None,
        typer.Option("--connection", "-c", help="Connection name (uses active connection if not specified)"),
    ] = None,
) -> None:
    """Create a company-managed project that shares another project's schemes.

    The new project reuses the reference's issue type scheme, issue type screen
    scheme and workflow scheme; you become its lead, issues start unassigned.
    Then a filter "project = KEY ORDER BY Rank ASC" (shared with the project)
    and a board on it are created. The permission scheme is left at the default
    (Jira Free does not allow changing it). Needs the 'Administer Jira' global
    permission.

    Examples:
        budjira project create APX --name Apodeixis --like CDDSINT --dry-run
        budjira project create APX --name Apodeixis --like CDDSINT
        budjira project create OPS --name Operations --like CDDSINT --board none
    """
    try:
        from budjira.core.jira_client import JiraClient

        key = key.strip().upper()
        like = like.strip().upper()
        if not _PROJECT_KEY.match(key):
            raise ValidationError(
                f"Invalid project key '{key}': start with a letter, then letters, digits or '_' (2-10 characters)."
            )

        connection = get_active_connection(connection_name)
        projects = JiraClient.from_connection(connection).projects

        if projects.project_exists(key):
            raise ValidationError(f"Project '{key}' already exists on {connection.name}.")

        reference = projects.get_reference(like)
        payload = build_project_payload(key, name, reference, lead_account_id=projects.current_account_id())
        board_type = None if board is BoardChoice.NONE else board.value

        if dry_run:
            plan = {
                "dry_run": True,
                "like": reference.key,
                "project": payload,
                "filter": build_filter_payload(key, "<new project id>") if board_type else None,
                "board": build_board_payload(key, "<new filter id>", board_type) if board_type else None,
            }
            if _is_json(ctx):
                OutputFormatter.output_json(plan)
            else:
                _print_plan(key, reference, plan)
            return

        created = projects.create_project(payload)
        result: dict[str, Any] = {"project": created, "like": reference.key, "filter_id": None, "board_id": None}
        if not _is_json(ctx):
            console.print(
                f"[green]✓[/green] Created project [cyan]{created['key']}[/cyan] (id {created['id']}) "
                f"like {reference.key}: {_scheme_summary(reference)}"
            )

        if board_type:
            try:
                result["filter_id"] = projects.create_filter(build_filter_payload(key, created["id"]))
                result["board_id"] = projects.create_board(build_board_payload(key, result["filter_id"], board_type))
            except BudjiraError as e:
                filter_note = f" (filter {result['filter_id']} exists)" if result["filter_id"] else ""
                raise BudjiraError(
                    f"Project {key} was created, but its {board_type} board was not{filter_note}: {e}"
                ) from e

        if _is_json(ctx):
            OutputFormatter.output_json(result)
            return

        if board_type:
            console.print(
                f"[green]✓[/green] Board '{key} board' (id {result['board_id']}, {board_type}) "
                f"on filter {result['filter_id']}"
            )
        base_url = str(connection.url).rstrip("/")
        console.print(f"\n[dim]View in Jira: {base_url}/browse/{key}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None
