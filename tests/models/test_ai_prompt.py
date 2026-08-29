"""Tests for AI prompt template models."""

from budjira.models.ai_prompt import AiPromptSection, AiPromptTemplate, get_default_ai_prompt_template


class TestAiPromptSection:
    """Test AI prompt section model."""

    def test_section_creation(self) -> None:
        """Test creating an AI prompt section."""
        section = AiPromptSection(
            title="Connection Management",
            content="## Connection Management\n\nSome content here.",
            order=1,
            enabled=True,
        )

        assert section.title == "Connection Management"
        assert section.content == "## Connection Management\n\nSome content here."
        assert section.order == 1
        assert section.enabled is True

    def test_section_defaults(self) -> None:
        """Test section with default enabled value."""
        section = AiPromptSection(
            title="Test Section",
            content="Content",
            order=0,
        )

        assert section.title == "Test Section"
        assert section.content == "Content"
        assert section.order == 0
        assert section.enabled is True  # Default


class TestAiPromptTemplate:
    """Test AI prompt template model."""

    def test_template_creation(self) -> None:
        """Test creating an AI prompt template."""
        sections = [
            AiPromptSection(title="Section 1", content="Content 1", order=0),
            AiPromptSection(title="Section 2", content="Content 2", order=1),
        ]
        template = AiPromptTemplate(version="1.0", sections=sections)

        assert template.version == "1.0"
        assert len(template.sections) == 2

    def test_template_defaults(self) -> None:
        """Test template with default values."""
        template = AiPromptTemplate()

        assert template.version == "1.0"
        assert template.sections == []

    def test_render_basic(self) -> None:
        """Test rendering template with two sections."""
        sections = [
            AiPromptSection(title="First", content="First content", order=0),
            AiPromptSection(title="Second", content="Second content", order=1),
        ]
        template = AiPromptTemplate(sections=sections)

        result = template.render()

        assert result == "First content\n\nSecond content"

    def test_render_with_ordering(self) -> None:
        """Test that sections are sorted by order field."""
        sections = [
            AiPromptSection(title="Third", content="Third content", order=2),
            AiPromptSection(title="First", content="First content", order=0),
            AiPromptSection(title="Second", content="Second content", order=1),
        ]
        template = AiPromptTemplate(sections=sections)

        result = template.render()

        assert result == "First content\n\nSecond content\n\nThird content"

    def test_render_skips_disabled(self) -> None:
        """Test that disabled sections are not included in render output."""
        sections = [
            AiPromptSection(title="Enabled 1", content="Content 1", order=0, enabled=True),
            AiPromptSection(title="Disabled", content="Skipped", order=1, enabled=False),
            AiPromptSection(title="Enabled 2", content="Content 2", order=2, enabled=True),
        ]
        template = AiPromptTemplate(sections=sections)

        result = template.render()

        assert result == "Content 1\n\nContent 2"
        assert "Skipped" not in result

    def test_render_empty_template(self) -> None:
        """Test rendering empty template."""
        template = AiPromptTemplate(sections=[])

        result = template.render()

        assert result == ""

    def test_get_section_exists(self) -> None:
        """Test retrieving a section by title."""
        sections = [
            AiPromptSection(title="Overview", content="Overview content", order=0),
            AiPromptSection(title="Details", content="Details content", order=1),
        ]
        template = AiPromptTemplate(sections=sections)

        section = template.get_section("Overview")

        assert section is not None
        assert section.title == "Overview"
        assert section.content == "Overview content"

    def test_get_section_not_exists(self) -> None:
        """Test retrieving a section that doesn't exist."""
        template = AiPromptTemplate(sections=[])

        section = template.get_section("NonExistent")

        assert section is None

    def test_add_section_new(self) -> None:
        """Test adding a new section to template."""
        template = AiPromptTemplate(sections=[])
        new_section = AiPromptSection(title="New Section", content="New content", order=0)

        template.add_section(new_section)

        assert len(template.sections) == 1
        assert template.sections[0].title == "New Section"

    def test_add_section_replaces_existing(self) -> None:
        """Test that adding a section with same title replaces the existing one."""
        original = AiPromptSection(title="Test", content="Original content", order=0)
        template = AiPromptTemplate(sections=[original])

        updated = AiPromptSection(title="Test", content="Updated content", order=1)
        template.add_section(updated)

        assert len(template.sections) == 1
        assert template.sections[0].content == "Updated content"
        assert template.sections[0].order == 1

    def test_remove_section_exists(self) -> None:
        """Test removing a section that exists."""
        sections = [
            AiPromptSection(title="Keep", content="Content", order=0),
            AiPromptSection(title="Remove", content="Content", order=1),
        ]
        template = AiPromptTemplate(sections=sections)

        result = template.remove_section("Remove")

        assert result is True
        assert len(template.sections) == 1
        assert template.sections[0].title == "Keep"

    def test_remove_section_not_exists(self) -> None:
        """Test removing a section that doesn't exist."""
        template = AiPromptTemplate(sections=[])

        result = template.remove_section("NonExistent")

        assert result is False


