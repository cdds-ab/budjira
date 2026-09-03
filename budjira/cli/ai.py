"""AI-related commands for budjira."""

from __future__ import annotations

import shutil
from datetime import datetime
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from budjira.config.metadata_cache import MetadataCache
from budjira.config.settings import get_settings
from budjira.models.ai_prompt import compute_template_hash, get_default_ai_prompt_template

if TYPE_CHECKING:
    from budjira.models.connection import Connection

app = typer.Typer(
    name="ai",
    help="AI integration commands - generate prompts and guides for AI assistants",
    no_args_is_help=True,
)

console = Console()


def _generate_usage_prompt(connection: Connection | None = None, use_defaults: bool = False) -> str:
    """Generate comprehensive AI usage prompt for budjira.

    Args:
        connection: Optional connection to include project-specific prompt from
        use_defaults: Render the built-in template instead of the user's local
            overlay, so the output is a function of the code alone (issue #105)

    Returns:
        Markdown-formatted prompt text explaining all budjira functionality
    """
    template = get_default_ai_prompt_template() if use_defaults else get_settings().ai_prompt_template
    base_prompt = template.render()

    # Append project-specific prompt if connection has one
    if connection is not None and connection.ai_prompt:
        base_prompt += f"\n\n# Project-Specific: {connection.name}\n\n{connection.ai_prompt}"

    # Append discovered project metadata if available
    if connection is not None:
        metadata_section = _generate_metadata_section(connection)
        if metadata_section:
            base_prompt += metadata_section

    return base_prompt


def _generate_metadata_section(connection: Connection) -> str:
    """Generate markdown section from cached project metadata.

    Args:
        connection: Connection to load metadata for

    Returns:
        Markdown string with metadata, or empty string if no metadata
    """
    try:
        settings = get_settings()
        cache = MetadataCache(settings.cache_dir)
        metadata = cache.load(connection)
        if metadata is None:
            return ""

        lines = [
            f"\n\n# Discovered Project Metadata: {connection.name} ({metadata.project_key})",
        ]

        if metadata.issue_types:
            lines.append("\n## Available Issue Types")
            for it in metadata.issue_types:
                required_fields = [f.name for f in it.fields if f.required]
                if required_fields:
                    lines.append(f"- {it.name} (required: {', '.join(required_fields)})")
                else:
                    lines.append(f"- {it.name}")

        if metadata.priorities:
            lines.append(f"\n## Priorities\n{', '.join(metadata.priorities)}")

        if metadata.components:
            lines.append(f"\n## Components\n{', '.join(metadata.components)}")

        return "\n".join(lines)
    except Exception:
        return ""


@app.command("usage-prompt")
def usage_prompt(
    plain: bool = typer.Option(False, "--plain", "-p", help="Output plain markdown without terminal formatting"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Include project-specific AI prompt from this connection",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Render the built-in template, ignoring a local ai-prompt-template.toml",
    ),
) -> None:
    """Generate comprehensive usage guide for AI assistants.

    Outputs a detailed, markdown-formatted guide explaining all budjira
    functionality. This prompt can be provided to AI assistants to help
    them understand and use budjira effectively.

    The guide includes:
    - Connection management
    - Issue search (JQL and filters)
    - Issue creation (interactive and non-interactive)
    - Issue updates and transitions
    - Epic management
    - Update management
    - Common workflows and examples
    - Error handling patterns

    When --connection is specified, the connection's project-specific AI prompt
    (if configured) will be appended to the generated guide.

    By default the guide is rendered from ~/.config/budjira/ai-prompt-template.toml
    when that file exists, so local edits show up. Use --defaults to render the
    built-in template instead: the output then depends only on the installed
    version, which is what a file checked into a repository needs.

    Examples:
        # Display the guide in terminal (formatted)
        budjira ai usage-prompt

        # Output plain markdown for files/clipboard
        budjira ai usage-prompt --plain

        # Include project-specific prompt from a connection
        budjira ai usage-prompt --connection my-project --plain

        # Save a reproducible copy to a file
        budjira ai usage-prompt --defaults --plain > .claude/ai-usage-prompt.md

        # Copy to clipboard (requires xclip/pbcopy)
        budjira ai usage-prompt --plain | xclip -selection clipboard
    """
    # Look up connection if specified
    connection = None
    if connection_name:
        settings = get_settings()
        connection = settings.connections.find_by_name(connection_name)
        if connection is None:
            console.print(f"[red]Error:[/red] Connection '{connection_name}' not found", style="red")
            raise typer.Exit(1)

    prompt = _generate_usage_prompt(connection, use_defaults=defaults)

    if plain:
        # Output raw markdown for file/clipboard
        print(prompt)
    else:
        # Render as Markdown for beautiful terminal output
        md = Markdown(prompt)
        console.print(md)


@app.command("reset-prompt-template")
def reset_prompt_template(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Restore the built-in AI usage prompt template.

    Overwrites ~/.config/budjira/ai-prompt-template.toml with the built-in
    default of the installed version, keeping a timestamped backup next to it.
    Use this when the file is stale (it is auto-generated on first use and
    older versions never refreshed it) or to undo local customizations.

    Files without local modifications are refreshed automatically on load -
    this command is for files the update check cannot safely touch (#126).

    Examples:
        # With confirmation
        budjira ai reset-prompt-template

        # Non-interactive
        budjira ai reset-prompt-template --force
    """
    settings = get_settings()
    template_file = settings.ai_prompt_template_file

    default = get_default_ai_prompt_template()
    default.default_hash = compute_template_hash(default)

    if template_file.exists():
        backup = template_file.with_name(f"{template_file.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        if not force and not Confirm.ask(
            f"Overwrite {template_file} with the built-in default?\nBackup goes to {backup.name}",
            default=True,
        ):
            console.print("Cancelled.")
            raise typer.Abort()
        shutil.copy2(template_file, backup)
        console.print(f"[green]✓[/green] Backup written: {backup}")

    settings.save_ai_prompt_template(default)
    console.print(f"[green]✓[/green] Restored built-in AI prompt template: {template_file}")
