"""Test AI CLI commands."""

from budjira.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_ai_help() -> None:
    """Test ai subcommand help."""
    result = runner.invoke(app, ["ai", "--help"])
    assert result.exit_code == 0
    assert "ai" in result.stdout.lower()
    assert "usage-prompt" in result.stdout.lower()


def test_ai_no_args_shows_help() -> None:
    """Test that ai with no args shows help."""
    result = runner.invoke(app, ["ai"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_usage_prompt_help() -> None:
    """Test usage-prompt command help."""
    result = runner.invoke(app, ["ai", "usage-prompt", "--help"])
    assert result.exit_code == 0
    assert "usage-prompt" in result.stdout.lower()
    assert "generate" in result.stdout.lower()


def test_usage_prompt_generates_content() -> None:
    """Test usage-prompt generates comprehensive guide."""
    result = runner.invoke(app, ["-q", "ai", "usage-prompt"])
    assert result.exit_code == 0

    # Check for major sections
    assert "budjira" in result.stdout.lower()
    assert "overview" in result.stdout.lower()
    assert "connection" in result.stdout.lower()
    assert "search" in result.stdout.lower()
    assert "create" in result.stdout.lower()

    # Check for key commands
    assert "budjira connect" in result.stdout.lower()
    assert "budjira search" in result.stdout.lower()
    assert "budjira create issue" in result.stdout.lower()

    # Check for important concepts
    assert "jql" in result.stdout.lower()
    assert "api token" in result.stdout.lower()
    assert "interactive" in result.stdout.lower()


def test_usage_prompt_includes_examples() -> None:
    """Test usage-prompt includes practical examples."""
    result = runner.invoke(app, ["-q", "ai", "usage-prompt"])
    assert result.exit_code == 0

    # Check for example commands
    assert "--type" in result.stdout
    assert "--status" in result.stdout
    assert "--assignee" in result.stdout
    assert "currentUser()" in result.stdout


def test_usage_prompt_includes_connection_resolution() -> None:
    """Test usage-prompt explains connection resolution priority."""
    result = runner.invoke(app, ["-q", "ai", "usage-prompt"])
    assert result.exit_code == 0

    # Check for connection resolution hierarchy
    assert "--connection" in result.stdout
    assert "BUDJIRA_CONNECTION" in result.stdout
    assert "priority" in result.stdout.lower()


def test_usage_prompt_includes_error_handling() -> None:
    """Test usage-prompt includes error handling guidance."""
    result = runner.invoke(app, ["-q", "ai", "usage-prompt"])
    assert result.exit_code == 0

    # Check for error handling section
    assert "error" in result.stdout.lower()
    assert "authentication" in result.stdout.lower()
