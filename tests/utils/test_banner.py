"""Test banner functionality."""

from budjira import __version__
from budjira.utils.banner import get_compact_header, get_header, print_header
from rich.console import Console
from rich.text import Text


def test_get_header() -> None:
    """Test that header is returned as Text."""
    header = get_header()
    assert isinstance(header, Text)
    assert "budjira" in str(header)
    assert "🦖" in str(header)


def test_get_compact_header() -> None:
    """Test compact header."""
    header = get_compact_header()
    assert isinstance(header, str)
    assert "budjira" in header
    assert "🦖" in header
    assert __version__ in header


def test_print_header(capsys: object) -> None:
    """Test header printing."""
    console = Console(file=None, force_terminal=False)
    print_header(console)
    # If we got here without errors, the function works


def test_print_header_quiet_mode() -> None:
    """Test that quiet mode suppresses header."""
    console = Console(file=None, force_terminal=False)
    print_header(console, quiet=True)
    # Should return early, no output


def test_header_contains_version() -> None:
    """Test that header contains version info."""
    header = str(get_header())
    assert f"v{__version__}" in header
    assert "Your CLI Pal for Jira" in header


def test_banner_lines_same_width() -> None:
    """Test that top and bottom banner lines have equal visual width."""
    console = Console()
    header = get_header()

    lines = str(header).split("\n")
    assert len(lines) >= 2

    # Measure both lines
    top_measurement = console.measure(lines[0])
    bottom_measurement = console.measure(lines[1])

    assert top_measurement.maximum == bottom_measurement.maximum, (
        f"Banner lines must have equal width: top={top_measurement.maximum}, bottom={bottom_measurement.maximum}"
    )