class TestGetDefaultAiPromptTemplate:
    """Test default AI prompt template generation."""

    def test_default_template_has_sections(self) -> None:
        """Test that default template contains expected number of sections."""
        template = get_default_ai_prompt_template()

        assert template.version == "1.0"
        assert len(template.sections) == 27  # All sections including v1.27.x Project Metadata

    def test_default_template_all_enabled(self) -> None:
        """Test that all default sections are enabled."""
        template = get_default_ai_prompt_template()

        for section in template.sections:
            assert section.enabled is True

    def test_default_template_ordered(self) -> None:
        """Test that default sections are correctly ordered."""
        template = get_default_ai_prompt_template()

        orders = [section.order for section in template.sections]
        assert orders == sorted(orders)  # Should be in ascending order

    def test_default_template_has_key_sections(self) -> None:
        """Test that default template contains key expected sections."""
        template = get_default_ai_prompt_template()

        section_titles = {s.title for s in template.sections}

        # Check for some critical sections
        assert "Header and Overview" in section_titles
        assert "Connection Management" in section_titles
        assert "Custom Fields Configuration" in section_titles  # v1.13.0
        assert "Connection-Specific AI Prompts" in section_titles  # v1.13.0
        assert "Searching Issues" in section_titles
        assert "Creating Issues" in section_titles
        assert "Tempo Timesheets Integration" in section_titles
        assert "Common Workflows for AI Assistants" in section_titles

    def test_default_template_render_not_empty(self) -> None:
        """Test that rendering default template produces output."""
        template = get_default_ai_prompt_template()

        result = template.render()

        assert len(result) > 1000  # Should be substantial content
        assert "budjira" in result  # Should mention the tool name
        assert "## " in result  # Should contain markdown headings

    def test_default_template_has_unique_titles(self) -> None:
        """Test that all section titles are unique."""
        template = get_default_ai_prompt_template()

        titles = [s.title for s in template.sections]
        unique_titles = set(titles)

        assert len(titles) == len(unique_titles)

    def test_default_template_sections_have_content(self) -> None:
        """Test that all sections have non-empty content."""
        template = get_default_ai_prompt_template()

        for section in template.sections:
            assert len(section.content) > 0
            assert section.content.strip() != ""

    def test_default_template_preserves_markdown(self) -> None:
        """Test that sections preserve markdown formatting."""
        template = get_default_ai_prompt_template()

        # Check that some sections contain markdown elements
        connection_section = template.get_section("Connection Management")
        assert connection_section is not None
        assert "## Connection Management" in connection_section.content
        assert "```bash" in connection_section.content

    def test_default_template_first_section_is_header(self) -> None:
        """Test that first section (order 0) is the header."""
        template = get_default_ai_prompt_template()

        header = min(template.sections, key=lambda s: s.order)
        assert header.order == 0
        assert header.title == "Header and Overview"
        assert "# budjira" in header.content

    def test_default_template_last_section_is_footer(self) -> None:
        """Test that last section (order 22) is the footer."""
        template = get_default_ai_prompt_template()

        footer = max(template.sections, key=lambda s: s.order)
        assert footer.order == 22
        assert footer.title == "Footer"
        assert "**This guide is generated by budjira itself" in footer.content
