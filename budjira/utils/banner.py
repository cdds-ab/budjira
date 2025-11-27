"""Simple header banner for budjira."""

from rich.console import Console
from rich.text import Text

from budjira import __version__


def get_header() -> Text:
    """Return a simple 2-line header for budjira.

    This is shown by default on every command unless -q/--quiet is used.
    """
    # Create temporary console for measurement
    temp_console = Console()

    # Build top line as Text object for measurement
    top_line = Text()
    top_line.append("╭─ ", style="bright_cyan")
    top_line.append("🦖", style="bright_blue")
    top_line.append(" ", style="")
    top_line.append("budjira", style="bold bright_magenta")
    top_line.append(f" v{__version__} ", style="dim")
    top_line.append("─ ", style="bright_cyan")
    top_line.append("Your CLI Pal for Jira", style="dim italic")
    top_line.append(" ─╮", style="bright_cyan")

    # Measure visual width (accounts for emoji = 2 cells, ANSI = 0 cells)
    top_width = temp_console.measure(top_line).maximum

    # Build final header
    header = Text()
    header.append(top_line)
    header.append("\n")

    # Bottom line - dynamically sized to match top
    header.append("╰", style="bright_cyan")
    header.append("─" * (top_width - 2), style="bright_cyan")  # -2 for corners
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
