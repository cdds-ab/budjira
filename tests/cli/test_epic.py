"""Test epic CLI commands."""

from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_epic_help() -> None:
    """Test epic subcommand help."""
    result = runner.invoke(app, ["epic", "--help"])
    assert result.exit_code == 0
    assert "epic" in result.stdout.lower()
    assert "show" in result.stdout.lower()


def test_epic_show_help() -> None:
    """Test epic show command help."""
    result = runner.invoke(app, ["epic", "show", "--help"])
    assert result.exit_code == 0
    assert "show" in result.stdout.lower()
    assert "epic" in result.stdout.lower()


def test_epic_show_requires_argument() -> None:
    """Test that epic show requires epic key argument."""
    result = runner.invoke(app, ["-q", "epic", "show"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()
