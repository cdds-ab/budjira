"""CLI commands for managing Definition of Ready (DoR) templates."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from budjira.config.settings import get_settings
from budjira.utils.editor import open_editor
from budjira.utils.errors import BudjiraError

app = typer.Typer(
    name="dor",
    help="Manage Definition of Ready (DoR) templates for issue types",
    no_args_is_help=True,
)

console = Console()


@app.command("list")
def list_templates() -> None:
    """List all available DoR templates.

    Shows which issue types have templates configured and whether they are enabled.

    Example:
        budjira dor list
    """
    try:
        settings = get_settings()
        templates = settings.dor_templates

        if not templates.templates:
            console.print("[yellow]No DoR templates configured.[/yellow]")
            console.print("\nDefault templates will be created on first use.")
            return

        console.print("\n[cyan bold]Definition of Ready Templates[/cyan bold]\n")

        table = Table(show_header=True)
        table.add_column("Issue Type", style="cyan")
        table.add_column("Sections", style="")
        table.add_column("Required", style="yellow")
        table.add_column("Status", style="")

        for issue_type, template in templates.templates.items():
            section_count = len(template.sections)
            required_count = sum(1 for s in template.sections if s.required)
            section_names = ", ".join(s.name for s in template.sections[:3])
            if len(template.sections) > 3:
                section_names += ", ..."

            status = "✓ Enabled" if template.enabled else "✗ Disabled"
            status_style = "green" if template.enabled else "dim"

            table.add_row(
                issue_type,
                f"{section_count} sections ({section_names})",
                f"{required_count} required",
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(table)

        console.print(
            f"\n[dim]Validation level: {templates.default_validation_level}[/dim]",
        )

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("show")
def show_template(
    issue_type: str = typer.Argument(help="Issue type (e.g., Story, Bug, Task)"),
) -> None:
    """Show details of a DoR template.

    Displays the template structure, sections, and full template text.

    Example:
        budjira dor show Story
    """
    try:
        settings = get_settings()
        templates = settings.dor_templates

        template = templates.get_template(issue_type)
        if not template:
            console.print(
                f"[yellow]No template found for issue type '{issue_type}'[/yellow]",
            )
            available = ", ".join(templates.templates.keys())
            console.print(f"\nAvailable templates: {available}")
            raise typer.Exit(1)

        console.print(f"\n[cyan bold]DoR Template: {issue_type}[/cyan bold]\n")

        # Show sections
        table = Table(show_header=True)
        table.add_column("Section", style="cyan")
        table.add_column("Required", style="")
        table.add_column("Help Text", style="dim")

        for section in template.sections:
            required = "✓ Required" if section.required else "Optional"
            help_text = section.help_text or ""
            if len(help_text) > 50:
                help_text = help_text[:47] + "..."

            table.add_row(section.name, required, help_text)

        console.print(table)

        # Show full template
        console.print("\n[cyan bold]Template Text:[/cyan bold]\n")
        md = Markdown(template.template_text)
        console.print(md)

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("edit")
def edit_template(
    issue_type: str = typer.Argument(help="Issue type (e.g., Story, Bug, Task)"),
) -> None:
    """Edit a DoR template in your text editor.

    Opens the template in $EDITOR for editing. The template must maintain
    the ## Section Name format for proper parsing.

    Example:
        budjira dor edit Story
    """
    try:
        settings = get_settings()
        templates = settings.dor_templates

        template = templates.get_template(issue_type)
        if not template:
            console.print(
                f"[yellow]No template found for issue type '{issue_type}'[/yellow]",
            )
            available = ", ".join(templates.templates.keys())
            console.print(f"\nAvailable templates: {available}")
            raise typer.Exit(1)

        # Edit template in editor
        console.print(f"\n[dim]Opening template for {issue_type} in editor...[/dim]")
        new_content = open_editor(
            initial_content=template.template_text,
            file_extension=".md",
            editor=settings.global_config.editor,
        )

        # Update template
        template.template_text = new_content
        templates.add_template(template)
        settings.save_dor_templates(templates)

        console.print(f"\n[green]✓[/green] Template for {issue_type} updated")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("validate")
def validate_template(
    issue_type: str = typer.Argument(help="Issue type (e.g., Story, Bug, Task)"),
) -> None:
    """Validate a DoR template structure.

    Checks that the template has the correct format and all required sections.

    Example:
        budjira dor validate Story
    """
    try:
        settings = get_settings()
        templates = settings.dor_templates

        template = templates.get_template(issue_type)
        if not template:
            console.print(
                f"[yellow]No template found for issue type '{issue_type}'[/yellow]",
            )
            raise typer.Exit(1)

        # Basic validation
        errors = []

        if not template.template_text.strip():
            errors.append("Template text is empty")

        # Check for section markers
        import re

        section_markers = re.findall(r"^## (.+)$", template.template_text, re.MULTILINE)

        if not section_markers:
            errors.append("No sections found (expected ## Section Name format)")

        # Check that required sections are in template
        for section in template.sections:
            if section.required and section.name not in section_markers:
                errors.append(f"Required section '{section.name}' not found in template")

        if errors:
            console.print(f"\n[red]✗ Template validation failed for {issue_type}:[/red]\n")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)

        console.print(f"\n[green]✓ Template for {issue_type} is valid[/green]")
        console.print(f"\nFound {len(section_markers)} sections: {', '.join(section_markers)}")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
