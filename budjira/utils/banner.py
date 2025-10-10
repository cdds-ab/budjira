"""Simple header banner for budjira."""

from rich.console import Console
from rich.text import Text

from budjira import __version__


def get_header() -> Text:
    """Return a simple 2-line header for budjira.

    This is shown by default on every command unless -q/--quiet is used.
    """
    # Build header line by line for exact width control
    header = Text()

    # Top line
    header.append("╭─ ", style="bright_cyan")
    header.append("🦖", style="bright_blue")
    header.append(" ", style="")
    header.append("budjira", style="bold bright_magenta")
    header.append(f" v{__version__} ", style="dim")
    header.append("─ ", style="bright_cyan")
    header.append("Your CLI Pal for Jira", style="dim italic")
    header.append(" ─╮", style="bright_cyan")
    header.append("\n")

    # Bottom line - match the visual width (emoji is 2 wide)
    header.append("╰", style="bright_cyan")
    header.append("─" * 44, style="bright_cyan")
    header.append("╯", style="bright_cyan")

    return header


def get_compact_header() -> str:
    """Return a minimal one-line header."""
    return f"🦖 budjira v{__version__}"


def print_header(console: Console | None = None, quiet: bool = False) -> None:
    """Print the budjira header to console.

    Args:
        console: Rich Console instance. If None, creates a new one.
        quiet: If True, don't print the header.
    """
    if quiet:
        return

    if console is None:
        console = Console()

    header = get_header()
    console.print(header)
    console.print()  # Empty line after header


if __name__ == "__main__":
    # Test the header
    print_header()
