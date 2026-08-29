"""Main CLI entry point for budjira."""

import sys

import typer
from rich.console import Console

from budjira import __version__
from budjira.cli import (
    ai,
    attach,
    comment,
    connect,
    create,
    dor,
    epic,
    issue,
    project,
    search,
    show,
    sprint,
    tempo,
    update,
    workflow,
    worklog,
)
from budjira.utils.banner import print_header
from budjira.utils.redact import install_redaction

# Credentials must never reach log output; scrub every record at creation.
install_redaction()

# Show header early for --help (which bypasses callback)
# Check for --help and show header unless -q is present
if "--help" in sys.argv and "-q" not in sys.argv and "--quiet" not in sys.argv:
    _console = Console()
    print_header(_console, quiet=False)

app = typer.Typer(
    name="budjira",
    help="A CLI buddy for Jira - efficient command-line interaction with Jira Cloud",
    add_completion=True,
    no_args_is_help=True,
)

console = Console()

# Register subcommands
app.add_typer(ai.app, name="ai")
app.add_typer(comment.app, name="comment")
app.add_typer(connect.app, name="connect")
app.add_typer(create.app, name="create")
app.add_typer(dor.app, name="dor")
app.add_typer(epic.app, name="epic")
app.add_typer(issue.app, name="issue")
app.add_typer(project.app, name="project")
app.add_typer(search.app, name="search")
app.add_typer(sprint.app, name="sprint")
app.add_typer(tempo.app, name="tempo")
app.add_typer(update.app, name="update")
app.add_typer(workflow.app, name="workflow")
app.add_typer(worklog.app, name="worklog")

# Register top-level show command
app.command(name="show")(show.show_issue)

# Register top-level attach command
app.command(name="attach")(attach.attach_files)


def is_quiet_mode() -> bool:
    """Check if quiet mode is enabled by parsing sys.argv."""
    return "-q" in sys.argv or "--quiet" in sys.argv


def _check_for_updates_on_startup() -> None:
    """Check for updates on startup (non-blocking, cached)."""
    try:
        from budjira.config import get_settings
        from budjira.utils.version import get_version_checker

        settings = get_settings()

        # Skip if disabled in config
        if not settings.global_config.check_updates:
            return

        checker = get_version_checker()
        update_available, latest_version, release_url, _ = checker.check_for_updates(force=False)

        if update_available and latest_version:
            console.print(
                f"[yellow]⚠[/yellow] Update available: [cyan]{latest_version}[/cyan] (current: {__version__})",
                style="yellow",
            )
            if release_url:
                console.print("[dim]Run [cyan]budjira update[/cyan] to install.[/dim]\n")

    except Exception:  # nosec B110
        # Silently ignore errors in update check - shouldn't block normal operation
        pass


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        # Show header unless quiet mode
        if not is_quiet_mode():
            print_header(console, quiet=False)
        console.print(f"budjira version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(  # noqa: ARG001
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress header output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug output",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table (default) or json",
    ),
) -> None:
    """budjira - Your Jira buddy on the command line.

    A tool for efficient Jira interaction: search tickets, create issues, log time, and more.
    """
    # Store format in context for subcommands
    ctx.obj = {"format": output_format, "debug": debug, "quiet": quiet}

    # Show header unless in quiet mode or JSON format
    if not quiet and output_format != "json":
        print_header(console, quiet=False)

    if debug and output_format != "json":
        console.print("[dim]Debug mode enabled[/dim]")

    # Check for updates if enabled (skip for update command itself)
    if not quiet and "update" not in sys.argv and output_format != "json":
        _check_for_updates_on_startup()


if __name__ == "__main__":
    app()
