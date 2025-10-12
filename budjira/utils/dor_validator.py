"""Definition of Ready (DoR) validation utilities."""

from __future__ import annotations

import re

from budjira.models.dor import DorTemplate, ValidationResult


def validate_description(description: str | None, template: DorTemplate) -> ValidationResult:
    """Validate a description against a DoR template.

    Args:
        description: Issue description text to validate
        template: DoR template to validate against

    Returns:
        ValidationResult with validation status and messages
    """
    if not description:
        description = ""

    result = ValidationResult(valid=True)

    # Extract sections from description
    found_sections = extract_sections(description)

    # Check required sections
    for section in template.sections:
        if not section.required:
            continue

        if section.name not in found_sections:
            result.missing_sections.append(section.name)
            result.errors.append(f"Required section '{section.name}' is missing")
            result.valid = False
            continue

        # Check if section is empty
        section_content = found_sections[section.name].strip()
        if not section_content or section_content == section.placeholder.strip():
            result.warnings.append(f"Section '{section.name}' appears to be empty or contains only placeholder text")

    return result


def extract_sections(description: str) -> dict[str, str]:
    """Extract sections from a markdown description.

    Sections are identified by markdown headers (## Section Name).

    Args:
        description: Markdown description text

    Returns:
        Dictionary mapping section names to their content
    """
    sections: dict[str, str] = {}

    # Split by ## headers
    parts = re.split(r"^## (.+)$", description, flags=re.MULTILINE)

    # First part is content before any section (ignore for now)
    # Remaining parts alternate between section name and content
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            section_name = parts[i].strip()
            section_content = parts[i + 1].strip()
            sections[section_name] = section_content

    return sections


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result as a human-readable message.

    Args:
        result: Validation result to format

    Returns:
        Formatted message string
    """
    lines = []

    if result.valid and not result.has_warnings:
        lines.append("✓ DoR validation passed")
        return "\n".join(lines)

    if result.has_errors:
        lines.append("✗ DoR validation failed:")
        lines.append("")

        if result.missing_sections:
            lines.append("Missing required sections:")
            for section in result.missing_sections:
                lines.append(f"  • {section}")
            lines.append("")

        if result.errors:
            lines.append("Errors:")
            for error in result.errors:
                lines.append(f"  • {error}")
            lines.append("")

    if result.has_warnings:
        if not result.has_errors:
            lines.append("⚠ DoR validation warnings:")
            lines.append("")

        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  • {warning}")

    return "\n".join(lines)
