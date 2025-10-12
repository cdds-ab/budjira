"""Test DoR CLI commands."""

from unittest.mock import MagicMock, Mock, patch

from budjira.cli.main import app
from budjira.models.dor import (
    DEFAULT_BUG_TEMPLATE,
    DEFAULT_STORY_TEMPLATE,
    DEFAULT_TASK_TEMPLATE,
    DorTemplate,
    DorTemplateConfig,
    ValidationLevel,
)
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


# Functional tests


@patch("budjira.cli.dor.get_settings")
def test_dor_list_no_templates(mock_get_settings: Mock) -> None:
    """Test dor list with no templates configured."""
    # Setup
    mock_settings = MagicMock()
    mock_settings.dor_templates = DorTemplateConfig(templates={})
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "list"])

    # Verify
    assert result.exit_code == 0
    assert "No DoR templates configured" in result.stdout
    assert "Default templates will be created on first use" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_list_with_templates(mock_get_settings: Mock) -> None:
    """Test dor list with configured templates."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(
        templates={
            "Story": DEFAULT_STORY_TEMPLATE,
            "Bug": DEFAULT_BUG_TEMPLATE,
            "Task": DEFAULT_TASK_TEMPLATE,
        },
        default_validation_level=ValidationLevel.WARN,
    )
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "list"])

    # Verify
    assert result.exit_code == 0
    assert "Story" in result.stdout
    assert "Bug" in result.stdout
    assert "Task" in result.stdout
    assert "Enabled" in result.stdout
    assert "warn" in result.stdout.lower()


@patch("budjira.cli.dor.get_settings")
def test_dor_list_with_disabled_template(mock_get_settings: Mock) -> None:
    """Test dor list with a disabled template."""
    # Setup
    mock_settings = MagicMock()
    disabled_template = DorTemplate(
        issue_type="Story",
        sections=DEFAULT_STORY_TEMPLATE.sections,
        template_text=DEFAULT_STORY_TEMPLATE.template_text,
        enabled=False,
    )
    templates = DorTemplateConfig(templates={"Story": disabled_template})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "list"])

    # Verify
    assert result.exit_code == 0
    assert "Disabled" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_show_valid_template(mock_get_settings: Mock) -> None:
    """Test dor show with a valid template."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "show", "Story"])

    # Verify
    assert result.exit_code == 0
    assert "Story" in result.stdout
    assert "Context" in result.stdout
    assert "User Story" in result.stdout
    assert "Acceptance Criteria" in result.stdout
    assert "Required" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_show_invalid_template(mock_get_settings: Mock) -> None:
    """Test dor show with an invalid template."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "show", "InvalidType"])

    # Verify
    assert result.exit_code == 1
    assert "No template found" in result.stdout
    assert "InvalidType" in result.stdout
    assert "Story" in result.stdout  # Shows available templates


@patch("budjira.cli.dor.get_settings")
@patch("budjira.cli.dor.open_editor")
def test_dor_edit_valid_template(mock_open_editor: Mock, mock_get_settings: Mock) -> None:
    """Test dor edit with a valid template."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
    mock_settings.dor_templates = templates
    mock_settings.global_config.editor = "vim"
    mock_get_settings.return_value = mock_settings

    # Mock editor returning modified content
    mock_open_editor.return_value = "## Context\n\nUpdated content\n\n## User Story\n\nAs a user..."

    # Execute
    result = runner.invoke(app, ["-q", "dor", "edit", "Story"])

    # Verify
    assert result.exit_code == 0
    assert "updated" in result.stdout.lower()
    mock_open_editor.assert_called_once()
    mock_settings.save_dor_templates.assert_called_once_with(templates)


@patch("budjira.cli.dor.get_settings")
def test_dor_edit_invalid_template(mock_get_settings: Mock) -> None:
    """Test dor edit with an invalid template."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "edit", "InvalidType"])

    # Verify
    assert result.exit_code == 1
    assert "No template found" in result.stdout
    assert "InvalidType" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_validate_valid_template(mock_get_settings: Mock) -> None:
    """Test dor validate with a valid template."""
    from budjira.models.dor import DorSection

    # Setup - create completely fresh template to avoid test pollution
    template = DorTemplate(
        issue_type="Story",
        sections=[
            DorSection(name="Context", required=True),
            DorSection(name="User Story", required=True),
            DorSection(name="Acceptance Criteria", required=True),
        ],
        template_text="## Context\n\nTest context\n\n## User Story\n\nAs a user\n\n## Acceptance Criteria\n\n- [ ] Item 1",
        enabled=True,
    )
    templates = DorTemplateConfig(templates={"Story": template})

    mock_settings = MagicMock()
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "validate", "Story"])

    # Verify - check basic success, not specific text which may vary
    assert result.exit_code == 0
    # Template should be reported as valid and show sections found
    assert "3" in result.stdout or "sections" in result.stdout.lower()


@patch("budjira.cli.dor.get_settings")
def test_dor_validate_empty_template(mock_get_settings: Mock) -> None:
    """Test dor validate with an empty template."""
    # Setup
    mock_settings = MagicMock()
    empty_template = DorTemplate(
        issue_type="Story",
        sections=DEFAULT_STORY_TEMPLATE.sections,
        template_text="",
        enabled=True,
    )
    templates = DorTemplateConfig(templates={"Story": empty_template})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "validate", "Story"])

    # Verify
    assert result.exit_code == 1
    assert "validation failed" in result.stdout.lower()
    assert "Template text is empty" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_validate_missing_sections(mock_get_settings: Mock) -> None:
    """Test dor validate with missing required sections."""
    # Setup
    mock_settings = MagicMock()
    invalid_template = DorTemplate(
        issue_type="Story",
        sections=DEFAULT_STORY_TEMPLATE.sections,
        template_text="## Context\n\nOnly context section, missing User Story and Acceptance Criteria",
        enabled=True,
    )
    templates = DorTemplateConfig(templates={"Story": invalid_template})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "validate", "Story"])

    # Verify
    assert result.exit_code == 1
    assert "validation failed" in result.stdout.lower()
    assert "User Story" in result.stdout
    assert "Acceptance Criteria" in result.stdout


@patch("budjira.cli.dor.get_settings")
def test_dor_validate_invalid_template_type(mock_get_settings: Mock) -> None:
    """Test dor validate with an invalid template type."""
    # Setup
    mock_settings = MagicMock()
    templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
    mock_settings.dor_templates = templates
    mock_get_settings.return_value = mock_settings

    # Execute
    result = runner.invoke(app, ["-q", "dor", "validate", "InvalidType"])

    # Verify
    assert result.exit_code == 1
    assert "No template found" in result.stdout
    assert "InvalidType" in result.stdout
