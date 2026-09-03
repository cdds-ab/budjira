"""Connection management commands."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed 'pass' CLI invocations with controlled args (trusted)

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from budjira.config import get_credential_store, get_settings
from budjira.config.secret_ref import PASS_TIMEOUT_SECONDS, parse_secret_ref, resolve_secret_ref
from budjira.config.secrets import (
    _env_safe_name,
    describe_api_token_source,
    describe_tempo_token_source,
    resolve_api_token,
)
from budjira.models.connection import Connection
from budjira.utils.description import DescriptionDialectOption  # noqa: TC001 - Typer resolves it at runtime
from budjira.utils.errors import BudjiraError, SecretRefError

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
    description_dialect: DescriptionDialectOption = typer.Option(
        None,
        "--description-dialect",
        help="Dialect descriptions on this instance are written in (default: markdown)",
    ),
    api_token_ref: str = typer.Option(
        None,
        "--api-token-ref",
        help="Secret reference for the Jira API token (env:NAME, pass:entry, file:/path) - recommended",
    ),
    store_token: bool = typer.Option(
        False,
        "--store-token",
        help="Store the API token on disk instead of using a reference (deprecated)",
    ),
) -> None:
    """Add or update a Jira connection.

    Creates a named connection that can be used across different projects
    and directories. Use --connection flag or BUDJIRA_CONNECTION env var
    to select which connection to use.

    API token: prefer a secret reference (env:NAME, pass:entry, file:/path) -
    the token then lives in your password manager or environment, and several
    connections can share one reference. Storing the token on disk
    (--store-token) is deprecated.

    Description dialect: pick "markdown" (the default) for an instance where
    authors write Markdown - budjira converts it to Jira wiki markup on upload.
    Pick "wiki" for an instance whose house format is already expressed in wiki
    markup, e.g. panel macros and "#" ordered lists; descriptions are then sent
    unchanged. Individual calls can deviate with --description-dialect.

    Examples:
        # Interactive mode
        budjira connect add

        # With all parameters, token via pass reference
        budjira connect add --name work --url https://work.atlassian.net \\
            --email user@work.com --project PROJ --api-token-ref pass:work/jira-token

        # An instance whose descriptions are authored in wiki markup
        budjira connect add --name house --url https://house.atlassian.net \\
            --email user@house.com --project PROJ --description-dialect wiki
    """
    try:
        settings = get_settings()
        credential_store = get_credential_store()

        if api_token_ref is not None and store_token:
            console.print(
                "[red]✗[/red] --api-token-ref and --store-token cannot be used together",
                style="red",
            )
            raise typer.Exit(1)

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

        # API token setup: secret reference (recommended) or stored token (deprecated).
        api_token: str | None = None
        ref_verified = False
        if api_token_ref is None and not store_token:
            if existing and (existing.api_token_ref or credential_store.has_credentials(existing)):
                current = existing.api_token_ref or "stored on disk (deprecated)"
                console.print(
                    f"[dim]API token: {current} - unchanged (--api-token-ref or --store-token to change)[/dim]"
                )
            else:
                source = Prompt.ask(
                    "API token source: 'ref' = secret reference (recommended), 'store' = on disk (deprecated)",
                    choices=["ref", "store"],
                    default="ref",
                )
                store_token = source == "store"

        if api_token_ref is None and not store_token:
            api_token_ref = Prompt.ask("API token reference (env:NAME, pass:entry, file:/path)")

        if api_token_ref is not None:
            try:
                resolve_secret_ref(api_token_ref)
                ref_verified = True
                console.print("[green]✓[/green] Reference resolves successfully")
            except SecretRefError as e:
                console.print(f"[red]✗[/red] {e}", style="red")
                if not Confirm.ask("Save reference anyway?", default=False):
                    raise typer.Abort() from None
        else:
            # Deprecated path: store the token on disk
            console.print(
                "[yellow]⚠[/yellow] Storing tokens on disk is deprecated - prefer a reference (env:/pass:/file:)",
                style="yellow",
            )
            api_token = Prompt.ask(
                "Jira API token",
                password=True,
                default="<keep existing>" if existing and credential_store.has_credentials(existing) else None,
            )

        # Updating carries the stored connection forward: this command only asks for a
        # handful of fields, and everything else (Tempo, custom fields, board, prompts)
        # must survive an edit of URL, email or project key.
        stored_values = existing.model_dump() if existing else {}
        changed_values: dict[str, object] = {
            "name": name,
            "url": url,
            "email": email,
            "project_key": project_key,
        }
        if description_dialect is not None:
            changed_values["description_dialect"] = description_dialect.value
        if api_token_ref is not None:
            changed_values["api_token_ref"] = api_token_ref
        elif store_token:
            changed_values["api_token_ref"] = None

        # Pydantic validates the merged values and converts the url string to HttpUrl
        connection = Connection(**{**stored_values, **changed_values})

        # Save connection
        if existing:
            settings.update_connection(connection)
            console.print(f"[green]✓[/green] Updated connection: [cyan]{name}[/cyan]")
        else:
            settings.add_connection(connection)
            console.print(f"[green]✓[/green] Added connection: [cyan]{name}[/cyan]")

        # Token handling: store (deprecated) or drop the stored file superseded by a
        # verified reference. An unverified reference leaves the stored file in place.
        if api_token and api_token != "<keep existing>":  # nosec B105
            credential_store.store(connection, api_token)
            console.print("[green]✓[/green] Saved API token (deprecated - consider 'budjira connect migrate')")
        if connection.api_token_ref and ref_verified and credential_store.has_credentials(connection):
            credential_store.delete(connection)
            console.print("[green]✓[/green] Removed stored API token (superseded by the reference)")

        # Show connection details
        console.print("\n[bold]Connection details:[/bold]")
        console.print(f"  Name:         {connection.name}")
        console.print(f"  URL:          {connection.url}")
        console.print(f"  Email:        {connection.email}")
        console.print(f"  Project:      {connection.project_key}")
        console.print(f"  Descriptions: {connection.description_dialect}")
        console.print(f"  API token:    {describe_api_token_source(connection)}")

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
    table.add_column("URL", no_wrap=True)
    table.add_column("Email")
    table.add_column("Project")
    table.add_column("Descriptions")
    table.add_column("API Token", no_wrap=True)
    table.add_column("Default", justify="center")

    for conn in connections:
        # Mark default connection
        is_default = conn.name == active_name
        default_icon = "[green]★[/green]" if is_default else ""

        # Show env override if set
        if env_connection == conn.name:
            default_icon = "[yellow]○[/yellow] ENV"

        source = describe_api_token_source(conn)
        if source == "stored (deprecated)":
            source_display = "[yellow]stored (deprecated)[/yellow]"
        elif source == "missing":
            source_display = "[red]missing[/red]"
        else:
            source_display = source

        table.add_row(
            conn.name,
            str(conn.url),
            conn.email,
            conn.project_key,
            conn.description_dialect,
            source_display,
            default_icon,
        )

    console.print(table)

    # Show legend
    console.print("\n[dim]Legend:[/dim]")
    console.print("[dim]  [green]★[/green] Default connection (use 'budjira connect use' to change)[/dim]")
    console.print("[dim]  [yellow]○[/yellow] ENV - Overridden by BUDJIRA_CONNECTION environment variable[/dim]")
    console.print(
        "[dim]  API Token: references shown verbatim; 'stored (deprecated)' migrates via "
        "'budjira connect migrate <name>'[/dim]"
    )


@app.command("show")
def show_connection(
    name: str = typer.Argument(help="Connection name to show"),
) -> None:
    """Show details of a specific connection."""
    settings = get_settings()

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
    console.print(f"[bold]Descriptions:[/bold] {connection.description_dialect}")
    console.print(f"[bold]Cache:[/bold]        {'Enabled' if connection.cache_enabled else 'Disabled'}")

    # Token source (references shown verbatim, never the resolved value)
    api_source = describe_api_token_source(connection)
    if api_source == "stored (deprecated)":
        api_source_display = "[yellow]stored (deprecated)[/yellow]"
    elif api_source == "missing":
        api_source_display = "[red]Missing[/red]"
    else:
        api_source_display = f"[green]{api_source}[/green]"
    console.print(f"[bold]API Token:[/bold]    {api_source_display}")

    # Check Tempo integration
    if connection.tempo_enabled:
        tempo_source = describe_tempo_token_source(connection)
        if tempo_source == "stored (deprecated)":
            tempo_source_display = "[yellow]stored (deprecated)[/yellow]"
        elif tempo_source == "missing":
            tempo_source_display = "[red]Missing[/red]"
        else:
            tempo_source_display = f"[green]{tempo_source}[/green]"
        console.print("[bold]Tempo:[/bold]        [green]Enabled[/green]")
        console.print(f"[bold]Tempo Token:[/bold]  {tempo_source_display}")
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

    # Remove credentials (API token and Tempo token file, if present)
    if credential_store.has_credentials(connection):
        credential_store.delete(connection)
        console.print("[green]✓[/green] Removed API token")
    if credential_store.delete_credential(connection.get_tempo_credential_key()):
        console.print("[green]✓[/green] Removed Tempo token")

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

    # Resolve the API token (ref -> env -> stored)
    try:
        api_token = resolve_api_token(connection)
    except SecretRefError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from None
    if not api_token:
        console.print(
            f"[red]✗[/red] No API token found for connection '{connection.name}'",
            style="red",
        )
        console.print(
            "\nSet api_token_ref (env:/pass:/file:), export BUDJIRA_API_TOKEN, "
            "or use [cyan]budjira connect add[/cyan] to update credentials."
        )
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
    tempo_token_ref: str = typer.Option(
        None,
        "--tempo-token-ref",
        help="Secret reference for the Tempo API token (env:NAME, pass:entry, file:/path) - recommended",
    ),
) -> None:
    """Configure Tempo Timesheets integration for a connection.

    Sets up Tempo API token for advanced time tracking functionality.
    Create a Tempo API token at: Tempo → Settings → API Integration → Tokens

    Prefer --tempo-token-ref (e.g. pass:acme/tempo-token) over storing the
    token on disk - stored tokens are deprecated.

    Examples:
        # Setup Tempo for active connection
        budjira connect tempo-setup

        # Setup Tempo for specific connection
        budjira connect tempo-setup --connection work

        # Token via pass reference
        budjira connect tempo-setup --connection work --tempo-token-ref pass:work/tempo-token
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

        existing_token_key = connection.get_tempo_credential_key()

        # Reference path: verify the reference resolves, then keep it on the connection
        if tempo_token_ref is not None:
            try:
                resolve_secret_ref(tempo_token_ref)
                ref_verified = True
                console.print("[green]✓[/green] Reference resolves successfully")
            except SecretRefError as e:
                console.print(f"[red]✗[/red] {e}", style="red")
                if not Confirm.ask("Save reference anyway?", default=False):
                    raise typer.Abort() from None
                ref_verified = False

            connection.tempo_token_ref = tempo_token_ref
            connection.tempo_enabled = True
            settings.update_connection(connection)
            console.print(f"[green]✓[/green] Tempo token reference set: [cyan]{tempo_token_ref}[/cyan]")

            if ref_verified and credential_store.get_credential(existing_token_key) is not None:
                credential_store.delete_credential(existing_token_key)
                console.print("[green]✓[/green] Removed stored Tempo token (superseded by the reference)")

            console.print("[green]✓[/green] Enabled Tempo integration for this connection")
            console.print("\n[bold]Tempo is now configured! You can use:[/bold]")
            console.print("  • [cyan]budjira tempo log ISSUE TIME[/cyan] - Log work via Tempo")
            console.print("  • [cyan]budjira tempo worklogs[/cyan] - View Tempo worklogs")
            console.print("  • [cyan]budjira tempo accounts[/cyan] - List Tempo accounts")
            return

        # Show instructions
        console.print("[bold]To create a Tempo API token:[/bold]")
        console.print("  1. Go to your Jira instance")
        console.print("  2. Navigate to: Tempo → Settings → API Integration")
        console.print("  3. Click 'New Token' and copy the generated token")
        console.print(
            "\n[dim]Tip: --tempo-token-ref pass:acme/tempo-token keeps the token in your password manager.[/dim]\n"
        )

        # Check if Tempo token already exists
        has_existing = credential_store.get_credential(existing_token_key) is not None

        if has_existing:
            console.print("[yellow]⚠[/yellow] Tempo token already configured for this connection")
            if not Confirm.ask("Replace existing Tempo token?", default=False):
                console.print("[yellow]Setup cancelled[/yellow]")
                raise typer.Exit(0)

        # Prompt for Tempo token
        console.print(
            "[yellow]⚠[/yellow] Storing tokens on disk is deprecated - prefer --tempo-token-ref (env:/pass:/file:)",
            style="yellow",
        )
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


