"""Test DoR CLI commands."""

from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_dor_help() -> None:
    """Test dor subcommand help."""
    result = runner.invoke(app, ["dor", "--help"])
    assert result.exit_code == 0
    assert "dor" in result.stdout.lower()
    assert "template" in result.stdout.lower()


def test_dor_list_help() -> None:
    """Test dor list command help."""
    result = runner.invoke(app, ["dor", "list", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout.lower()


def test_dor_show_help() -> None:
    """Test dor show command help."""
    result = runner.invoke(app, ["dor", "show", "--help"])
    assert result.exit_code == 0
    assert "show" in result.stdout.lower()
    assert "issue" in result.stdout.lower()


def test_dor_show_requires_argument() -> None:
    """Test that dor show requires issue type argument."""
    result = runner.invoke(app, ["-q", "dor", "show"])
    assert result.exit_code != 0


def test_dor_edit_help() -> None:
    """Test dor edit command help."""
    result = runner.invoke(app, ["dor", "edit", "--help"])
    assert result.exit_code == 0
    assert "edit" in result.stdout.lower()


def test_dor_validate_help() -> None:
    """Test dor validate command help."""
    result = runner.invoke(app, ["dor", "validate", "--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout.lower()
