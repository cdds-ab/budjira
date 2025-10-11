"""Connection management commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from budjira.config import get_credential_store, get_settings
from budjira.models.connection import Connection
from budjira.utils.errors import BudjiraError

app = typer.Typer(
    name="connect",
    help="Manage Jira connections",
    no_args_is_help=True,
)
console = Console()


@app.command("add")
def add_connection(
    name: str = typer.Option(None, "--name", "-n", help="Connection name"),
    url: str = typer.Option(None, "--url", "-u", help="Jira instance URL"),
    email: str = typer.Option(None, "--email", "-e", help="Email address"),
    project_key: str = typer.Option(None, "--project", "-p", help="Default project key"),
    project_root: Path = typer.Option(
        None,
        "--root",
        "-r",
        help="Project root directory (defaults to current directory)",
    ),
) -> None:
    """Add a new Jira connection.

    Creates a connection for the specified project root, allowing you to
    interact with Jira from that directory and its subdirectories.
    """
    try:
        settings = get_settings()
        credential_store = get_credential_store()

        # Use current directory if no root specified
        project_root = Path.cwd() if project_root is None else project_root.expanduser().resolve()

        # Check if connection already exists for this root
        existing = settings.connections.find_by_root(project_root)
        if existing:
            console.print(
                f"[yellow]⚠[/yellow] Connection already exists for {project_root}",
                style="yellow",
            )
            console.print(f"Existing connection: [cyan]{existing.name}[/cyan]")

            if not Confirm.ask("Update existing connection?"):
                raise typer.Abort()

        # Interactive prompts if values not provided
        if name is None:
            name = Prompt.ask(
                "Connection name",
                default=existing.name if existing else project_root.name,
            )

        if url is None:
            default_url = str(existing.url) if existing else None
            url = Prompt.ask(
                "Jira URL (e.g., https://company.atlassian.net)",
                default=default_url,
            )

        if email is None:
            default_email = existing.email if existing else None
            email = Prompt.ask("Email address", default=default_email)

        if project_key is None:
            default_key = existing.project_key if existing else None
            project_key = Prompt.ask(
                "Default project key (e.g., PROJ)",
                default=default_key,
            ).upper()

        # Prompt for API token
        api_token = Prompt.ask(
            "Jira API token",
            password=True,
            default="<keep existing>" if existing and credential_store.has_credentials(existing) else None,
        )

        # Create connection
        # Pydantic will validate and convert url string to HttpUrl
        connection = Connection(
            name=name,
            url=url,  # type: ignore[arg-type]
            email=email,
            project_key=project_key,
            project_root=project_root,
        )

        # Save connection
        if existing:
            settings.update_connection(connection)
            console.print(f"[green]✓[/green] Updated connection: [cyan]{name}[/cyan]")
        else:
            settings.add_connection(connection)
            console.print(f"[green]✓[/green] Added connection: [cyan]{name}[/cyan]")

        # Save credentials (unless user kept existing)
        if api_token and api_token != "<keep existing>":  # nosec B105
            credential_store.store(connection, api_token)
            console.print("[green]✓[/green] Saved API token securely")

        # Show connection details
        console.print("\n[bold]Connection details:[/bold]")
        console.print(f"  Name:         {connection.name}")
        console.print(f"  URL:          {connection.url}")
        console.print(f"  Email:        {connection.email}")
        console.print(f"  Project:      {connection.project_key}")
        console.print(f"  Root:         {connection.project_root}")

    except ValueError as e:
        console.print(f"[red]✗[/red] Validation error: {e}", style="red")
        raise typer.Exit(1) from None
    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None


@app.command("list")
def list_connections() -> None:
    """List all configured connections."""
    settings = get_settings()
    connections = settings.connections.connections

    if not connections:
        console.print("[yellow]No connections configured yet.[/yellow]")
        console.print("\nUse [cyan]budjira connect add[/cyan] to create one.")
        return

    table = Table(title="Configured Connections", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("URL")
    table.add_column("Email")
    table.add_column("Project")
    table.add_column("Root", overflow="fold")
    table.add_column("Active", justify="center")

    for conn in connections:
        active_icon = "✓" if conn.is_active else "✗"
        table.add_row(
            conn.name,
            str(conn.url),
            conn.email,
            conn.project_key,
            str(conn.project_root),
            active_icon,
        )

    console.print(table)


@app.command("show")
def show_connection(
    name: str = typer.Argument(None, help="Connection name to show"),
) -> None:
    """Show details of a specific connection.

    If no name is provided, shows the connection for the current directory.
    """
    settings = get_settings()
    credential_store = get_credential_store()

    if name:
        connection = settings.connections.find_by_name(name)
        if not connection:
            console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
            raise typer.Exit(1)
    else:
        connection = settings.get_connection_for_current_dir()
        if not connection:
            console.print(
                "[yellow]⚠[/yellow] No connection found for current directory",
                style="yellow",
            )
            console.print("\nUse [cyan]budjira connect add[/cyan] to create one.")
            raise typer.Exit(1)

    # Display connection details
    console.print(f"\n[bold cyan]{connection.name}[/bold cyan]")
    console.print(f"[dim]{'─' * 50}[/dim]")

    console.print(f"[bold]URL:[/bold]          {connection.url}")
    console.print(f"[bold]Email:[/bold]        {connection.email}")
    console.print(f"[bold]Project Key:[/bold]  {connection.project_key}")
    console.print(f"[bold]Project Root:[/bold] {connection.project_root}")
    console.print(f"[bold]Active:[/bold]       {'Yes' if connection.is_active else 'No'}")
    console.print(f"[bold]Cache:[/bold]        {'Enabled' if connection.cache_enabled else 'Disabled'}")

    # Check credentials
    has_creds = credential_store.has_credentials(connection)
    cred_status = "[green]Stored[/green]" if has_creds else "[red]Missing[/red]"
    console.print(f"[bold]API Token:[/bold]    {cred_status}")

    # Show file paths
    console.print("\n[bold]Files:[/bold]")
    console.print(f"  Log:   {settings.get_log_file(connection)}")
    console.print(f"  Cache: {settings.get_cache_file(connection)}")


@app.command("remove")
def remove_connection(
    name: str = typer.Argument(..., help="Connection name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a connection and its credentials."""
    settings = get_settings()
    credential_store = get_credential_store()

    connection = settings.connections.find_by_name(name)
    if not connection:
        console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
        raise typer.Exit(1)

    # Confirm removal
    if not force:
        console.print(f"[yellow]⚠[/yellow] About to remove connection: [cyan]{connection.name}[/cyan]")
        console.print(f"  URL:  {connection.url}")
        console.print(f"  Root: {connection.project_root}")

        if not Confirm.ask("\nAre you sure?", default=False):
            console.print("Cancelled.")
            raise typer.Abort()

    # Remove credentials
    if credential_store.has_credentials(connection):
        credential_store.delete(connection)
        console.print("[green]✓[/green] Removed API token")

    # Remove connection
    settings.remove_connection(connection.project_root)
    console.print(f"[green]✓[/green] Removed connection: [cyan]{name}[/cyan]")


