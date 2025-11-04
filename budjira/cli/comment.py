"""Comment management commands."""

from __future__ import annotations

import logging

import typer
from rich.console import Console

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.editor import open_editor
from budjira.utils.errors import BudjiraError

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Add comments to Jira issues")


@app.command(name="add")
def add_comment(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    text: str | None = typer.Argument(None, help="Comment text (omit to open editor)"),
    editor: bool = typer.Option(False, "--editor", "-e", help="Open editor for multi-line comment"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides default)",
    ),
) -> None:
    """Add a comment to a Jira issue.

    Add comments without logging time (unlike worklog add).

    Examples:
        # Quick single-line comment
        budjira comment add PROJ-123 "Fixed in latest deployment"

        # Multi-line comment via editor
        budjira comment add PROJ-123 --editor

        # Open editor if no text provided
        budjira comment add PROJ-123
    """
    try:
        # Resolve connection
        connection = get_active_connection(connection_name)

        # Get comment text
        if editor or text is None:
            # Open editor for multi-line input
            initial_content = text if text else ""
            comment_text = open_editor(initial_content, file_extension=".md")

            # Check if user provided content
            if not comment_text.strip():
                console.print("[yellow]No comment text provided. Aborting.[/yellow]")
                raise typer.Exit(0)
        else:
            comment_text = text

        # Create Jira client and add comment
        jira_client = JiraClient.from_connection(connection)
        result = jira_client.add_comment(issue_key, comment_text)

        # Display success message
        console.print(f"\n[green]✓[/green] Comment added to {issue_key}")
        console.print(f"  [dim]Comment ID:[/dim] {result['id']}")
        console.print(f"  [dim]Author:[/dim] {result['author']}")
        if result.get("created"):
            console.print(f"  [dim]Created:[/dim] {result['created']}")

        # Show preview of comment (first 100 chars)
        preview = comment_text[:100]
        if len(comment_text) > 100:
            preview += "..."
        console.print(f"\n[dim]Preview:[/dim] {preview}")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error adding comment")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e
