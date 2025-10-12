"""Test issue CLI commands."""

from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_issue_help() -> None:
    """Test issue subcommand help."""
    result = runner.invoke(app, ["issue", "--help"])
    assert result.exit_code == 0
    assert "issue" in result.stdout.lower()
    assert "update" in result.stdout.lower()
    assert "transitions" in result.stdout.lower()


def test_issue_update_help() -> None:
    """Test issue update command help."""
    result = runner.invoke(app, ["issue", "update", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout.lower()
    assert "assignee" in result.stdout.lower()
    assert "priority" in result.stdout.lower()
    assert "label" in result.stdout.lower()
    assert "epic" in result.stdout.lower()


def test_issue_update_requires_argument() -> None:
    """Test that issue update requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "update"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()


def test_issue_update_requires_options() -> None:
    """Test that issue update requires at least one update option."""
    result = runner.invoke(app, ["-q", "issue", "update", "PROJ-123"])
    assert result.exit_code != 0
    # Should warn about no updates specified
    assert "no updates" in result.stdout.lower() or "Error" in result.stdout


def test_issue_transitions_help() -> None:
    """Test issue transitions command help."""
    result = runner.invoke(app, ["issue", "transitions", "--help"])
    assert result.exit_code == 0
    assert "transitions" in result.stdout.lower()
    assert "workflow" in result.stdout.lower()


def test_issue_transitions_requires_argument() -> None:
    """Test that issue transitions requires issue key argument."""
    result = runner.invoke(app, ["-q", "issue", "transitions"])
    assert result.exit_code != 0
    assert "Missing argument" in result.stdout or "required" in result.stdout.lower()
