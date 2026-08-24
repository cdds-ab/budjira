"""Comment management commands."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.editor import open_editor
from budjira.utils.errors import BudjiraError
from budjira.utils.formatter import OutputFormatter

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Manage comments on Jira issues (add, list, show, update, delete)")

_PREVIEW_LENGTH = 100
_LIST_PREVIEW_LENGTH = 80


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


@app.command(name="list")
def list_comments(
    ctx: typer.Context,
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides default)",
    ),
) -> None:
    """List all comments on a Jira issue.

    Shows a table with comment ID, author, creation date and the first line
    of each comment body. Use the ID with 'comment show', 'comment update'
    or 'comment delete'.

    Examples:
        # List comments as table
        budjira comment list PROJ-123

        # List comments as JSON
        budjira --format json comment list PROJ-123
    """
    output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

    try:
        connection = get_active_connection(connection_name)
        jira_client = JiraClient.from_connection(connection)
        comments = jira_client.comments.list(issue_key)

        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json(
                {
                    "issue": issue_key,
                    "total": len(comments),
                    "comments": comments,
                }
            )
            return

        if not comments:
            console.print(f"[yellow]No comments found on {issue_key}[/yellow]")
            return

        table = Table(title=f"Comments on {issue_key}", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Author", style="cyan")
        table.add_column("Created", style="blue")
        table.add_column("Comment", style="white", no_wrap=False)

        for comment in comments:
            table.add_row(
                str(comment["id"]),
                str(comment["author"]),
                _format_date(comment.get("created")),
                _first_line(comment.get("body"), _LIST_PREVIEW_LENGTH),
            )

        console.print(table)
        console.print(f"\n[green]Total: {len(comments)} comment(s)[/green]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error listing comments")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="show")
def show_comment(
    ctx: typer.Context,
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comment_id: str = typer.Argument(..., help="Comment ID (see 'comment list')"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides default)",
    ),
) -> None:
    """Show the full body of a single comment.

    Examples:
        # Show a comment
        budjira comment show PROJ-123 10234

        # Show a comment as JSON
        budjira --format json comment show PROJ-123 10234
    """
    output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

    try:
        connection = get_active_connection(connection_name)
        jira_client = JiraClient.from_connection(connection)
        comment = jira_client.comments.get(issue_key, comment_id)

        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json(comment)
            return

        console.print(f"[bold]Comment {comment['id']} on {issue_key}[/bold]")
        console.print(f"  [dim]Author:[/dim] {comment['author']}")
        if comment.get("created"):
            console.print(f"  [dim]Created:[/dim] {comment['created']}")
        if comment.get("updated"):
            console.print(f"  [dim]Updated:[/dim] {comment['updated']}")
        console.print()
        console.print(comment["body"] or "")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error showing comment")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="update")
def update_comment(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comment_id: str = typer.Argument(..., help="Comment ID (see 'comment list')"),
    text: str | None = typer.Argument(None, help="New comment text (omit to open editor with current body)"),
    editor: bool = typer.Option(False, "--editor", "-e", help="Open editor for multi-line comment"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides default)",
    ),
) -> None:
    """Replace the body of an existing comment.

    Without TEXT the editor opens prefilled with the current comment body,
    so you can adjust the wording in place. This is the reliable way to fix
    a comment — Jira often forbids deleting comments even for their author.

    Examples:
        # Replace body directly
        budjira comment update PROJ-123 10234 "Corrected deployment note"

        # Edit current body in editor
        budjira comment update PROJ-123 10234
    """
    try:
        # Resolve connection
        connection = get_active_connection(connection_name)
        jira_client = JiraClient.from_connection(connection)

        # Get new comment text
        if editor or text is None:
            # Prefill the editor with the given text or the current body
            initial_content = text if text else (jira_client.comments.get(issue_key, comment_id).get("body") or "")
            comment_text = open_editor(initial_content, file_extension=".md")

            # Check if user provided content
            if not comment_text.strip():
                console.print("[yellow]No comment text provided. Aborting.[/yellow]")
                return
        else:
            comment_text = text

        # Update comment
        result = jira_client.comments.update(issue_key, comment_id, comment_text)

        # Display success message
        console.print(f"\n[green]✓[/green] Comment {result['id']} on {issue_key} updated")
        console.print(f"  [dim]Author:[/dim] {result['author']}")
        if result.get("updated"):
            console.print(f"  [dim]Updated:[/dim] {result['updated']}")

        # Show preview of comment (first 100 chars)
        preview = comment_text[:_PREVIEW_LENGTH]
        if len(comment_text) > _PREVIEW_LENGTH:
            preview += "..."
        console.print(f"\n[dim]Preview:[/dim] {preview}")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error updating comment")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="delete")
def delete_comment(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
    comment_id: str = typer.Argument(..., help="Comment ID (see 'comment list')"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    connection_name: str | None = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides default)",
    ),
) -> None:
    """Delete a comment from a Jira issue.

    Note that Jira often forbids deleting comments even for their author.
    If deletion is denied, use 'budjira comment update' to revise the body
    instead.

    Examples:
        # Delete comment with confirmation
        budjira comment delete PROJ-123 10234

        # Delete comment without confirmation
        budjira comment delete PROJ-123 10234 --force
    """
    try:
        # Resolve connection
        connection = get_active_connection(connection_name)
        jira_client = JiraClient.from_connection(connection)

        # Confirm deletion unless --force is used
        if not force:
            confirm = typer.confirm(f"Delete comment {comment_id} on {issue_key}?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Delete comment
        jira_client.comments.delete(issue_key, comment_id)
        console.print(f"[green]✓[/green] Comment {comment_id} deleted from {issue_key}")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error deleting comment")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


def _format_date(created: str | None) -> str:
    """Format a Jira timestamp for table display (date part only)."""
    return created[:10] if created else ""


def _first_line(body: str | None, max_length: int) -> str:
    """Return the first line of a comment body, truncated to max_length."""
    if not body:
        return ""
    first = body.splitlines()[0] if body.splitlines() else ""
    if len(first) > max_length:
        return first[:max_length] + "..."
    return first
