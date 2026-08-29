"""Attach command for uploading files to issues."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    ConnectionError,
    InvalidIssueError,
    PermissionError,
    ValidationError,
)
from budjira.utils.formatter import OutputFormatter

console = Console()


def _format_size(size: int) -> str:
    """Format a byte count as a human-readable size (e.g., '12.3 KB')."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def attach_files(
    ctx: typer.Context,
    issue_key: Annotated[
        str,
        typer.Argument(help="Issue key (e.g., PROJ-123)"),
    ],
    files: Annotated[
        list[str],
        typer.Argument(help="File(s) to attach (paths, one or more)"),
    ],
    connection_name: Annotated[
        str | None,
        typer.Option(
            "--connection",
            help="Connection to use (overrides default)",
            envvar="BUDJIRA_CONNECTION",
        ),
    ] = None,
) -> None:
    """Attach one or more files to an issue.

    Upload files as issue attachments. Reference them from a comment with
    'budjira comment add --attach', or embed images inline with '--embed'.

    Examples:

        # Attach a single file
        budjira attach PROJ-123 chart.png

        # Attach several files at once
        budjira attach PROJ-123 chart.png report.pdf

        # JSON output for scripting
        budjira -f json attach PROJ-123 chart.png
    """
    output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

    try:
        connection = get_active_connection(connection_name)
        jira_client = JiraClient.from_connection(connection)

        uploaded = []
        for file in files:
            result = jira_client.attachments.add(issue_key, Path(file))
            uploaded.append(result)
            if not OutputFormatter.is_json_format(output_format):
                console.print(f"✅ [green]Attached {result['filename']} ({_format_size(result['size'])})[/green]")

        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json({"issue": issue_key, "attachments": uploaded})

    except ConnectionError as e:
        console.print(f"[red]Connection Error:[/red] {e}")
        raise typer.Exit(1) from e
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error:[/red] {e}")
        raise typer.Exit(1) from e
    except InvalidIssueError as e:
        console.print(f"[red]Invalid Issue:[/red] {e}")
        raise typer.Exit(1) from e
    except PermissionError as e:
        console.print(f"[red]Permission Denied:[/red] {e}")
        raise typer.Exit(1) from e
    except ValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1) from e
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
