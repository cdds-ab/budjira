"""Test AI CLI commands."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl fields during validation

from pathlib import Path
from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from budjira.models.connection import Connection, ConnectionList
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


class TestUsagePromptWithConnection:
    """Test usage-prompt command with --connection flag."""

    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_with_connection_includes_ai_prompt(
        self,
        mock_get_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that --connection includes project-specific AI prompt."""
        # Create connection with ai_prompt
        ai_prompt = """## Project-Specific Workflow

This project uses custom issue types:
- Change Request: For production changes
- Incident: For production incidents

Always set the 'affected_system' custom field.
"""
        connection = Connection(
            name="my-project",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=ai_prompt,
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "my-project"])

        assert result.exit_code == 0
        # Check that project-specific section header is present
        assert "Project-Specific: my-project" in result.stdout
        # Check that ai_prompt content is included
        assert "Change Request" in result.stdout
        assert "Incident" in result.stdout
        assert "affected_system" in result.stdout

    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_connection_without_ai_prompt(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test --connection with connection that has no ai_prompt."""
        # Create connection without ai_prompt
        connection = Connection(
            name="no-prompt-project",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=None,
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "no-prompt-project"])

        assert result.exit_code == 0
        # Should NOT have project-specific section
        assert "Project-Specific:" not in result.stdout
        # But should still have regular content
        assert "budjira" in result.stdout.lower()

    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_connection_not_found(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test --connection with non-existent connection name."""
        # Empty connection list
        connection_list = ConnectionList(connections=[])

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "non-existent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
        assert "non-existent" in result.stdout

    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_with_connection_plain_output(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test --connection with --plain flag."""
        ai_prompt = "Custom workflow instructions here."
        connection = Connection(
            name="plain-test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=ai_prompt,
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "plain-test", "--plain"])

        assert result.exit_code == 0
        assert "Project-Specific: plain-test" in result.stdout
        assert "Custom workflow instructions here" in result.stdout

    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_without_connection_flag(
        self,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test that without --connection flag, no project-specific prompt is included."""
        # Even if connections exist with ai_prompts, they shouldn't be included
        connection = Connection(
            name="some-project",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt="This should not appear",
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt"])

        assert result.exit_code == 0
        # Should NOT include project-specific content
        assert "Project-Specific:" not in result.stdout
        assert "This should not appear" not in result.stdout
