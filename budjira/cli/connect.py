"""Connection management commands."""

from __future__ import annotations

import os

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


def _auto_sync_metadata(connection: Connection) -> None:
    """Attempt to sync project metadata after connection setup.

    Failure is non-blocking: shows a warning but doesn't prevent connection creation.

    Args:
        connection: Connection to sync metadata for
    """
    try:
        from budjira.config.metadata_cache import MetadataCache
        from budjira.core.jira_client import JiraClient

        console.print("\n[dim]Syncing project metadata...[/dim]")
        client = JiraClient.from_connection(connection)
        metadata = client.metadata.fetch_project_metadata(connection.project_key)

        settings = get_settings()
        cache = MetadataCache(settings.cache_dir)
        cache.save(connection, metadata)

        type_count = len(metadata.issue_types)
        priority_count = len(metadata.priorities)
        component_count = len(metadata.components)
        console.print(
            f"[green]✓[/green] Project metadata synced: "
            f"{type_count} issue types, {priority_count} priorities, {component_count} components"
        )
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Could not sync project metadata: {e}", style="yellow")
        console.print("[dim]Run 'budjira project sync' later to fetch metadata.[/dim]")


@app.command("add")
def add_connection(
    name: str = typer.Option(None, "--name", "-n", help="Connection name"),
    url: str = typer.Option(None, "--url", "-u", help="Jira instance URL"),
    email: str = typer.Option(None, "--email", "-e", help="Email address"),
    project_key: str = typer.Option(None, "--project", "-p", help="Default project key"),
) -> None:
    """Add or update a Jira connection.

    Creates a named connection that can be used across different projects
    and directories. Use --connection flag or BUDJIRA_CONNECTION env var
    to select which connection to use.

    Examples:
        # Interactive mode
        budjira connect add

        # With all parameters
        budjira connect add --name work --url https://work.atlassian.net \\
            --email user@work.com --project PROJ
    """
    try:
        settings = get_settings()
        credential_store = get_credential_store()

        # Interactive prompts if values not provided
        if name is None:
            name = Prompt.ask("Connection name")

        # Check if connection already exists
        existing = settings.connections.find_by_name(name)
        if existing:
            console.print(
                f"[yellow]⚠[/yellow] Connection '{name}' already exists",
                style="yellow",
            )
            if not Confirm.ask("Update existing connection?", default=True):
                raise typer.Abort()

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

        # Auto-sync project metadata
        _auto_sync_metadata(connection)

        console.print("\n[dim]To use this connection:[/dim]")
        console.print(f"[dim]  • For single command: budjira search --connection {name}[/dim]")
        console.print(f"[dim]  • For shell session: export BUDJIRA_CONNECTION={name}[/dim]")
        console.print(f"[dim]  • As global default: budjira connect use {name}[/dim]")

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

    # Get active connection info
    active_name = settings.global_config.active_connection
    env_connection = os.getenv("BUDJIRA_CONNECTION")

    table = Table(title="Configured Connections", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan")
    table.add_column("URL")
    table.add_column("Email")
    table.add_column("Project")
    table.add_column("Default", justify="center")

    for conn in connections:
        # Mark default connection
        is_default = conn.name == active_name
        default_icon = "[green]★[/green]" if is_default else ""

        # Show env override if set
        if env_connection == conn.name:
            default_icon = "[yellow]○[/yellow] ENV"

        table.add_row(
            conn.name,
            str(conn.url),
            conn.email,
            conn.project_key,
            default_icon,
        )

    console.print(table)

    # Show legend
    console.print("\n[dim]Legend:[/dim]")
    console.print("[dim]  [green]★[/green] Default connection (use 'budjira connect use' to change)[/dim]")
    console.print("[dim]  [yellow]○[/yellow] ENV - Overridden by BUDJIRA_CONNECTION environment variable[/dim]")


@app.command("show")
def show_connection(
    name: str = typer.Argument(help="Connection name to show"),
) -> None:
    """Show details of a specific connection."""
    settings = get_settings()
    credential_store = get_credential_store()

    connection = settings.connections.find_by_name(name)
    if not connection:
        console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
        console.print("\nUse [cyan]budjira connect list[/cyan] to see available connections.")
        raise typer.Exit(1)

    # Display connection details
    console.print(f"\n[bold cyan]{connection.name}[/bold cyan]")
    console.print(f"[dim]{'─' * 50}[/dim]")

    console.print(f"[bold]URL:[/bold]          {connection.url}")
    console.print(f"[bold]Email:[/bold]        {connection.email}")
    console.print(f"[bold]Project Key:[/bold]  {connection.project_key}")
    console.print(f"[bold]Cache:[/bold]        {'Enabled' if connection.cache_enabled else 'Disabled'}")

    # Check credentials
    has_creds = credential_store.has_credentials(connection)
    cred_status = "[green]Stored[/green]" if has_creds else "[red]Missing[/red]"
    console.print(f"[bold]API Token:[/bold]    {cred_status}")

    # Check Tempo integration
    if connection.tempo_enabled:
        tempo_key = connection.get_tempo_credential_key()
        has_tempo_token = credential_store.get_credential(tempo_key) is not None
        tempo_token_status = "[green]Stored[/green]" if has_tempo_token else "[red]Missing[/red]"
        console.print("[bold]Tempo:[/bold]        [green]Enabled[/green]")
        console.print(f"[bold]Tempo Token:[/bold]  {tempo_token_status}")
    else:
        console.print("[bold]Tempo:[/bold]        [dim]Disabled[/dim]")

    # Check if this is the default connection
    is_default = settings.global_config.active_connection == connection.name
    if is_default:
        console.print("[bold]Default:[/bold]      [green]Yes[/green]")

    # Check if overridden by ENV
    env_connection = os.getenv("BUDJIRA_CONNECTION")
    if env_connection == connection.name:
        console.print("[bold]ENV Override:[/bold] [yellow]Yes (BUDJIRA_CONNECTION)[/yellow]")

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
        console.print(f"  URL:     {connection.url}")
        console.print(f"  Project: {connection.project_key}")

        if not Confirm.ask("\nAre you sure?", default=False):
            console.print("Cancelled.")
            raise typer.Abort()

    # Remove credentials
    if credential_store.has_credentials(connection):
        credential_store.delete(connection)
        console.print("[green]✓[/green] Removed API token")

    # Clear active_connection if this was the default
    if settings.global_config.active_connection == name:
        settings.global_config.active_connection = None
        settings.save_global_config(settings.global_config)
        console.print("[yellow]⚠[/yellow] Cleared default connection")

    # Remove connection
    settings.remove_connection(name)
    console.print(f"[green]✓[/green] Removed connection: [cyan]{name}[/cyan]")


@app.command("use")
def use_connection(
    name: str = typer.Argument(..., help="Connection name to set as default"),
) -> None:
    """Set a connection as the default for all commands.

    This sets the global default connection that will be used when
    no --connection flag or BUDJIRA_CONNECTION env var is specified.

    Example:
        budjira connect use work
        budjira search  # Uses 'work' connection
    """
    settings = get_settings()

    connection = settings.connections.find_by_name(name)
    if not connection:
        console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
        console.print("\nUse [cyan]budjira connect list[/cyan] to see available connections.")
        raise typer.Exit(1)

    # Set as active connection
    settings.global_config.active_connection = name
    settings.save_global_config(settings.global_config)

    console.print(f"[green]✓[/green] Set default connection to: [cyan]{name}[/cyan]")
    console.print(f"\n[dim]Using:[/dim] {connection.url} ({connection.email})")
    console.print(f"[dim]Default project:[/dim] {connection.project_key}")


@app.command("current")
def show_current() -> None:
    """Show the currently active connection.

    Shows which connection will be used based on the resolution order:
    1. BUDJIRA_CONNECTION environment variable
    2. Global default (set via 'budjira connect use')
    3. No default configured
    """
    from budjira.utils.connection import get_active_connection

    settings = get_settings()
    env_connection = os.getenv("BUDJIRA_CONNECTION")

    try:
        connection = get_active_connection()

        console.print("[bold]Active Connection:[/bold]")
        console.print(f"  Name:    [cyan]{connection.name}[/cyan]")
        console.print(f"  URL:     {connection.url}")
        console.print(f"  Project: {connection.project_key}")

        # Show how it was selected
        if env_connection:
            console.print("\n[yellow]Source:[/yellow] BUDJIRA_CONNECTION environment variable")
        elif settings.global_config.active_connection:
            console.print("\n[green]Source:[/green] Global default (set via 'budjira connect use')")

    except BudjiraError:
        console.print("[yellow]No active connection configured[/yellow]")
        console.print("\n[dim]To set a default connection:[/dim]")
        console.print("[dim]  • For shell session: export BUDJIRA_CONNECTION=<name>[/dim]")
        console.print("[dim]  • As global default: budjira connect use <name>[/dim]")
        console.print("[dim]  • List connections: budjira connect list[/dim]")
        raise typer.Exit(1) from None


@app.command("test")
def test_connection(
    name: str = typer.Argument(None, help="Connection name to test (uses current if not specified)"),
) -> None:
    """Test a Jira connection.

    Tests the connection by attempting to authenticate and fetch server info.
    If no name is provided, tests the currently active connection.
    """
    from jira import JIRA

    from budjira.utils.connection import get_active_connection

    settings = get_settings()
    credential_store = get_credential_store()

    # Find connection
    if name:
        connection = settings.connections.find_by_name(name)
        if not connection:
            console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
            raise typer.Exit(1)
    else:
        try:
            connection = get_active_connection()
            console.print(f"[dim]Testing current connection: {connection.name}[/dim]\n")
        except BudjiraError:
            console.print(
                "[yellow]⚠[/yellow] No active connection configured",
                style="yellow",
            )
            console.print("\nSpecify a connection name or set a default with 'budjira connect use'")
            raise typer.Exit(1) from None

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

        # Verify authentication by fetching current user
        # server_info() does NOT require auth on many Jira instances,
        # so we must use an authenticated endpoint to validate the token
        current_user = jira.current_user()

        # Fetch server info for display (optional, non-critical)
        try:
            server_info = jira.server_info()
        except Exception:  # nosec B110
            server_info = {}

        console.print("[green]✓[/green] Connection successful!")
        console.print("\n[bold]Server Info:[/bold]")
        if server_info:
            console.print(f"  Version:      {server_info.get('version', 'Unknown')}")
            console.print(f"  Build:        {server_info.get('buildNumber', 'Unknown')}")
            console.print(f"  Server Title: {server_info.get('serverTitle', 'Unknown')}")
        console.print(f"  Logged in as: {current_user}")

    except Exception as e:
        console.print(f"[red]✗[/red] Connection failed: {e}", style="red")
        console.print("\n[yellow]Common issues:[/yellow]")
        console.print("  • Invalid or expired API token")
        console.print("  • Wrong email address for this token")
        console.print("  • Network connectivity problems")
        console.print("  • Jira instance is down or unreachable")
        raise typer.Exit(1) from None


@app.command("tempo-setup")
def tempo_setup(
    connection_name: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name (uses active connection if not specified)",
    ),
) -> None:
    """Configure Tempo Timesheets integration for a connection.

    Sets up Tempo API token for advanced time tracking functionality.
    Create a Tempo API token at: Tempo → Settings → API Integration → Tokens

    Examples:
        # Setup Tempo for active connection
        budjira connect tempo-setup

        # Setup Tempo for specific connection
        budjira connect tempo-setup --connection work
    """
    try:
        from budjira.utils.connection import get_active_connection

        settings = get_settings()
        credential_store = get_credential_store()

        # Get connection
        if connection_name:
            connection = settings.connections.find_by_name(connection_name)
            if not connection:
                console.print(
                    f"[red]✗[/red] Connection '{connection_name}' not found",
                    style="red",
                )
                raise typer.Exit(1)
        else:
            try:
                connection = get_active_connection()
            except BudjiraError:
                console.print(
                    "[yellow]⚠[/yellow] No active connection configured",
                    style="yellow",
                )
                console.print("\nSpecify a connection with --connection or set a default with 'budjira connect use'")
                raise typer.Exit(1) from None

        console.print(f"\n[bold]Configuring Tempo for connection:[/bold] [cyan]{connection.name}[/cyan]\n")

        # Show instructions
        console.print("[bold]To create a Tempo API token:[/bold]")
        console.print("  1. Go to your Jira instance")
        console.print("  2. Navigate to: Tempo → Settings → API Integration")
        console.print("  3. Click 'New Token' and copy the generated token\n")

        # Check if Tempo token already exists
        existing_token_key = connection.get_tempo_credential_key()
        has_existing = credential_store.get_credential(existing_token_key) is not None

        if has_existing:
            console.print("[yellow]⚠[/yellow] Tempo token already configured for this connection")
            if not Confirm.ask("Replace existing Tempo token?", default=False):
                console.print("[yellow]Setup cancelled[/yellow]")
                raise typer.Exit(0)

        # Prompt for Tempo token
        tempo_token = Prompt.ask(
            "Tempo API token",
            password=True,
        )

        if not tempo_token or tempo_token.strip() == "":
            console.print("[red]✗[/red] Tempo token cannot be empty", style="red")
            raise typer.Exit(1)

        # Test the Tempo token
        console.print("\nTesting Tempo API connection...")
        try:
            from budjira.tempo.client import TempoClient

            tempo_client = TempoClient(tempo_token=tempo_token)
            # Try a simple API call to verify the token
            tempo_client.get_accounts(limit=1)
            console.print("[green]✓[/green] Tempo API connection successful!")

        except Exception as e:
            console.print(f"[red]✗[/red] Tempo API connection failed: {e}", style="red")
            console.print("\n[yellow]Common issues:[/yellow]")
            console.print("  • Invalid Tempo API token")
            console.print("  • Tempo is not installed in your Jira instance")
            console.print("  • Network connectivity problems")

            if not Confirm.ask("\nSave token anyway?", default=False):
                raise typer.Exit(1) from None

        # Save Tempo token
        credential_store.store_credential(existing_token_key, tempo_token)
        console.print("[green]✓[/green] Saved Tempo API token securely")

        # Enable Tempo for this connection
        connection.tempo_enabled = True
        settings.update_connection(connection)
        console.print("[green]✓[/green] Enabled Tempo integration for this connection")

        # Show usage instructions
        console.print("\n[bold]Tempo is now configured! You can use:[/bold]")
        console.print("  • [cyan]budjira tempo log ISSUE TIME[/cyan] - Log work via Tempo")
        console.print("  • [cyan]budjira tempo worklogs[/cyan] - View Tempo worklogs")
        console.print("  • [cyan]budjira tempo accounts[/cyan] - List Tempo accounts")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None
