"""CLI commands for updating Jira issues."""

import sys
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.models.transition import Transition
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError, InvalidIssueError, PermissionError
from budjira.utils.time_parser import parse_time_string
from budjira.utils.transition_fields import (
    attribute_validator_error,
    format_field_requirements,
    missing_required_fields,
    parse_field_args,
    resolve_fields,
)

app = typer.Typer(
    name="issue",
    help="Update and manage existing Jira issues",
    no_args_is_help=True,
)

console = Console()


@app.command("delete")
def delete_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
    delete_subtasks: Annotated[
        bool, typer.Option("--delete-subtasks", help="Also delete subtasks of the issue")
    ] = False,
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Delete a Jira issue.

    Permanently removes an issue from Jira. This action cannot be undone.

    Examples:

        # Delete issue with confirmation
        budjira issue delete PROJ-123

        # Delete without confirmation
        budjira issue delete PROJ-123 --force

        # Delete issue and its subtasks
        budjira issue delete PROJ-123 --delete-subtasks
    """
    try:
        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]")

        # Create client
        client = JiraClient.from_connection(conn)

        # Fetch issue summary for confirmation
        try:
            issue = client.issues.get(issue_key, fields=["summary"])
            issue_summary = issue.summary
        except InvalidIssueError as e:
            console.print(f"[red]Error:[/red] Issue '{issue_key}' not found.")
            raise typer.Exit(1) from e

        # Confirm deletion unless --force is used
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete {issue_key} '{issue_summary}'?")
            if not confirm:
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Delete issue
        client.issues.delete(issue_key, delete_subtasks=delete_subtasks)
        console.print(f"[green]✓[/green] Deleted issue {issue_key} '{issue_summary}'")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


def _validator_messages(error: Exception) -> list[str]:
    """Extract errorMessages from a Jira error whose 'errors' object is empty.

    A populated 'errors' object means Jira already named the field, so there is
    nothing to attribute.

    Args:
        error: Exception raised while transitioning

    Returns:
        The anonymous validator messages, empty if this is not that case
    """
    # The service layer converts JIRAError into JiraAPIError and keeps only the
    # error text, so the response body survives solely in the __cause__ chain.
    # Walk it, otherwise attribution never fires outside of unit tests.
    current: BaseException | None = error
    while current is not None:
        response = getattr(current, "response", None)
        if response is not None:
            try:
                body = response.json()
            except Exception:
                # A non-JSON body simply carries no attribution.
                body = None
            if isinstance(body, dict) and not body.get("errors"):
                return [str(m) for m in body.get("errorMessages") or []]
        current = current.__cause__
    return []


def _can_prompt() -> bool:
    """Whether prompting can actually succeed.

    budjira is frequently driven by agents and CI, where ``--no-interactive`` is
    easy to forget. Without a terminal attached a prompt would hang forever, so
    the absence of a TTY counts as non-interactive regardless of the flag.

    Returns:
        True if stdin is a terminal
    """
    return sys.stdin.isatty()


def _collect_transition_fields(
    client: JiraClient,
    issue_key: str,
    status: str,
    field_args: list[str] | None,
    interactive: bool,
    dry_run: bool,
) -> tuple[Transition, dict[str, Any]]:
    """Resolve screen field values for a transition, prompting when allowed.

    Args:
        client: Connected Jira client
        issue_key: Issue key
        status: Transition name requested with --status
        field_args: Raw --field arguments
        interactive: Whether prompting is permitted
        dry_run: Whether this is a dry run (never prompts)

    Returns:
        The matched transition and the resolved field values

    Raises:
        BudjiraError: If the transition is unknown or a required field is missing
    """
    transitions = client.transitions.get_transition_details(issue_key)
    matched = next((t for t in transitions if t.name.lower() == status.lower()), None)
    if matched is None:
        available = ", ".join(t.name for t in transitions) or "none"
        raise BudjiraError(f"Invalid transition '{status}' for {issue_key}. Available transitions: {available}")

    resolved = resolve_fields(parse_field_args(field_args), matched)

    missing = missing_required_fields(resolved, matched)
    if missing and not dry_run:
        if interactive and _can_prompt():
            for field_meta in missing:
                answer = typer.prompt(f"{field_meta.name} ({field_meta.field_id})")
                resolved.update(resolve_fields({field_meta.field_id: answer}, matched))
        else:
            raise BudjiraError(
                f"Transition '{matched.name}' requires field values that were not supplied:\n"
                f"{format_field_requirements(missing)}"
            )

    return matched, resolved


@app.command("update")
def update_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    status: Annotated[str | None, typer.Option("--status", "-s", help="Transition to status")] = None,
    field: Annotated[
        list[str] | None,
        typer.Option("--field", help="Transition screen field as key=value (repeatable)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show the transition and its fields without performing it")
    ] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive/--no-interactive", "-i/-n", help="Prompt for missing required fields")
    ] = True,
    assignee: Annotated[
        str | None, typer.Option("--assignee", "-a", help="Assign to user (username or 'currentUser()')")
    ] = None,
    priority: Annotated[str | None, typer.Option("--priority", "-p", help="Set priority")] = None,
    add_label: Annotated[list[str] | None, typer.Option("--add-label", help="Add label (repeatable)")] = None,
    remove_label: Annotated[list[str] | None, typer.Option("--remove-label", help="Remove label (repeatable)")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="Update summary")] = None,
    description: Annotated[str | None, typer.Option("--description", help="Update description")] = None,
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Link to epic (epic key)")] = None,
    original_estimate: Annotated[
        str | None, typer.Option("--original-estimate", help="Update original estimate (e.g., 2h, 30m)")
    ] = None,
    remaining_estimate: Annotated[
        str | None, typer.Option("--remaining-estimate", help="Update remaining estimate (e.g., 2h, 30m)")
    ] = None,
    log_work: Annotated[str | None, typer.Option("--log-work", help="Log work time (e.g., 2h, 30m)")] = None,
    work_comment: Annotated[
        str | None, typer.Option("--work-comment", help="Work log comment (requires --log-work)")
    ] = None,
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Update an existing Jira issue.

    Update status, assignee, priority, labels, summary, and description.
    Multiple updates can be performed in a single command.

    Examples:

        # Transition to In Progress and assign to current user
        budjira update issue PROJ-123 --status "In Progress" --assignee currentUser()

        # Update priority and add labels
        budjira update issue PROJ-123 --priority High --add-label urgent --add-label backend

        # Multiple updates at once
        budjira update issue PROJ-123 \\
            --status Done \\
            --priority Low \\
            --add-label completed
    """
    try:
        # Validate work_comment requires log_work
        if work_comment and not log_work:
            console.print("[red]Error: --work-comment requires --log-work[/red]")
            raise typer.Exit(1)

        # Check that at least one update option is provided
        if not any(
            [
                status,
                field,
                assignee is not None,
                priority,
                add_label,
                remove_label,
                summary,
                description,
                epic,
                original_estimate,
                remaining_estimate,
                log_work,
            ]
        ):
            console.print("[yellow]No updates specified. Use --help to see available options.[/yellow]")
            raise typer.Exit(1)

        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]")

        # Create client
        client = JiraClient.from_connection(conn)

        # Track changes for output
        changes: list[tuple[str, str]] = []

        # Screen fields have no meaning without a transition to resolve them against
        if field and not status:
            console.print("[red]Error:[/red] --field requires --status; screen fields belong to a transition.")
            raise typer.Exit(1)

        # Perform status transition first (if specified)
        if status:
            try:
                matched, resolved = _collect_transition_fields(client, issue_key, status, field, interactive, dry_run)

                if dry_run:
                    console.print(f"[cyan]Dry run:[/cyan] would transition {issue_key} via '{matched.name}'")
                    if matched.to_status:
                        console.print(f"  Target status: {matched.to_status}")
                    for field_id, value in resolved.items():
                        console.print(f"  {field_id} = {value}")
                    still_missing = missing_required_fields(resolved, matched)
                    if still_missing:
                        console.print("[yellow]Missing required fields:[/yellow]")
                        console.print(format_field_requirements(still_missing))
                    return

                try:
                    client.transitions.transition(issue_key, matched.name, fields=resolved or None)
                except Exception as transition_error:
                    messages = _validator_messages(transition_error)
                    culprit = attribute_validator_error(messages, matched) if messages else None
                    if culprit is None:
                        if not messages:
                            raise
                        # Forward Jira's own wording rather than naming a field we
                        # could not identify, but show what the screen offers.
                        console.print(f"[red]✗[/red] Transition '{matched.name}' was rejected: {' '.join(messages)}")
                        if matched.fields:
                            console.print("Screen fields on this transition:")
                            console.print(format_field_requirements(matched.fields))
                        raise typer.Exit(1) from transition_error

                    detail = f"'{culprit.name}' ({culprit.field_id})"
                    if not (interactive and _can_prompt()):
                        console.print(
                            f"[red]✗[/red] Transition '{matched.name}' was rejected by a workflow validator. "
                            f"The message refers to field {detail}. Supply it with:\n"
                            f"{format_field_requirements([culprit])}"
                        )
                        raise typer.Exit(1) from transition_error

                    console.print(f"[yellow]![/yellow] A workflow validator requires field {detail}.")
                    answer = typer.prompt(f"{culprit.name} ({culprit.field_id})")
                    resolved.update(resolve_fields({culprit.field_id: answer}, matched))
                    client.transitions.transition(issue_key, matched.name, fields=resolved)

                changes.append(("Status", f"→ {status}"))
            except BudjiraError as e:
                console.print(f"[red]✗[/red] Status update failed: {e}")
                raise typer.Exit(1) from e

        # Perform field updates
        try:
            # Update basic fields
            if any([assignee is not None, priority, summary, description]):
                client.update_issue(
                    issue_key,
                    assignee=assignee,
                    priority=priority,
                    summary=summary,
                    description=description,
                )
                if assignee is not None:
                    changes.append(("Assignee", f"→ {assignee}"))
                if priority:
                    changes.append(("Priority", f"→ {priority}"))
                if summary:
                    changes.append(("Summary", "Updated"))
                if description:
                    changes.append(("Description", "Updated"))

            # Add labels
            if add_label:
                client.add_labels(issue_key, add_label)
                for label in add_label:
                    changes.append(("Label", f"+ {label}"))

            # Remove labels
            if remove_label:
                client.remove_labels(issue_key, remove_label)
                for label in remove_label:
                    changes.append(("Label", f"- {label}"))

            # Link to epic
            if epic:
                client.link_to_epic(issue_key, epic)
                changes.append(("Epic", f"→ {epic}"))

            # Update time tracking estimates
            if original_estimate or remaining_estimate:
                timetracking_fields = {}
                if original_estimate:
                    timetracking_fields["originalEstimate"] = original_estimate
                if remaining_estimate:
                    timetracking_fields["remainingEstimate"] = remaining_estimate

                client.update_issue(issue_key, fields={"timetracking": timetracking_fields})
                if original_estimate:
                    changes.append(("Original Estimate", f"→ {original_estimate}"))
                if remaining_estimate:
                    changes.append(("Remaining Estimate", f"→ {remaining_estimate}"))

            # Log work
            if log_work:
                time_spent_minutes = parse_time_string(log_work)
                client.add_worklog(
                    issue_key=issue_key,
                    time_spent_minutes=time_spent_minutes,
                    comment=work_comment,
                )
                changes.append(("Work Logged", log_work))
                if work_comment:
                    changes.append(("  Comment", work_comment))

        except BudjiraError as e:
            console.print(f"[red]✗[/red] Update failed: {e}")
            raise typer.Exit(1) from e

        # Display success message with changes
        console.print(f"\n[green]✓[/green] Updated {issue_key}")

        if changes:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Field", style="cyan")
            table.add_column("Change", style="")

            for field_name, change in changes:
                table.add_row(field_name, change)

            console.print(table)

        # Show issue URL
        issue_url = f"{conn.url}/browse/{issue_key}"
        console.print(f"\n[dim]View: {issue_url}[/dim]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("transitions")
def show_transitions(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Show available transitions for an issue.

    Displays all workflow transitions available from the issue's current status.

    Example:

        budjira update transitions PROJ-123
    """
    try:
        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        # Create client
        client = JiraClient.from_connection(conn)

        # Get transitions
        transitions = client.get_transitions(issue_key)

        if not transitions:
            console.print(f"[yellow]No transitions available for {issue_key}[/yellow]")
            return

        console.print(f"Available transitions for [cyan]{issue_key}[/cyan]:\n")

        table = Table(show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")

        for transition in transitions:
            table.add_row(transition["id"], transition["name"])

        console.print(table)

        console.print(f'\n[dim]Use: budjira update issue {issue_key} --status "<name>"[/dim]')

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("link")
def link_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue to link FROM")],
    relates_to: Annotated[list[str] | None, typer.Option("--relates-to", help="Link as 'relates to'")] = None,
    blocks: Annotated[list[str] | None, typer.Option("--blocks", help="Link as 'blocks'")] = None,
    is_blocked_by: Annotated[list[str] | None, typer.Option("--is-blocked-by", help="Link as 'is blocked by'")] = None,
    clones: Annotated[list[str] | None, typer.Option("--clones", help="Link as 'clones'")] = None,
    is_cloned_by: Annotated[list[str] | None, typer.Option("--is-cloned-by", help="Link as 'is cloned by'")] = None,
    duplicates: Annotated[list[str] | None, typer.Option("--duplicates", help="Link as 'duplicates'")] = None,
    is_duplicated_by: Annotated[
        list[str] | None, typer.Option("--is-duplicated-by", help="Link as 'is duplicated by'")
    ] = None,
    connection: Annotated[
        str | None, typer.Option("--connection", "-c", help="Connection name (overrides environment)")
    ] = None,
) -> None:
    """Link an issue to another issue.

    Create issue links between two issues. Multiple links can be created in a single command.

    Common link types:
    - Relates: Generic relationship
    - Blocks/Blocked By: Dependency relationship
    - Clones/Cloned By: Issue duplication
    - Duplicates/Duplicated By: Issue tracking

    Examples:

        # Link issue to related issues
        budjira issue link PROJ-123 --relates-to PROJ-456 --relates-to PROJ-789

        # Create blocking relationship
        budjira issue link PROJ-123 --blocks PROJ-456

        # Multiple link types
        budjira issue link PROJ-100 --relates-to PROJ-200 --blocks PROJ-300
    """
    try:
        # Get active connection
        conn = get_active_connection(connection)
        console.print(f"[dim]Using connection: {conn.name}[/dim]\n")

        # Create client
        client = JiraClient.from_connection(conn)

        # Collect all link operations
        link_operations = []

        if relates_to:
            for target in relates_to:
                link_operations.append(("Relates", issue_key, target))

        if blocks:
            for target in blocks:
                link_operations.append(("Blocks", issue_key, target))

        if is_blocked_by:
            for target in is_blocked_by:
                link_operations.append(("Blocks", target, issue_key))

        if clones:
            for target in clones:
                link_operations.append(("Clones", issue_key, target))

        if is_cloned_by:
            for target in is_cloned_by:
                link_operations.append(("Clones", target, issue_key))

        if duplicates:
            for target in duplicates:
                link_operations.append(("Duplicate", issue_key, target))

        if is_duplicated_by:
            for target in is_duplicated_by:
                link_operations.append(("Duplicate", target, issue_key))

        if not link_operations:
            console.print("[yellow]No link operations specified. Use --help for usage.[/yellow]")
            raise typer.Exit(1)

        # Validate link types first
        try:
            available_types = client.links.get_link_types()
        except Exception as e:
            console.print(f"[red]Failed to fetch available link types:[/red] {e}")
            raise typer.Exit(1) from e

        # Execute link operations
        success_count = 0
        failed_count = 0

        for link_type, outward_issue, inward_issue in link_operations:
            try:
                client.links.create_link(link_type, outward_issue, inward_issue)
                console.print(f"[green]✓[/green] Linked {outward_issue} → {inward_issue} ({link_type})")
                success_count += 1
            except ValueError as e:
                # Invalid link type
                console.print(f"[red]✗[/red] {e}")
                console.print(f"[dim]Available types: {', '.join(available_types.keys())}[/dim]")
                failed_count += 1
            except InvalidIssueError as e:
                console.print(f"[red]✗[/red] {e}")
                failed_count += 1
            except PermissionError as e:
                console.print(f"[red]✗[/red] {e}")
                failed_count += 1
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to create link: {e}")
                failed_count += 1

        # Summary
        console.print()
        if success_count > 0:
            console.print(f"[green]Successfully created {success_count} link(s)[/green]")
        if failed_count > 0:
            console.print(f"[red]Failed to create {failed_count} link(s)[/red]")
            raise typer.Exit(1)

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
