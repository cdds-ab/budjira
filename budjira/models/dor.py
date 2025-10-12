"""Definition of Ready (DoR) models for issue templates."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ValidationLevel(str, Enum):
    """DoR validation enforcement levels."""

    STRICT = "strict"  # Block creation if DoR not met
    WARN = "warn"  # Show warnings but allow creation
    OFF = "off"  # No DoR enforcement


class DorSection(BaseModel):
    """Definition of a single DoR section."""

    name: str = Field(
        description="Section name (e.g., 'Context', 'User Story')",
    )
    required: bool = Field(
        default=True,
        description="Whether this section is required",
    )
    placeholder: str = Field(
        default="",
        description="Placeholder text for the section",
    )
    help_text: str | None = Field(
        default=None,
        description="Optional help text explaining what to write",
    )


class DorTemplate(BaseModel):
    """DoR template for a specific issue type."""

    issue_type: str = Field(
        description="Jira issue type (Story, Bug, Task, etc.)",
    )
    sections: list[DorSection] = Field(
        default_factory=list,
        description="List of sections in the template",
    )
    template_text: str = Field(
        description="Full template text with placeholders",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this template is active",
    )


class DorTemplateConfig(BaseModel):
    """Configuration for all DoR templates."""

    templates: dict[str, DorTemplate] = Field(
        default_factory=dict,
        description="Templates keyed by issue type",
    )
    default_validation_level: ValidationLevel = Field(
        default=ValidationLevel.WARN,
        description="Default validation level for all templates",
    )

    def get_template(self, issue_type: str) -> DorTemplate | None:
        """Get template for a specific issue type.

        Args:
            issue_type: Issue type to get template for

        Returns:
            Template if found and enabled, None otherwise
        """
        template = self.templates.get(issue_type)
        if template and template.enabled:
            return template
        return None

    def add_template(self, template: DorTemplate) -> None:
        """Add or update a template.

        Args:
            template: Template to add/update
        """
        self.templates[template.issue_type] = template

    def remove_template(self, issue_type: str) -> bool:
        """Remove a template.

        Args:
            issue_type: Issue type to remove template for

        Returns:
            True if template was removed, False if not found
        """
        if issue_type in self.templates:
            del self.templates[issue_type]
            return True
        return False


class ValidationResult(BaseModel):
    """Result of DoR validation."""

    valid: bool = Field(
        description="Whether the description meets DoR requirements",
    )
    missing_sections: list[str] = Field(
        default_factory=list,
        description="List of required sections that are missing",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical validation warnings",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Critical validation errors",
    )

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0 or len(self.missing_sections) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


# Default templates
DEFAULT_STORY_TEMPLATE = DorTemplate(
    issue_type="Story",
    sections=[
        DorSection(
            name="Context",
            required=True,
            placeholder="Why do we need this? What problem are we solving?",
            help_text="Explain the background and motivation for this story",
        ),
        DorSection(
            name="User Story",
            required=True,
            placeholder="As a [role]\nI want to [action]\nSo that [benefit]",
            help_text="Describe the feature from the user's perspective",
        ),
        DorSection(
            name="Acceptance Criteria",
            required=True,
            placeholder="- [ ] First criterion\n- [ ] Second criterion",
            help_text="List specific, testable requirements",
        ),
    ],
    template_text="""## Context


## User Story
As a [role]
I want to [action]
So that [benefit]

## Acceptance Criteria
- [ ]
- [ ]
""",
    enabled=True,
)

DEFAULT_BUG_TEMPLATE = DorTemplate(
    issue_type="Bug",
    sections=[
        DorSection(
            name="Steps to Reproduce",
            required=True,
            placeholder="1. Go to...\n2. Click on...\n3. See error",
            help_text="Detailed steps to reproduce the bug",
        ),
        DorSection(
            name="Expected Behavior",
            required=True,
            placeholder="What should happen?",
            help_text="Describe the correct/expected behavior",
        ),
        DorSection(
            name="Actual Behavior",
            required=True,
            placeholder="What actually happens?",
            help_text="Describe what actually happens (the bug)",
        ),
        DorSection(
            name="Environment",
            required=False,
            placeholder="Browser, OS, version, etc.",
            help_text="Relevant environment details",
        ),
    ],
    template_text="""## Steps to Reproduce
1.
2.
3.

## Expected Behavior


## Actual Behavior


## Environment

""",
    enabled=True,
)

DEFAULT_TASK_TEMPLATE = DorTemplate(
    issue_type="Task",
    sections=[
        DorSection(
            name="Description",
            required=True,
            placeholder="What needs to be done?",
            help_text="Clear description of the task",
        ),
        DorSection(
            name="Acceptance Criteria",
            required=False,
            placeholder="- [ ] Done when...",
            help_text="Optional: How do we know it's complete?",
        ),
    ],
    template_text="""## Description


## Acceptance Criteria
- [ ]
""",
    enabled=True,
)


def get_default_templates() -> DorTemplateConfig:
    """Get default DoR template configuration.

    Returns:
        Default template configuration with Story, Bug, and Task templates
    """
    config = DorTemplateConfig()
    config.add_template(DEFAULT_STORY_TEMPLATE)
    config.add_template(DEFAULT_BUG_TEMPLATE)
    config.add_template(DEFAULT_TASK_TEMPLATE)
    return config
