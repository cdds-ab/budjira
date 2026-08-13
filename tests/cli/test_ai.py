"""Test AI CLI commands."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl fields during validation

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from budjira.cli.main import app
from budjira.models.connection import Connection, ConnectionList
from budjira.models.project_metadata import (
    FieldMetadata,
    IssueTypeMetadata,
    ProjectMetadata,
)
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


class TestUsagePromptWithMetadata:
    """Test usage-prompt command with project metadata integration."""

    @patch("budjira.cli.ai.MetadataCache")
    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_includes_metadata(
        self,
        mock_get_settings: MagicMock,
        mock_cache_class: MagicMock,
    ) -> None:
        """Test that --connection includes discovered project metadata."""
        connection = Connection(
            name="meta-project",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        # Mock metadata cache
        metadata = ProjectMetadata(
            project_key="TEST",
            project_name="Test Project",
            issue_types=[
                IssueTypeMetadata(
                    id="1",
                    name="Change Request",
                    fields=[
                        FieldMetadata(field_id="summary", name="Summary", required=True),
                        FieldMetadata(field_id="priority", name="Priority", required=True),
                    ],
                ),
                IssueTypeMetadata(id="2", name="Bug"),
            ],
            priorities=["FK1", "FK2", "FK3"],
            components=["Backend", "Frontend"],
            fetched_at=datetime.now(tz=timezone.utc),
        )
        mock_cache_instance = MagicMock()
        mock_cache_instance.load.return_value = metadata
        mock_cache_class.return_value = mock_cache_instance

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "meta-project", "--plain"])

        assert result.exit_code == 0
        assert "Discovered Project Metadata" in result.stdout
        assert "Change Request" in result.stdout
        assert "Summary" in result.stdout
        assert "FK1" in result.stdout
        assert "Backend" in result.stdout

    @patch("budjira.cli.ai.MetadataCache")
    @patch("budjira.cli.ai.get_settings")
    def test_usage_prompt_without_metadata(
        self,
        mock_get_settings: MagicMock,
        mock_cache_class: MagicMock,
    ) -> None:
        """Test that --connection works when no metadata is cached."""
        connection = Connection(
            name="no-meta",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )
        connection_list = ConnectionList(connections=[connection])

        mock_template = MagicMock()
        mock_template.render.return_value = "# budjira AI Usage Guide\n\nBase content here."

        mock_settings = MagicMock()
        mock_settings.connections = connection_list
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        mock_cache_instance = MagicMock()
        mock_cache_instance.load.return_value = None
        mock_cache_class.return_value = mock_cache_instance

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--connection", "no-meta", "--plain"])

        assert result.exit_code == 0
        assert "Discovered Project Metadata" not in result.stdout


class TestUsagePromptDefaults:
    """--defaults renders the built-in template, so committed docs are reproducible (#105)."""

    @patch("budjira.cli.ai.get_settings")
    def test_defaults_ignores_the_local_template(self, mock_get_settings: MagicMock) -> None:
        """A stale local template must not leak into the generated output."""
        mock_template = MagicMock()
        mock_template.render.return_value = "# Stale local template"
        mock_settings = MagicMock()
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--defaults", "--plain"])

        assert result.exit_code == 0
        assert "Stale local template" not in result.stdout
        mock_template.render.assert_not_called()

    @patch("budjira.cli.ai.get_settings")
    def test_local_template_is_used_without_the_flag(self, mock_get_settings: MagicMock) -> None:
        """The user template overlay stays intact for interactive use."""
        mock_template = MagicMock()
        mock_template.render.return_value = "# Stale local template"
        mock_settings = MagicMock()
        mock_settings.ai_prompt_template = mock_template
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--plain"])

        assert result.exit_code == 0
        assert "Stale local template" in result.stdout

    def test_defaults_documents_the_description_dialect_option(self) -> None:
        """The built-in template covers the options the CLI actually offers."""
        result = runner.invoke(app, ["-q", "ai", "usage-prompt", "--defaults", "--plain"])

        assert result.exit_code == 0
        assert result.stdout.count("--description-dialect") >= 2
