"""AI-related commands for budjira."""

import typer
from rich.console import Console
from rich.markdown import Markdown

from budjira.config.settings import get_settings

app = typer.Typer(
    name="ai",
    help="AI integration commands - generate prompts and guides for AI assistants",
    no_args_is_help=True,
)

console = Console()


def _generate_usage_prompt() -> str:
    """Generate comprehensive AI usage prompt for budjira.

    Returns:
        Markdown-formatted prompt text explaining all budjira functionality
    """
    settings = get_settings()
    template = settings.ai_prompt_template
    return template.render()


@app.command("usage-prompt")
def usage_prompt(
    plain: bool = typer.Option(False, "--plain", "-p", help="Output plain markdown without terminal formatting"),
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

    Examples:
        # Display the guide in terminal (formatted)
        budjira ai usage-prompt

        # Output plain markdown for files/clipboard
        budjira ai usage-prompt --plain

        # Save to file
        budjira ai usage-prompt --plain > .claude/ai-usage-prompt.md

        # Copy to clipboard (requires xclip/pbcopy)
        budjira ai usage-prompt --plain | xclip -selection clipboard
    """
    prompt = _generate_usage_prompt()

    if plain:
        # Output raw markdown for file/clipboard
        print(prompt)
    else:
        # Render as Markdown for beautiful terminal output
        md = Markdown(prompt)
        console.print(md)