@app.command("test")
def test_connection(
    name: str = typer.Argument(None, help="Connection name to test"),
) -> None:
    """Test a Jira connection.

    If no name is provided, tests the connection for the current directory.
    """
    from jira import JIRA

    settings = get_settings()
    credential_store = get_credential_store()

    # Find connection
    if name:
        connection = settings.connections.find_by_name(name)
        if not connection:
            console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
            raise typer.Exit(1)
    else:
        connection = settings.get_connection_for_current_dir()
        if not connection:
            console.print(
                "[yellow]⚠[/yellow] No connection found for current directory",
                style="yellow",
            )
            raise typer.Exit(1)

    # Check credentials
    api_token = credential_store.retrieve(connection)
    if not api_token:
        console.print(
            f"[red]✗[/red] No API token found for connection '{connection.name}'",
            style="red",
        )
        console.print("\nUse [cyan]budjira connect add[/cyan] to update credentials.")
        raise typer.Exit(1)

    # Test connection
    console.print(f"Testing connection to [cyan]{connection.url}[/cyan]...")

    try:
        jira = JIRA(
            server=str(connection.url),
            basic_auth=(connection.email, api_token),
            timeout=10,
        )

        # Try to get server info
        server_info = jira.server_info()

        console.print("[green]✓[/green] Connection successful!")
        console.print("\n[bold]Server Info:[/bold]")
        console.print(f"  Version:     {server_info.get('version', 'Unknown')}")
        console.print(f"  Build:       {server_info.get('buildNumber', 'Unknown')}")
        console.print(f"  Server Title: {server_info.get('serverTitle', 'Unknown')}")

        # Try to get current user
        try:
            current_user = jira.current_user()
            console.print(f"  Logged in as: {current_user}")
        except Exception:  # nosec B110
            pass  # Some Jira instances don't support this

    except Exception as e:
        console.print(f"[red]✗[/red] Connection failed: {e}", style="red")
        console.print("\n[yellow]Common issues:[/yellow]")
        console.print("  • Invalid URL or API token")
        console.print("  • Network connectivity problems")
        console.print("  • Jira instance is down or unreachable")
        raise typer.Exit(1) from None
