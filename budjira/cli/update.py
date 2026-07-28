"""Update command."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from budjira import __version__
from budjira.utils.version import get_version_checker

app = typer.Typer(
    name="update",
    help="Check for and install updates",
    no_args_is_help=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def update(
    ctx: typer.Context,
    check_only: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Only check for updates without installing",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force check even if cache is valid",
    ),
) -> None:
    """Check for and install updates.

    By default, updates budjira with the mechanism matching how it was
    installed (install script, uv tool, or pipx). If the install method cannot
    be determined, the update is refused rather than guessed.
    Use --check to only check for updates without installing.
    """
    # If a subcommand was called, don't run the default behavior
    if ctx.invoked_subcommand is not None:
        return

    checker = get_version_checker()

    console.print(f"[dim]Current version: {__version__}[/dim]")
    console.print("Checking for updates...\n")

    update_available, latest_version, release_url, release_notes = checker.check_for_updates(force=force)

    if not update_available:
        if latest_version:
            console.print("[green]✓[/green] You are using the latest version!")
        else:
            console.print("[yellow]⚠[/yellow] Could not check for updates (network error)")
        return

    # Show update info
    console.print(f"[yellow]⚠[/yellow] A new version is available: [cyan]{latest_version}[/cyan]")

    if release_url:
        console.print(f"Release page: {release_url}\n")

    # Show release notes if available
    if release_notes:
        notes = Markdown(release_notes)
        console.print(Panel(notes, title="Release Notes", border_style="cyan"))

    # Check-only mode
    if check_only:
        console.print("\n[dim]Run [cyan]budjira update[/cyan] to install the update.[/dim]")
        return

    # Confirm update
    if not typer.confirm("\nDo you want to update now?", default=True):
        console.print("Update cancelled.")
        raise typer.Abort()

    # Perform update
    console.print("\n[cyan]Downloading and installing update...[/cyan]")
    success, message = checker.perform_update()

    if success:
        console.print(f"\n[green]✓[/green] {message}")
    else:
        console.print(f"\n[red]✗[/red] {message}", style="red")
        raise typer.Exit(1)


@app.command("check")
def check_update(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force check even if cache is valid",
    ),
) -> None:
    """Check for updates without installing.

    Uses cached result if available (default: 24 hours).
    Use --force to bypass cache and check immediately.
    """
    checker = get_version_checker()

    console.print(f"[dim]Current version: {__version__}[/dim]")
    console.print("Checking for updates...\n")

    update_available, latest_version, release_url, release_notes = checker.check_for_updates(force=force)

    if not update_available:
        if latest_version:
            console.print("[green]✓[/green] You are using the latest version!")
        else:
            console.print("[yellow]⚠[/yellow] Could not check for updates (network error)")
        return

    # Show update info
    console.print(f"[yellow]⚠[/yellow] A new version is available: [cyan]{latest_version}[/cyan]")

    if release_url:
        console.print(f"Release page: {release_url}\n")

    # Show release notes if available
    if release_notes:
        notes = Markdown(release_notes)
        console.print(Panel(notes, title="Release Notes", border_style="cyan"))

    console.print("\n[dim]Run [cyan]budjira update[/cyan] to install the update.[/dim]")