def _migrate_one_token(
    connection: Connection,
    kind: str,
    target_ref: str,
    *,
    force: bool,
) -> bool:
    """Migrate one stored token of a connection to a secret reference.

    pass: insert the stored token into the entry (stdin), verify the reference
    resolves to the same value, only then switch the connection and delete the
    stored file. env: only proceed when the variable already holds the stored
    token's value - the reference is set and the file deleted only on a match,
    so the printed export line is never the last remaining copy.

    Connections that already use a reference for this token are skipped.

    Args:
        connection: Connection whose token is migrated
        kind: ``API`` or ``TEMPO``
        target_ref: Target reference (``pass:<entry>`` or ``env:<NAME>``)
        force: Overwrite an existing pass entry

    Returns:
        True if the token was migrated, False if skipped/failed
    """
    credential_store = get_credential_store()

    scheme, target = parse_secret_ref(target_ref)

    label = "API token" if kind == "API" else "Tempo token"

    current_ref = connection.api_token_ref if kind == "API" else connection.tempo_token_ref
    if current_ref:
        console.print(f"[dim]{connection.name}: {label} already uses reference '{current_ref}' - skipping[/dim]")
        return False

    if kind == "API":
        stored_token = credential_store.retrieve(connection)
    else:
        stored_token = credential_store.get_credential(connection.get_tempo_credential_key())

    if not stored_token:
        console.print(f"[dim]{connection.name}: no stored {label} - nothing to migrate[/dim]")
        return False

    if scheme == "pass":
        # Distinguish "entry absent" from other pass failures: a decryption
        # error (locked or missing GPG key) must NOT read as "absent" -
        # 'pass insert --force' only needs the public key and would silently
        # overwrite the existing entry.
        try:
            check = subprocess.run(  # nosec B603 B607 - fixed 'pass show' args, entry from config
                ["pass", "show", target],
                capture_output=True,
                text=True,
                timeout=PASS_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            console.print(
                f"[red]✗[/red] {connection.name}: 'pass show' timed out after "
                f"{PASS_TIMEOUT_SECONDS}s (is the GPG key unlocked?)",
                style="red",
            )
            return False
        needs_insert = True
        if check.returncode == 0:
            lines = check.stdout.splitlines()
            existing = lines[0].strip() if lines else ""
            if existing and existing == stored_token:
                # The entry already holds exactly this token: nothing to
                # overwrite, no --force needed - insert is a no-op.
                needs_insert = False
                console.print(f"[dim]{connection.name}: pass entry '{target}' already holds this token[/dim]")
            elif not force:
                console.print(
                    f"[red]✗[/red] {connection.name}: pass entry '{target}' already exists (use --force to overwrite)",
                    style="red",
                )
                return False
        elif "is not in the password store" not in check.stderr:
            detail = check.stderr.strip().splitlines()[0] if check.stderr.strip() else f"exit {check.returncode}"
            console.print(
                f"[red]✗[/red] {connection.name}: cannot inspect pass entry '{target}' - {detail[:200]}",
                style="red",
            )
            return False

        if needs_insert:
            try:
                insert = subprocess.run(  # nosec B603 B607 - fixed 'pass insert' args, entry from config
                    ["pass", "insert", "--multiline", "--force", target],
                    input=stored_token + "\n",
                    capture_output=True,
                    text=True,
                    timeout=PASS_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                console.print(
                    f"[red]✗[/red] {connection.name}: 'pass insert' timed out after {PASS_TIMEOUT_SECONDS}s",
                    style="red",
                )
                return False
            if insert.returncode != 0:
                detail = insert.stderr.strip().splitlines()[0] if insert.stderr.strip() else "unknown error"
                console.print(
                    f"[red]✗[/red] {connection.name}: pass insert failed - {detail[:200]}",
                    style="red",
                )
                return False

        # Verify before deleting: the reference must resolve to the same value
        try:
            resolved = resolve_secret_ref(target_ref)
        except SecretRefError as e:
            console.print(f"[red]✗[/red] {connection.name}: verification failed - {e}", style="red")
            console.print("[yellow]Stored token kept; the pass entry was written.[/yellow]")
            return False
        if resolved != stored_token:
            console.print(
                f"[red]✗[/red] {connection.name}: verification failed - the reference resolves to a different value",
                style="red",
            )
            console.print("[yellow]Stored token kept; the pass entry was written.[/yellow]")
            return False
    else:
        # env: the reference only becomes authoritative once the variable
        # provably holds the stored token - deleting the file earlier would
        # strand the last copy in the user's scrollback.
        current_value = os.environ.get(target)
        if current_value is None:
            console.print(
                f"[yellow]⚠[/yellow] {connection.name}: environment variable '{target}' is not set",
                style="yellow",
            )
            console.print("[dim]Export it first, then re-run migrate:[/dim]")
            console.print(f"export {target}='{stored_token}'")
            return False
        if current_value.strip() != stored_token:
            console.print(
                f"[red]✗[/red] {connection.name}: '{target}' holds a different value than the stored token",
                style="red",
            )
            return False

    # Switch the connection to the reference and drop the stored file
    if kind == "API":
        connection.api_token_ref = target_ref
        credential_store.delete(connection)
    else:
        connection.tempo_token_ref = target_ref
        credential_store.delete_credential(connection.get_tempo_credential_key())

    console.print(f"[green]✓[/green] {connection.name}: {label} migrated to [cyan]{target_ref}[/cyan]")
    return True


@app.command("migrate")
def migrate_connection(
    name: str = typer.Argument(None, help="Connection name to migrate"),
    to: str = typer.Option(
        None,
        "--to",
        help="Target reference for the Jira API token (pass:<entry> or env:<NAME>)",
    ),
    tempo_to: str = typer.Option(
        None,
        "--tempo-to",
        help="Target reference for the Tempo token (pass:<entry> or env:<NAME>)",
    ),
    all_connections: bool = typer.Option(
        False,
        "--all",
        help="Migrate every connection with a stored token; --to/--tempo-to are used as prefixes",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing pass entries"),
) -> None:
    """Migrate stored tokens to secret references.

    Reads the stored (deprecated) token, moves it to the target - a pass
    entry or an environment variable - and points the connection at the
    reference. With pass:, the reference is verified to resolve to the same
    value before the stored file is deleted. With env:, the variable must
    already hold the stored token's value - the file is only deleted on a
    match, so the printed export line is never the last copy.

    With --all, --to and --tempo-to are prefixes: the per-connection target is
    '<prefix>/<connection-name>' for pass: ('…/tempo' for the Tempo token) and
    '<PREFIX>_<NAME>' for env: ('…_TEMPO' suffix for the Tempo token).

    Examples:
        # One connection, Jira token to pass
        budjira connect migrate acme --to pass:acme/atlassian-token

        # Jira and Tempo tokens at once
        budjira connect migrate acme --to pass:acme/atlassian-token --tempo-to pass:acme/tempo-token

        # Everything stored, one pass entry per connection
        budjira connect migrate --all --to pass:budjira
    """
    settings = get_settings()

    if not all_connections and name is None:
        console.print("[red]✗[/red] Specify a connection name or --all", style="red")
        raise typer.Exit(1)
    if to is None and tempo_to is None:
        console.print("[red]✗[/red] Nothing to do: pass --to and/or --tempo-to", style="red")
        raise typer.Exit(1)

    # Validate targets before touching anything
    for candidate in (to, tempo_to):
        if candidate is None:
            continue
        try:
            scheme, _ = parse_secret_ref(candidate)
        except SecretRefError as e:
            console.print(f"[red]✗[/red] {e}", style="red")
            raise typer.Exit(1) from None
        if scheme not in ("pass", "env"):
            console.print(
                f"[red]✗[/red] migrate supports pass: and env: targets, not '{scheme}:'",
                style="red",
            )
            raise typer.Exit(1)

    # Identical targets would map both tokens of one connection to one secret.
    # Under --all the tempo template carries its own suffix, so equal prefixes
    # still diverge per connection.
    if not all_connections and to is not None and to == tempo_to:
        console.print("[red]✗[/red] --to and --tempo-to must differ", style="red")
        raise typer.Exit(1)

    # pass: targets need the binary - a missing one must not traceback later
    needs_pass = any(parse_secret_ref(candidate)[0] == "pass" for candidate in (to, tempo_to) if candidate is not None)
    if needs_pass and shutil.which("pass") is None:
        console.print(
            "[red]✗[/red] 'pass' executable not found. Install pass (the standard Unix "
            "password manager) or migrate to an env: target.",
            style="red",
        )
        raise typer.Exit(1)

    if all_connections:
        targets = list(settings.connections.connections)
        if name is not None:
            console.print("[red]✗[/red] --all takes no connection name", style="red")
            raise typer.Exit(1)
    else:
        connection = settings.connections.find_by_name(name)
        if not connection:
            console.print(f"[red]✗[/red] Connection '{name}' not found", style="red")
            raise typer.Exit(1)
        targets = [connection]

    migrated = 0
    for connection in targets:
        changed = False
        if to is not None:
            target = to
            if all_connections:
                scheme, base = parse_secret_ref(to)
                if scheme == "pass":
                    safe = connection.name.lower().replace(" ", "-")
                    target = f"pass:{base}/{safe}"
                elif scheme == "env":
                    target = f"env:{base}_{_env_safe_name(connection.name)}"
            if _migrate_one_token(connection, "API", target, force=force):
                changed = True
        if tempo_to is not None:
            target = tempo_to
            if all_connections:
                scheme, base = parse_secret_ref(tempo_to)
                if scheme == "pass":
                    safe = connection.name.lower().replace(" ", "-")
                    target = f"pass:{base}/{safe}/tempo"
                elif scheme == "env":
                    target = f"env:{base}_{_env_safe_name(connection.name)}_TEMPO"
            if _migrate_one_token(connection, "TEMPO", target, force=force):
                changed = True
        if changed:
            settings.update_connection(connection)
            migrated += 1

    if migrated:
        console.print(f"\n[green]✓[/green] Migrated {migrated} connection(s)")
    else:
        console.print("\n[yellow]Nothing migrated[/yellow]")
