"""Create new Jira issues."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from budjira.config.metadata_cache import MetadataCache
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
    from budjira.models.custom_field import CustomFieldConfig
    from budjira.models.issue import Issue
    from budjira.models.project_metadata import ProjectMetadata

app = typer.Typer(
    name="create",
    help="Create new Jira issues",
    no_args_is_help=True,
)
console = Console()


def _load_project_metadata(connection: Connection) -> ProjectMetadata | None:
    """Load cached project metadata for a connection.

    Args:
        connection: Active Jira connection

    Returns:
        ProjectMetadata if available, None otherwise
    """
    try:
        settings = get_settings()
        cache = MetadataCache(settings.cache_dir)
        return cache.load(connection)
    except Exception:
        return None


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


def _get_issue_type_input(interactive: bool, issue_type: str | None, metadata: ProjectMetadata | None = None) -> str:
    """Get issue type from user input.

    Uses discovered project metadata if available, otherwise falls back
    to hardcoded IssueType enum values.

    Args:
        interactive: Whether to prompt interactively
        issue_type: Pre-provided issue type value
        metadata: Optional cached project metadata

    Returns:
        Issue type
    """
    if interactive and issue_type is None:
        if metadata and metadata.issue_types:
            type_names = metadata.get_issue_type_names()
            issue_types_str = ", ".join(type_names)
        else:
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
        if template is not None and Confirm.ask(f"Use DoR template for {issue_type}?", default=True):
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


def _get_priority_input(interactive: bool, priority: str | None, metadata: ProjectMetadata | None = None) -> str | None:
    """Get priority from user input.

    Uses discovered project metadata if available, otherwise falls back
    to hardcoded Priority enum values.

    Args:
        interactive: Whether to prompt interactively
        priority: Pre-provided priority value
        metadata: Optional cached project metadata

    Returns:
        Priority or None
    """
    if interactive and priority is None and Confirm.ask("Set priority?", default=False):
        if metadata and metadata.priorities:
            priorities_str = ", ".join(metadata.priorities)
            default = metadata.priorities[0] if metadata.priorities else "Medium"
        else:
            priorities_str = ", ".join([p.value for p in Priority])
            default = "Medium"
        return str(Prompt.ask(f"Priority ({priorities_str})", default=default))
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


def _is_subtask_type(issue_type: str, metadata: ProjectMetadata | None) -> bool:
    """Determine whether an issue type is a sub-task type.

    Prefers the authoritative ``subtask`` flag from project metadata, which is
    robust to naming differences between instances (e.g. 'Subtask' vs
    'Sub-task'). Falls back to a normalized name heuristic when metadata is
    unavailable.

    Args:
        issue_type: Issue type name as entered by the user
        metadata: Cached project metadata, if available

    Returns:
        True if the issue type represents a sub-task
    """
    if metadata:
        for it in metadata.issue_types:
            if it.name.lower() == issue_type.lower():
                return it.subtask
    return issue_type.lower().replace("-", "").replace(" ", "") == "subtask"


def _get_parent_input(
    interactive: bool,
    parent: str | None,
    issue_type: str,
    metadata: ProjectMetadata | None,
) -> str | None:
    """Prompt for a parent issue key when creating a sub-task without one.

    Args:
        interactive: Whether to prompt interactively
        parent: Pre-provided parent issue key
        issue_type: Resolved issue type
        metadata: Cached project metadata, if available

    Returns:
        Parent issue key or None
    """
    if parent is None and interactive and _is_subtask_type(issue_type, metadata):
        return str(Prompt.ask("Parent issue key (required for sub-tasks, e.g., PROJ-123)"))
    return parent


def _parse_custom_fields(
    custom_args: list[str] | None,
    custom_field_configs: dict[str, CustomFieldConfig],
) -> dict[str, str]:
    """Parse custom field arguments from CLI.

    Args:
        custom_args: List of 'name=value' strings from --custom flags
        custom_field_configs: Custom field configurations from connection

    Returns:
        Dictionary mapping field names to their raw values

    Raises:
        typer.Exit: If parsing fails or field name is unknown
    """
    if not custom_args:
        return {}

    parsed: dict[str, str] = {}
    for arg in custom_args:
        if "=" not in arg:
            console.print(f"[red]Invalid custom field format:[/red] '{arg}'", style="red")
            console.print("[dim]Expected format: name=value (e.g., --custom affected_system=Infrastructure)[/dim]")
            raise typer.Exit(1)

        name, value = arg.split("=", 1)
        name = name.strip()
        value = value.strip()

        if not name:
            console.print("[red]Custom field name cannot be empty[/red]", style="red")
            raise typer.Exit(1)

        # Check if custom fields are configured
        if not custom_field_configs:
            console.print(f"[red]Unknown custom field:[/red] '{name}'", style="red")
            console.print("[dim]No custom fields configured for this connection[/dim]")
            raise typer.Exit(1)

        if name not in custom_field_configs:
            available = ", ".join(custom_field_configs.keys())
            console.print(f"[red]Unknown custom field:[/red] '{name}'", style="red")
            console.print(f"[dim]Available fields: {available}[/dim]")
            raise typer.Exit(1)

        parsed[name] = value

    return parsed


def _validate_custom_field_values(
    values: dict[str, str],
    configs: dict[str, CustomFieldConfig],
) -> None:
    """Validate custom field values against their configurations.

    Args:
        values: Dictionary mapping field names to their raw values
        configs: Custom field configurations

    Raises:
        typer.Exit: If validation fails
    """
    for name, value in values.items():
        if name not in configs:
            continue

        config = configs[name]
        is_valid, error_msg = config.validate_value(value)
        if not is_valid:
            label = config.label or name
            console.print(f"[red]Invalid value for '{label}':[/red] {error_msg}", style="red")
            raise typer.Exit(1)


def _get_custom_fields_input(
    interactive: bool,
    custom_values: dict[str, str],
    configs: dict[str, CustomFieldConfig],
) -> dict[str, str]:
    """Get custom field values interactively for required fields.

    Args:
        interactive: Whether to prompt interactively
        custom_values: Already provided custom field values
        configs: Custom field configurations

    Returns:
        Updated dictionary with all required fields filled
    """
    if not interactive or not configs:
        return custom_values

    result = dict(custom_values)

    for name, config in configs.items():
        # Skip if already provided
        if name in result:
            continue

        # Skip if not required and has no default
        if not config.required and config.default is None:
            continue

        label = config.label or name

        # For required fields without value, prompt
        if config.required:
            if config.options:
                options_str = ", ".join(config.options)
                prompt_text = f"{label} ({options_str})"
            else:
                prompt_text = label

            default = config.default
            value = str(Prompt.ask(prompt_text, default=default or ""))

            if value:
                result[name] = value
            elif config.required:
                console.print(f"[red]'{label}' is required[/red]", style="red")
                raise typer.Exit(1)
        elif config.default is not None:
            # Optional field with default - use default
            result[name] = config.default

    return result


def _format_custom_fields_for_api(
    values: dict[str, str],
    configs: dict[str, CustomFieldConfig],
) -> dict[str, Any]:
    """Format custom field values for Jira API.

    Args:
        values: Dictionary mapping field names to their raw values
        configs: Custom field configurations

    Returns:
        Dictionary mapping Jira field IDs to formatted values
    """
    result: dict[str, Any] = {}

    for name, value in values.items():
        if name not in configs:
            continue

        config = configs[name]
        formatted_value = config.format_value(value)
        result[config.field_id] = formatted_value

    return result


def _check_required_custom_fields(
    values: dict[str, str],
    configs: dict[str, CustomFieldConfig],
) -> None:
    """Check that all required custom fields have values.

    Args:
        values: Dictionary mapping field names to their raw values
        configs: Custom field configurations

    Raises:
        typer.Exit: If required fields are missing
    """
    missing = []
    for name, config in configs.items():
        if config.required and name not in values:
            label = config.label or name
            missing.append(label)

    if missing:
        console.print(f"[red]Missing required custom field(s):[/red] {', '.join(missing)}", style="red")
        console.print("[dim]Use --custom name=value to provide values[/dim]")
        raise typer.Exit(1)


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


def _validate_parent(parent: str | None, issue_type: str, metadata: ProjectMetadata | None) -> None:
    """Validate that sub-task creation has a parent issue.

    Fails fast with an actionable message instead of letting Jira reject the
    request with the cryptic "parent issue key or id not specified" error.

    Args:
        parent: Parent issue key, if provided
        issue_type: Resolved issue type
        metadata: Cached project metadata, if available

    Raises:
        BudjiraError: If a sub-task is created without a parent
    """
    if not parent and _is_subtask_type(issue_type, metadata):
        raise BudjiraError(
            f"Issue type '{issue_type}' is a sub-task and requires a parent issue. "
            f"Provide it with --parent PROJ-123."
        )


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


def _prepare_parent_field(parent: str | None) -> dict[str, Any]:
    """Prepare the parent field for sub-task creation.

    Args:
        parent: Parent issue key (e.g., PROJ-123)

    Returns:
        Dictionary with the Jira parent field, or empty if no parent
    """
    return {"parent": {"key": parent}} if parent else {}


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
        help=f"Issue type (uses project metadata if available, otherwise: {', '.join([t.value for t in IssueType])})",
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
        help="Priority level (uses project metadata if available, otherwise: "
        f"{', '.join([p.value for p in Priority])})",
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
    parent: str = typer.Option(
        None,
        "--parent",
        help="Parent issue key for sub-tasks (e.g., PROJ-123)",
    ),
    custom: list[str] = typer.Option(
        None,
        "--custom",
        help="Custom field value as name=value (can be specified multiple times)",
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

        # Create a sub-task under a parent issue
        budjira create issue "Implement login form" --type Subtask --parent PROJ-123 --no-interactive

        # Create multiple stories for same epic
        budjira create issue "Story 1" --type Story --epic PROJ-100 --no-interactive
        budjira create issue "Story 2" --type Story --epic PROJ-100 --no-interactive

        # With custom fields (configured in connection)
        budjira create issue "Fix bug" --type Bug --custom affected_system=Infrastructure --no-interactive

        # Multiple custom fields
        budjira create issue "New feature" --type Story --custom env=Production --custom component=API
    """
    try:
        # Setup
        settings = get_settings()
        active_connection = get_active_connection(connection)
        project_key = project or active_connection.project_key
        custom_field_configs = active_connection.custom_fields

        # Load project metadata for discovered types/priorities
        project_metadata = _load_project_metadata(active_connection)

        # Gather inputs (interactive or command-line provided)
        summary = _get_summary_input(interactive, summary)
        issue_type = _get_issue_type_input(interactive, issue_type, project_metadata)
        description = _get_description_input(interactive, description, issue_type, skip_dor, settings)  # type: ignore[assignment]
        priority = _get_priority_input(interactive, priority, project_metadata)  # type: ignore[assignment]
        assignee = _get_assignee_input(interactive, assignee)  # type: ignore[assignment]
        labels = _get_labels_input(interactive, labels)
        epic = _get_epic_input(interactive, epic)  # type: ignore[assignment]
        parent = _get_parent_input(interactive, parent, issue_type, project_metadata)  # type: ignore[assignment]

        # Handle custom fields
        custom_values = _parse_custom_fields(custom, custom_field_configs)
        _validate_custom_field_values(custom_values, custom_field_configs)
        custom_values = _get_custom_fields_input(interactive, custom_values, custom_field_configs)
        if not interactive:
            _check_required_custom_fields(custom_values, custom_field_configs)

        # Validate
        _validate_required_fields(summary, issue_type)
        _validate_parent(parent, issue_type, project_metadata)
        _validate_dor(description, issue_type, skip_dor, settings)

        # Create issue
        client = JiraClient.from_connection(active_connection)
        console.print(f"\n[dim]Creating {issue_type} in project {project_key}...[/dim]")

        extra_fields = _prepare_time_tracking(original_estimate, remaining_estimate)

        # Add parent field for sub-tasks
        extra_fields.update(_prepare_parent_field(parent))

        # Add custom fields to extra_fields
        if custom_values and custom_field_configs:
            custom_api_fields = _format_custom_fields_for_api(custom_values, custom_field_configs)
            extra_fields.update(custom_api_fields)

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
