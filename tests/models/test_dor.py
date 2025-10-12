"""Tests for DoR models."""

from budjira.models.dor import (
    DEFAULT_BUG_TEMPLATE,
    DEFAULT_STORY_TEMPLATE,
    DEFAULT_TASK_TEMPLATE,
    DorSection,
    DorTemplate,
    DorTemplateConfig,
    ValidationLevel,
    ValidationResult,
    get_default_templates,
)


class TestDorSection:
    """Test DoR section model."""

    def test_section_creation(self) -> None:
        """Test creating a DoR section."""
        section = DorSection(
            name="Context",
            required=True,
            placeholder="Why do we need this?",
            help_text="Explain the background",
        )

        assert section.name == "Context"
        assert section.required is True
        assert section.placeholder == "Why do we need this?"
        assert section.help_text == "Explain the background"

    def test_section_defaults(self) -> None:
        """Test section with default values."""
        section = DorSection(name="Optional Section", required=False)

        assert section.name == "Optional Section"
        assert section.required is False
        assert section.placeholder == ""
        assert section.help_text is None


class TestDorTemplate:
    """Test DoR template model."""

    def test_template_creation(self) -> None:
        """Test creating a DoR template."""
        sections = [
            DorSection(name="Section 1", required=True),
            DorSection(name="Section 2", required=False),
        ]
        template = DorTemplate(
            issue_type="Story",
            sections=sections,
            template_text="## Section 1\n\n## Section 2\n",
            enabled=True,
        )

        assert template.issue_type == "Story"
        assert len(template.sections) == 2
        assert template.enabled is True


class TestDorTemplateConfig:
    """Test DoR template configuration."""

    def test_empty_config(self) -> None:
        """Test empty template configuration."""
        config = DorTemplateConfig()

        assert len(config.templates) == 0
        assert config.default_validation_level == ValidationLevel.WARN

    def test_add_template(self) -> None:
        """Test adding a template to configuration."""
        config = DorTemplateConfig()
        template = DEFAULT_STORY_TEMPLATE

        config.add_template(template)

        assert "Story" in config.templates
        assert config.templates["Story"] == template

    def test_get_template(self) -> None:
        """Test retrieving a template."""
        config = DorTemplateConfig()
        config.add_template(DEFAULT_STORY_TEMPLATE)

        template = config.get_template("Story")

        assert template is not None
        assert template.issue_type == "Story"

    def test_get_nonexistent_template(self) -> None:
        """Test retrieving a template that doesn't exist."""
        config = DorTemplateConfig()

        template = config.get_template("NonExistent")

        assert template is None

    def test_get_disabled_template(self) -> None:
        """Test that disabled templates are not returned."""
        config = DorTemplateConfig()
        template = DorTemplate(
            issue_type="Disabled",
            sections=[],
            template_text="",
            enabled=False,
        )
        config.add_template(template)

        result = config.get_template("Disabled")

        assert result is None

    def test_remove_template(self) -> None:
        """Test removing a template."""
        config = DorTemplateConfig()
        config.add_template(DEFAULT_STORY_TEMPLATE)

        removed = config.remove_template("Story")

        assert removed is True
        assert "Story" not in config.templates

    def test_remove_nonexistent_template(self) -> None:
        """Test removing a template that doesn't exist."""
        config = DorTemplateConfig()

        removed = config.remove_template("NonExistent")

        assert removed is False


class TestValidationResult:
    """Test validation result model."""

    def test_valid_result(self) -> None:
        """Test a valid validation result."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.has_errors is False
        assert result.has_warnings is False

    def test_result_with_errors(self) -> None:
        """Test validation result with errors."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            missing_sections=["Context"],
        )

        assert result.valid is False
        assert result.has_errors is True
        assert len(result.errors) == 2
        assert len(result.missing_sections) == 1

    def test_result_with_warnings(self) -> None:
        """Test validation result with warnings."""
        result = ValidationResult(
            valid=True,
            warnings=["Warning 1"],
        )

        assert result.valid is True
        assert result.has_warnings is True
        assert len(result.warnings) == 1


class TestDefaultTemplates:
    """Test default DoR templates."""

    def test_story_template(self) -> None:
        """Test default Story template."""
        assert DEFAULT_STORY_TEMPLATE.issue_type == "Story"
        assert DEFAULT_STORY_TEMPLATE.enabled is True
        assert len(DEFAULT_STORY_TEMPLATE.sections) == 3

        section_names = [s.name for s in DEFAULT_STORY_TEMPLATE.sections]
        assert "Context" in section_names
        assert "User Story" in section_names
        assert "Acceptance Criteria" in section_names

    def test_bug_template(self) -> None:
        """Test default Bug template."""
        assert DEFAULT_BUG_TEMPLATE.issue_type == "Bug"
        assert DEFAULT_BUG_TEMPLATE.enabled is True
        assert len(DEFAULT_BUG_TEMPLATE.sections) == 4

        section_names = [s.name for s in DEFAULT_BUG_TEMPLATE.sections]
        assert "Steps to Reproduce" in section_names
        assert "Expected Behavior" in section_names
        assert "Actual Behavior" in section_names

    def test_task_template(self) -> None:
        """Test default Task template."""
        assert DEFAULT_TASK_TEMPLATE.issue_type == "Task"
        assert DEFAULT_TASK_TEMPLATE.enabled is True
        assert len(DEFAULT_TASK_TEMPLATE.sections) == 2

    def test_get_default_templates(self) -> None:
        """Test getting default template configuration."""
        config = get_default_templates()

        assert len(config.templates) == 3
        assert "Story" in config.templates
        assert "Bug" in config.templates
        assert "Task" in config.templates
