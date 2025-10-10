"""Test main CLI functionality."""

from budjira import __version__
from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version_flag() -> None:
    """Test --version flag shows version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_flag() -> None:
    """Test --help flag shows help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "budjira" in result.stdout.lower()
    assert "jira" in result.stdout.lower()


def test_no_args_shows_help() -> None:
    """Test that running with no args shows help."""
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
