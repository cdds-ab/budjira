"""Main CLI entry point for budjira."""

import sys

import typer
from rich.console import Console

from budjira import __version__
from budjira.utils.banner import print_header

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


def is_quiet_mode() -> bool:
    """Check if quiet mode is enabled by parsing sys.argv."""
    return "-q" in sys.argv or "--quiet" in sys.argv


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
) -> None:
    """budjira - Your Jira buddy on the command line.

    A tool for efficient Jira interaction: search tickets, create issues, log time, and more.
    """
    # Show header unless in quiet mode
    if not quiet:
        print_header(console, quiet=False)

    if debug:
        console.print("[dim]Debug mode enabled[/dim]")


if __name__ == "__main__":
    app()
