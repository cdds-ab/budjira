"""Project metadata management commands."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from budjira.config import get_settings
from budjira.config.metadata_cache import MetadataCache
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError

app = typer.Typer(
    name="project",
    help="Manage Jira project metadata (issue types, priorities, components)",
    no_args_is_help=True,
)
console = Console()


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
