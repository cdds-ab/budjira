"""CLI commands for updating Jira issues."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError
from budjira.utils.time_parser import parse_time_string

app = typer.Typer(
    name="issue",
    help="Update and manage existing Jira issues",
    no_args_is_help=True,
)

console = Console()


@app.command("update")
def update_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key (e.g., PROJ-123)")],
    status: Annotated[str | None, typer.Option("--status", "-s", help="Transition to status")] = None,
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

        # Perform status transition first (if specified)
        if status:
            try:
                client.transition_issue(issue_key, status)
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

            for field, change in changes:
                table.add_row(field, change)

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
