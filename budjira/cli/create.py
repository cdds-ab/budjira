"""Create new Jira issues."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from budjira.config.settings import get_settings
from budjira.core.jira_client import JiraClient
from budjira.models.issue import IssueType, Priority
from budjira.utils.connection import get_active_connection
from budjira.utils.dor_validator import format_validation_result, validate_description
from budjira.utils.editor import open_editor
from budjira.utils.errors import BudjiraError

app = typer.Typer(
    name="create",
    help="Create new Jira issues",
    no_args_is_help=True,
)
console = Console()


@app.command()
def issue(
    summary: str = typer.Argument(None, help="Issue summary/title"),
    issue_type: str = typer.Option(
        None,
        "--type",
        "-t",
        help=f"Issue type ({', '.join([t.value for t in IssueType])})",
    ),
    description: str = typer.Option(
        None,
        "--description",
        "-d",
        help="Issue description",
    ),
    project: str = typer.Option(
        None,
        "--project",
        "-p",
        help="Project key (uses connection default if not specified)",
    ),
    priority: str = typer.Option(
        None,
        "--priority",
        help=f"Priority level ({', '.join([p.value for p in Priority])})",
    ),
    assignee: str = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Assignee username",
    ),
    labels: list[str] = typer.Option(
        None,
        "--label",
        "-l",
        help="Labels (can be specified multiple times)",
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        "-i/-n",
        help="Interactive mode with prompts",
    ),
    connection: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides BUDJIRA_CONNECTION env var)",
    ),
    skip_dor: bool = typer.Option(
        False,
        "--skip-dor",
        help="Skip Definition of Ready template and validation",
    ),
    original_estimate: str = typer.Option(
        None,
        "--original-estimate",
        help="Original time estimate (e.g., 2h, 30m, 2h30m)",
    ),
    remaining_estimate: str = typer.Option(
        None,
        "--remaining-estimate",
        help="Remaining time estimate (e.g., 2h, 30m, 2h30m)",
    ),
) -> None:
    """Create a new Jira issue.

    You can provide all details via command line options, or use interactive mode
    to be prompted for required fields.

    Examples:

        # Interactive mode (default)
        budjira create issue "Fix login bug"

        # Non-interactive with all details
        budjira create issue "Fix login bug" --type Bug --priority High --no-interactive

        # With description and labels
        budjira create issue "Add feature" --type Story --description "Detailed desc" --label feature --label frontend
    """
    try:
        # Get settings for DoR templates
        settings = get_settings()

        # Get active connection (from --connection, env var, or config)
        active_connection = get_active_connection(connection)

        # Use provided project or connection default
        project_key = project or active_connection.project_key

        # Interactive prompts for missing required fields
        if interactive:
            if summary is None:
                summary = Prompt.ask("Issue summary")

            if issue_type is None:
                issue_types_str = ", ".join([t.value for t in IssueType])
                issue_type = Prompt.ask(
                    f"Issue type ({issue_types_str})",
                    default="Task",
                )

            # Handle description with DoR template if applicable
            if description is None:
                # Check if DoR is enabled and template exists for this type
                use_dor = (
                    not skip_dor
                    and settings.global_config.enforce_dor
                    and issue_type is not None
                    and settings.dor_templates.get_template(issue_type) is not None
                )

                if use_dor:
                    template = settings.dor_templates.get_template(issue_type)
                    if Confirm.ask(f"Use DoR template for {issue_type}?", default=True):
                        console.print(f"\n[dim]Opening editor with DoR template for {issue_type}...[/dim]")
                        description = open_editor(
                            initial_content=template.template_text,
                            file_extension=".md",
                            editor=settings.global_config.editor,
                        )
                    elif Confirm.ask("Add description?", default=False):
                        description = Prompt.ask("Description")
                elif Confirm.ask("Add description?", default=False):
                    description = Prompt.ask("Description")

            if priority is None and Confirm.ask("Set priority?", default=False):
                priorities_str = ", ".join([p.value for p in Priority])
                priority = Prompt.ask(f"Priority ({priorities_str})", default="Medium")

            if assignee is None and Confirm.ask("Assign to someone?", default=False):
                assignee = Prompt.ask("Assignee username")

            if not labels and Confirm.ask("Add labels?", default=False):
                labels_input = Prompt.ask("Labels (comma-separated)")
                labels = [label.strip() for label in labels_input.split(",") if label.strip()]

        # Validate required fields
        if not summary:
            console.print("[red]✗[/red] Summary is required", style="red")
            raise typer.Exit(1)

        if not issue_type:
            console.print("[red]✗[/red] Issue type is required", style="red")
            raise typer.Exit(1)

        # Validate DoR if enabled and description provided
        if not skip_dor and settings.global_config.enforce_dor and description:
            template = settings.dor_templates.get_template(issue_type)
            if template:
                validation_result = validate_description(description, template)

                # Get validation level from config
                validation_level = settings.global_config.dor_validation_level

                if validation_result.has_errors or validation_result.has_warnings:
                    console.print()
                    console.print(format_validation_result(validation_result))
                    console.print()

                    if validation_level == "strict" and validation_result.has_errors:
                        console.print("[red]DoR validation failed in strict mode. Issue creation blocked.[/red]")
                        console.print("[dim]Use --skip-dor to bypass validation[/dim]")
                        raise typer.Exit(1)
                    elif validation_level == "warn":
                        if not Confirm.ask("Continue anyway?", default=True):
                            raise typer.Exit(0)

        # Create client and issue
        client = JiraClient.from_connection(active_connection)

        console.print(
            f"\n[dim]Creating {issue_type} in project {project_key}...[/dim]",
        )

        # Prepare time tracking fields if provided
        extra_fields = {}
        if original_estimate or remaining_estimate:
            timetracking = {}
            if original_estimate:
                timetracking["originalEstimate"] = original_estimate
            if remaining_estimate:
                timetracking["remainingEstimate"] = remaining_estimate
            extra_fields["timetracking"] = timetracking

        created_issue = client.create_issue(
            project_key=project_key,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            assignee=assignee,
            labels=labels or [],
            **extra_fields,
        )

        # Display created issue
        console.print("\n[green]✓[/green] Issue created successfully!", style="green")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("Key", f"[bold]{created_issue.key}[/bold]")
        table.add_row("Type", created_issue.issue_type)
        table.add_row("Status", created_issue.status)
        table.add_row("Summary", created_issue.summary)

        if created_issue.description:
            desc_preview = (
                created_issue.description[:100] + "..."
                if len(created_issue.description) > 100
                else created_issue.description
            )
            table.add_row("Description", desc_preview)

        if created_issue.priority:
            table.add_row("Priority", created_issue.priority)

        if created_issue.assignee:
            table.add_row("Assignee", created_issue.assignee)

        if created_issue.labels:
            table.add_row("Labels", ", ".join(created_issue.labels))

        console.print(table)

        # Show Jira URL
        issue_url = f"{active_connection.url}/browse/{created_issue.key}"
        console.print(f"\n[dim]View in Jira: {issue_url}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}", style="red")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
