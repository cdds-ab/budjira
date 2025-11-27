"""Create new Jira issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from budjira.config.settings import Settings
    from budjira.models.connection import Connection
    from budjira.models.issue import Issue

app = typer.Typer(
    name="create",
    help="Create new Jira issues",
    no_args_is_help=True,
)
console = Console()


def _get_summary_input(interactive: bool, summary: str | None) -> str:
    """Get issue summary from user input.

    Args:
        interactive: Whether to prompt interactively
        summary: Pre-provided summary value

    Returns:
        Issue summary
    """
    if interactive and summary is None:
        return str(Prompt.ask("Issue summary"))
    return summary or ""


def _get_issue_type_input(interactive: bool, issue_type: str | None) -> str:
    """Get issue type from user input.

    Args:
        interactive: Whether to prompt interactively
        issue_type: Pre-provided issue type value

    Returns:
        Issue type
    """
    if interactive and issue_type is None:
        issue_types_str = ", ".join([t.value for t in IssueType])
        return str(Prompt.ask(f"Issue type ({issue_types_str})", default="Task"))
    return issue_type or ""


def _get_description_input(
    interactive: bool,
    description: str | None,
    issue_type: str | None,
    skip_dor: bool,
    settings: Settings,
) -> str | None:
    """Get issue description from user input, potentially using DoR template.

    Args:
        interactive: Whether to prompt interactively
        description: Pre-provided description value
        issue_type: Issue type for DoR template lookup
        skip_dor: Whether to skip DoR template
        settings: Application settings

    Returns:
        Issue description or None
    """
    if not interactive or description is not None:
        return description

    # Check if DoR is enabled and template exists for this type
    use_dor = (
        not skip_dor
        and settings.global_config.enforce_dor
        and issue_type is not None
        and settings.dor_templates.get_template(issue_type) is not None
    )

    if use_dor:
        template = settings.dor_templates.get_template(issue_type or "")
        if template and Confirm.ask(f"Use DoR template for {issue_type}?", default=True):
            console.print(f"\n[dim]Opening editor with DoR template for {issue_type}...[/dim]")
            return open_editor(
                initial_content=template.template_text,
                file_extension=".md",
                editor=settings.global_config.editor,
            )
        elif Confirm.ask("Add description?", default=False):
            return str(Prompt.ask("Description"))
    elif Confirm.ask("Add description?", default=False):
        return str(Prompt.ask("Description"))

    return None


def _get_priority_input(interactive: bool, priority: str | None) -> str | None:
    """Get priority from user input.

    Args:
        interactive: Whether to prompt interactively
        priority: Pre-provided priority value

    Returns:
        Priority or None
    """
    if interactive and priority is None and Confirm.ask("Set priority?", default=False):
        priorities_str = ", ".join([p.value for p in Priority])
        return str(Prompt.ask(f"Priority ({priorities_str})", default="Medium"))
    return priority


def _get_assignee_input(interactive: bool, assignee: str | None) -> str | None:
    """Get assignee from user input.

    Args:
        interactive: Whether to prompt interactively
        assignee: Pre-provided assignee value

    Returns:
        Assignee username or None
    """
    if interactive and assignee is None and Confirm.ask("Assign to someone?", default=False):
        return str(Prompt.ask("Assignee username"))
    return assignee


def _get_labels_input(interactive: bool, labels: list[str] | None) -> list[str]:
    """Get labels from user input.

    Args:
        interactive: Whether to prompt interactively
        labels: Pre-provided labels list

    Returns:
        List of labels
    """
    if interactive and not labels and Confirm.ask("Add labels?", default=False):
        labels_input = Prompt.ask("Labels (comma-separated)")
        return [label.strip() for label in labels_input.split(",") if label.strip()]
    return labels or []


def _get_epic_input(interactive: bool, epic: str | None) -> str | None:
    """Get epic key from user input.

    Args:
        interactive: Whether to prompt interactively
        epic: Pre-provided epic key

    Returns:
        Epic key or None
    """
    if interactive and epic is None and Confirm.ask("Link to an epic?", default=False):
        return str(Prompt.ask("Epic key (e.g., PROJ-100)"))
    return epic


def _validate_required_fields(summary: str, issue_type: str) -> None:
    """Validate that required fields are provided.

    Args:
        summary: Issue summary
        issue_type: Issue type

    Raises:
        typer.Exit: If validation fails
    """
    if not summary:
        console.print("[red]✗[/red] Summary is required", style="red")
        raise typer.Exit(1)

    if not issue_type:
        console.print("[red]✗[/red] Issue type is required", style="red")
        raise typer.Exit(1)


def _validate_dor(description: str | None, issue_type: str, skip_dor: bool, settings: Settings) -> None:
    """Validate description against DoR template if enabled.

    Args:
        description: Issue description
        issue_type: Issue type
        skip_dor: Whether to skip DoR validation
        settings: Application settings

    Raises:
        typer.Exit: If validation fails in strict mode
    """
    if not skip_dor and settings.global_config.enforce_dor and description:
        template = settings.dor_templates.get_template(issue_type)
        if template:
            validation_result = validate_description(description, template)

            if validation_result.has_errors or validation_result.has_warnings:
                console.print()
                console.print(format_validation_result(validation_result))
                console.print()

                validation_level = settings.global_config.dor_validation_level
                if validation_level == "strict" and validation_result.has_errors:
                    console.print("[red]DoR validation failed in strict mode. Issue creation blocked.[/red]")
                    console.print("[dim]Use --skip-dor to bypass validation[/dim]")
                    raise typer.Exit(1)
                elif validation_level == "warn":
                    if not Confirm.ask("Continue anyway?", default=True):
                        raise typer.Exit(0)


def _prepare_time_tracking(original_estimate: str | None, remaining_estimate: str | None) -> dict[str, Any]:
    """Prepare time tracking fields for issue creation.

    Args:
        original_estimate: Original time estimate
        remaining_estimate: Remaining time estimate

    Returns:
        Dictionary with time tracking fields
    """
    extra_fields: dict[str, Any] = {}
    if original_estimate or remaining_estimate:
        timetracking: dict[str, str] = {}
        if original_estimate:
            timetracking["originalEstimate"] = original_estimate
        if remaining_estimate:
            timetracking["remainingEstimate"] = remaining_estimate
        extra_fields["timetracking"] = timetracking
    return extra_fields


def _link_to_epic_if_specified(client: JiraClient, issue_key: str, epic: str | None) -> str | None:
    """Link issue to epic if epic key is provided.

    Args:
        client: Jira client
        issue_key: Created issue key
        epic: Epic key to link to

    Returns:
        Epic name if successful, None otherwise
    """
    if not epic:
        return None

    try:
        console.print(f"[dim]Linking to epic {epic}...[/dim]")
        client.link_to_epic(issue_key, epic)

        # Fetch epic name for display
        epic_issue = client.get_issue(epic)
        epic_name = epic_issue.summary
        console.print(f"[green]✓[/green] Linked to epic: {epic} ({epic_name})", style="green")
        return epic_name
    except BudjiraError as e:
        console.print(f"[yellow]⚠[/yellow] Warning: Failed to link to epic {epic}: {e}", style="yellow")
        console.print("[dim]Issue was created successfully but epic link failed[/dim]")
        return None


def _display_created_issue(
    created_issue: Issue, active_connection: Connection, epic: str | None, epic_name: str | None
) -> None:
    """Display created issue details in a formatted table.

    Args:
        created_issue: Created issue object
        active_connection: Active Jira connection
        epic: Epic key if linked
        epic_name: Epic name if linked
    """
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

    if epic and epic_name:
        table.add_row("Epic", f"{epic} ({epic_name})")

    console.print(table)

    # Show Jira URL
    base_url = str(active_connection.url).rstrip("/")
    issue_url = f"{base_url}/browse/{created_issue.key}"
    console.print(f"\n[dim]View in Jira: {issue_url}[/dim]")


@app.command()
def issue(
    summary: str | None = typer.Argument(None, help="Issue summary/title"),
    issue_type: str | None = typer.Option(
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
    epic: str = typer.Option(
        None,
        "--epic",
        "-e",
        help="Epic key to link this issue to (e.g., PROJ-100)",
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

        # Link to epic during creation
        budjira create issue "User authentication" --type Story --epic PROJ-100

        # Create multiple stories for same epic
        budjira create issue "Story 1" --type Story --epic PROJ-100 --no-interactive
        budjira create issue "Story 2" --type Story --epic PROJ-100 --no-interactive
    """
    try:
        # Setup
        settings = get_settings()
        active_connection = get_active_connection(connection)
        project_key = project or active_connection.project_key

        # Gather inputs (interactive or command-line provided)
        summary = _get_summary_input(interactive, summary)
        issue_type = _get_issue_type_input(interactive, issue_type)
        description = _get_description_input(interactive, description, issue_type, skip_dor, settings)  # type: ignore[assignment]
        priority = _get_priority_input(interactive, priority)  # type: ignore[assignment]
        assignee = _get_assignee_input(interactive, assignee)  # type: ignore[assignment]
        labels = _get_labels_input(interactive, labels)
        epic = _get_epic_input(interactive, epic)  # type: ignore[assignment]

        # Validate
        _validate_required_fields(summary, issue_type)
        _validate_dor(description, issue_type, skip_dor, settings)

        # Create issue
        client = JiraClient.from_connection(active_connection)
        console.print(f"\n[dim]Creating {issue_type} in project {project_key}...[/dim]")

        extra_fields = _prepare_time_tracking(original_estimate, remaining_estimate)
        created_issue = client.create_issue(
            project_key=project_key,
            summary=summary,
            issue_type=issue_type,
            description=description,
            priority=priority,
            assignee=assignee,
            labels=labels,
            **extra_fields,
        )

        # Link to epic if specified
        epic_name = _link_to_epic_if_specified(client, created_issue.key, epic)

        # Display result
        _display_created_issue(created_issue, active_connection, epic, epic_name)

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}", style="red")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
