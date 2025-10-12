"""Tests for DoR validator."""

from budjira.models.dor import DEFAULT_STORY_TEMPLATE, DorSection, DorTemplate
from budjira.utils.dor_validator import (
    extract_sections,
    format_validation_result,
    validate_description,
)


class TestExtractSections:
    """Test section extraction from markdown."""

    def test_extract_single_section(self) -> None:
        """Test extracting a single section."""
        description = """## Context
This is the context."""

        sections = extract_sections(description)

        assert "Context" in sections
        assert sections["Context"] == "This is the context."

    def test_extract_multiple_sections(self) -> None:
        """Test extracting multiple sections."""
        description = """## Context
Background info

## User Story
As a user...

## Acceptance Criteria
- [ ] First criterion"""

        sections = extract_sections(description)

        assert len(sections) == 3
        assert "Context" in sections
        assert "User Story" in sections
        assert "Acceptance Criteria" in sections

    def test_extract_no_sections(self) -> None:
        """Test extracting from description with no sections."""
        description = "Just some text without sections"

        sections = extract_sections(description)

        assert len(sections) == 0

    def test_extract_with_content_before_sections(self) -> None:
        """Test that content before first section is ignored."""
        description = """Some intro text

## Section 1
Content 1"""

        sections = extract_sections(description)

        assert len(sections) == 1
        assert "Section 1" in sections


class TestValidateDescription:
    """Test description validation."""

    def test_valid_description(self) -> None:
        """Test validation of valid description."""
        description = """## Context
We need this feature

## User Story
As a developer
I want to validate descriptions
So that issues meet DoR standards

## Acceptance Criteria
- [ ] Validation works
- [ ] Errors are reported"""

        result = validate_description(description, DEFAULT_STORY_TEMPLATE)

        assert result.valid is True
        assert len(result.missing_sections) == 0
        assert len(result.errors) == 0

    def test_missing_required_section(self) -> None:
        """Test validation with missing required section."""
        description = """## User Story
As a user...

## Acceptance Criteria
- [ ] Criterion 1"""

        result = validate_description(description, DEFAULT_STORY_TEMPLATE)

        assert result.valid is False
        assert "Context" in result.missing_sections
        assert len(result.errors) > 0

    def test_empty_description(self) -> None:
        """Test validation of empty description."""
        result = validate_description("", DEFAULT_STORY_TEMPLATE)

        assert result.valid is False
        assert len(result.missing_sections) == 3  # All required sections

    def test_none_description(self) -> None:
        """Test validation of None description."""
        result = validate_description(None, DEFAULT_STORY_TEMPLATE)

        assert result.valid is False
        assert len(result.missing_sections) == 3

    def test_empty_section_content_warning(self) -> None:
        """Test that empty sections generate warnings."""
        description = """## Context


## User Story


## Acceptance Criteria
"""

        result = validate_description(description, DEFAULT_STORY_TEMPLATE)

        assert result.valid is True  # Sections exist
        assert len(result.warnings) > 0  # But they're empty

    def test_optional_section_not_required(self) -> None:
        """Test that optional sections don't cause validation failure."""
        template = DorTemplate(
            issue_type="Test",
            sections=[
                DorSection(name="Required", required=True),
                DorSection(name="Optional", required=False),
            ],
            template_text="## Required\n\n## Optional\n",
            enabled=True,
        )

        description = "## Required\nSome content"

        result = validate_description(description, template)

        assert result.valid is True
        assert len(result.missing_sections) == 0


class TestFormatValidationResult:
    """Test validation result formatting."""

    def test_format_success(self) -> None:
        """Test formatting successful validation."""
        from budjira.models.dor import ValidationResult

        result = ValidationResult(valid=True)

        formatted = format_validation_result(result)

        assert "✓" in formatted
        assert "passed" in formatted.lower()

    def test_format_with_errors(self) -> None:
        """Test formatting validation with errors."""
        from budjira.models.dor import ValidationResult

        result = ValidationResult(
            valid=False,
            missing_sections=["Context", "User Story"],
            errors=["Missing Context", "Missing User Story"],
        )

        formatted = format_validation_result(result)

        assert "✗" in formatted
        assert "failed" in formatted.lower()
        assert "Context" in formatted
        assert "User Story" in formatted

    def test_format_with_warnings(self) -> None:
        """Test formatting validation with warnings."""
        from budjira.models.dor import ValidationResult

        result = ValidationResult(
            valid=True,
            warnings=["Section appears empty"],
        )

        formatted = format_validation_result(result)

        assert "⚠" in formatted
        assert "warning" in formatted.lower()
