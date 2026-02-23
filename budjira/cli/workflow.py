"""CLI commands for workflow profile management."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from budjira.config.settings import get_settings
from budjira.models.workflow import (
    OverbookingPolicy,
    ProjectMapping,
    ShadowTicketStrategy,
    WorkflowProfile,
)
from budjira.services.workflow import WorkflowService, _format_seconds
from budjira.utils.errors import (
    BudjiraError,
    OverbookingError,
    ShadowTicketAmbiguousError,
    ShadowTicketNotFoundError,
    WorkflowConfigError,
)
from budjira.utils.formatter import OutputFormatter

app = typer.Typer(
    name="workflow",
    help="Manage cross-instance workflow profiles (planning + booking)",
    no_args_is_help=True,
)

console = Console()


@app.command("setup")
def workflow_setup() -> None:
    """Create a new workflow profile interactively.

    Guides you through setting up a workflow profile that connects a planning
    Jira instance with a booking Jira instance (Tempo-enabled).

    Example:
        budjira workflow setup
    """
    try:
        settings = get_settings()

        console.print("\n[cyan bold]Workflow Profile Setup[/cyan bold]\n")

        # Profile name
        name = typer.prompt("Profile name")

        # Check for existing profile
        if settings.workflows.find_by_name(name):
            console.print(f"[red]Profile '{name}' already exists.[/red]")
            raise typer.Exit(1)

        # List available connections
        connections = settings.connections
        if len(connections.connections) < 2:
            console.print(
                "[red]At least 2 connections are required for a workflow profile.[/red]\n"
                "Run 'budjira connect add' to create connections."
            )
            raise typer.Exit(1)

        console.print("\n[dim]Available connections:[/dim]")
        for conn in connections.connections:
            tempo_badge = " [green](Tempo)[/green]" if conn.tempo_enabled else ""
            console.print(f"  - {conn.name} ({conn.url}){tempo_badge}")

        # Planning connection
        planning_connection = typer.prompt("\nPlanning connection name")
        planning_conn = connections.find_by_name(planning_connection)
        if not planning_conn:
            console.print(f"[red]Connection '{planning_connection}' not found.[/red]")
            raise typer.Exit(1)

        # Booking connection
        booking_connection = typer.prompt("Booking connection name (must have Tempo enabled)")
        booking_conn = connections.find_by_name(booking_connection)
        if not booking_conn:
            console.print(f"[red]Connection '{booking_connection}' not found.[/red]")
            raise typer.Exit(1)

        if not booking_conn.tempo_enabled:
            console.print(
                f"[red]Connection '{booking_connection}' does not have Tempo enabled.[/red]\n"
                "Run 'budjira connect tempo-setup' to configure Tempo."
            )
            raise typer.Exit(1)

        if planning_connection == booking_connection:
            console.print("[red]Planning and booking connections must be different.[/red]")
            raise typer.Exit(1)

        # Project mappings
        console.print("\n[dim]Add project mappings (planning project -> booking project).[/dim]")
        project_mappings: list[ProjectMapping] = []

        while True:
            planning_project = typer.prompt("Planning project key (e.g., EK)")
            booking_project = typer.prompt("Booking project key (e.g., K)")
            project_mappings.append(
                ProjectMapping(
                    planning_project=planning_project.upper(),
                    booking_project=booking_project.upper(),
                )
            )
            if not typer.confirm("Add another mapping?", default=False):
                break

        # Shadow strategy
        console.print("\n[dim]Shadow ticket resolution strategy:[/dim]")
        console.print("  summary - Search by issue key in shadow ticket summary (default)")
        shadow_strategy_str = typer.prompt(
            "Strategy",
            default="summary",
            type=str,
        )
        shadow_strategy = ShadowTicketStrategy(shadow_strategy_str)

        # Overbooking policy
        console.print("\n[dim]Overbooking policy:[/dim]")
        console.print("  warn    - Show warning but continue (default)")
        console.print("  confirm - Ask for confirmation")
        console.print("  block   - Refuse to book")
        overbooking_str = typer.prompt(
            "Policy",
            default="warn",
            type=str,
        )
        overbooking_policy = OverbookingPolicy(overbooking_str)

        # Create profile
        profile = WorkflowProfile(
            name=name,
            planning_connection=planning_connection,
            booking_connection=booking_connection,
            project_mappings=project_mappings,
            shadow_strategy=shadow_strategy,
            overbooking_policy=overbooking_policy,
        )

        workflows = settings.workflows
        workflows.add(profile)
        settings.save_workflows(workflows)

        console.print(f"\n[green]Workflow profile '{name}' created successfully.[/green]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("list")
def workflow_list(
    ctx: typer.Context,
) -> None:
    """List all configured workflow profiles.

    Example:
        budjira workflow list
        budjira --format json workflow list
    """
    try:
        settings = get_settings()
        workflows = settings.workflows

        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        if not workflows.profiles:
            if OutputFormatter.is_json_format(output_format):
                OutputFormatter.output_json({"total": 0, "profiles": []})
            else:
                console.print("[yellow]No workflow profiles configured.[/yellow]")
                console.print("\nRun 'budjira workflow setup' to create one.")
            return

        if OutputFormatter.is_json_format(output_format):
            profile_dicts = []
            for profile in workflows.profiles:
                profile_dicts.append(
                    {
                        "name": profile.name,
                        "planning_connection": profile.planning_connection,
                        "booking_connection": profile.booking_connection,
                        "shadow_strategy": profile.shadow_strategy.value,
                        "overbooking_policy": profile.overbooking_policy.value,
                        "project_mappings": [
                            {
                                "planning_project": m.planning_project,
                                "booking_project": m.booking_project,
                            }
                            for m in profile.project_mappings
                        ],
                    }
                )
            OutputFormatter.output_json({"total": len(profile_dicts), "profiles": profile_dicts})
        else:
            console.print("\n[cyan bold]Workflow Profiles[/cyan bold]\n")

            table = Table(show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Planning", style="")
            table.add_column("Booking", style="")
            table.add_column("Mappings", style="yellow")
            table.add_column("Shadow", style="dim")
            table.add_column("Overbooking", style="dim")

            for profile in workflows.profiles:
                mappings = ", ".join(f"{m.planning_project}->{m.booking_project}" for m in profile.project_mappings)
                table.add_row(
                    profile.name,
                    profile.planning_connection,
                    profile.booking_connection,
                    mappings,
                    profile.shadow_strategy.value,
                    profile.overbooking_policy.value,
                )

            console.print(table)

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("show")
def workflow_show(
    ctx: typer.Context,
    profile_name: Annotated[
        str,
        typer.Argument(help="Workflow profile name"),
    ],
) -> None:
    """Show details of a workflow profile.

    Example:
        budjira workflow show ek-to-k
    """
    try:
        settings = get_settings()
        profile = settings.workflows.find_by_name(profile_name)

        if not profile:
            console.print(f"[yellow]Workflow profile '{profile_name}' not found.[/yellow]")
            available = ", ".join(p.name for p in settings.workflows.profiles)
            if available:
                console.print(f"\nAvailable profiles: {available}")
            raise typer.Exit(1)

        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json(
                {
                    "name": profile.name,
                    "planning_connection": profile.planning_connection,
                    "booking_connection": profile.booking_connection,
                    "shadow_strategy": profile.shadow_strategy.value,
                    "shadow_custom_field": profile.shadow_custom_field,
                    "overbooking_policy": profile.overbooking_policy.value,
                    "project_mappings": [
                        {
                            "planning_project": m.planning_project,
                            "booking_project": m.booking_project,
                        }
                        for m in profile.project_mappings
                    ],
                }
            )
        else:
            console.print(f"\n[cyan bold]Workflow Profile: {profile.name}[/cyan bold]\n")
            console.print(f"  Planning connection: {profile.planning_connection}")
            console.print(f"  Booking connection:  {profile.booking_connection}")
            console.print(f"  Shadow strategy:     {profile.shadow_strategy.value}")
            if profile.shadow_custom_field:
                console.print(f"  Shadow custom field: {profile.shadow_custom_field}")
            console.print(f"  Overbooking policy:  {profile.overbooking_policy.value}")

            if profile.project_mappings:
                console.print("\n  [bold]Project Mappings:[/bold]")
                for mapping in profile.project_mappings:
                    console.print(f"    {mapping.planning_project} -> {mapping.booking_project}")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("remove")
def workflow_remove(
    profile_name: Annotated[
        str,
        typer.Argument(help="Workflow profile name to remove"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Remove a workflow profile.

    Example:
        budjira workflow remove ek-to-k
        budjira workflow remove ek-to-k --force
    """
    try:
        settings = get_settings()
        workflows = settings.workflows

        profile = workflows.find_by_name(profile_name)
        if not profile:
            console.print(f"[yellow]Workflow profile '{profile_name}' not found.[/yellow]")
            raise typer.Exit(1)

        if not force and not typer.confirm(f"Remove workflow profile '{profile_name}'?"):
            console.print("[yellow]Removal cancelled.[/yellow]")
            return

        workflows.remove(profile_name)
        settings.save_workflows(workflows)

        console.print(f"[green]Workflow profile '{profile_name}' removed.[/green]")

    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("status")
def workflow_status(
    ctx: typer.Context,
    issue_key: Annotated[
        str,
        typer.Argument(help="Planning issue key (e.g., EK-123)"),
    ],
    profile_name: Annotated[
        str,
        typer.Option("--profile", "-p", help="Workflow profile to use"),
    ],
) -> None:
    """Show booking status for a planning issue.

    Displays estimate vs spent time across planning and booking instances.

    Example:
        budjira workflow status EK-123 --profile ek-to-k
    """
    try:
        service = WorkflowService.from_profile(profile_name)
        status = service.get_booking_status(issue_key)

        output_format = ctx.obj.get("format", "table") if ctx.obj else "table"

        if OutputFormatter.is_json_format(output_format):
            OutputFormatter.output_json(
                {
                    "planning_issue_key": status.planning_issue_key,
                    "planning_summary": status.planning_summary,
                    "booking_issue_key": status.booking_issue_key,
                    "estimate_seconds": status.estimate_seconds,
                    "spent_seconds": status.spent_seconds,
                    "remaining_seconds": status.remaining_seconds,
                    "is_overbooked": status.is_overbooked,
                    "overbooking_seconds": status.overbooking_seconds,
                }
            )
        else:
            console.print(f"\n[cyan bold]Booking Status: {issue_key}[/cyan bold]\n")
            console.print(
                f"  Planning:  {status.planning_issue_key} "
                f'"{status.planning_summary}" ({service.profile.planning_connection})'
            )

            if status.booking_issue_key:
                console.print(f"  Shadow:    {status.booking_issue_key} ({service.profile.booking_connection})")
            else:
                console.print("  Shadow:    [yellow]Not found[/yellow]")
                console.print(
                    "\n[dim]The shadow ticket may not have been synced yet. "
                    "Create it manually or wait for sync, then try again.[/dim]"
                )
                return

            # Estimate
            if status.estimate_seconds is not None:
                console.print(f"  Estimate:  {_format_seconds(status.estimate_seconds)}")
            else:
                console.print("  Estimate:  [dim]Not set[/dim]")

            # Spent
            console.print(f"  Spent:     {_format_seconds(status.spent_seconds)} (via Tempo)")

            # Remaining
            if status.remaining_seconds is not None:
                console.print(f"  Remaining: {_format_seconds(status.remaining_seconds)}")

            # Progress bar
            if status.estimate_seconds and status.estimate_seconds > 0:
                pct = min(status.spent_seconds / status.estimate_seconds * 100, 100)
                filled = int(pct / 10)
                empty = 10 - filled
                bar = "[green]" + "\u2588" * filled + "[/green]" + "\u2591" * empty
                pct_display = f"{status.spent_seconds / status.estimate_seconds * 100:.1f}%"

                if status.is_overbooked:
                    console.print(
                        f"  Progress:  {bar} [red]{pct_display} "
                        f"(+{_format_seconds(status.overbooking_seconds)} over)[/red]"
                    )
                else:
                    console.print(f"  Progress:  {bar} {pct_display}")

    except (ShadowTicketNotFoundError, ShadowTicketAmbiguousError, WorkflowConfigError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("book")
def workflow_book(
    issue_key: Annotated[
        str,
        typer.Argument(help="Planning issue key (e.g., EK-123)"),
    ],
    time_spent: Annotated[
        str,
        typer.Argument(help="Time to log (e.g., 2h, 30m, 2h30m)"),
    ],
    profile_name: Annotated[
        str,
        typer.Option("--profile", "-p", help="Workflow profile to use"),
    ],
    comment: Annotated[
        str | None,
        typer.Option("--comment", "-c", help="Worklog comment/description"),
    ] = None,
    started: Annotated[
        str | None,
        typer.Option(
            "--started",
            "-s",
            help="When work started (YYYY-MM-DD HH:MM, YYYY-MM-DD, today, yesterday)",
        ),
    ] = None,
) -> None:
    """Book time via workflow (resolve shadow ticket + log to Tempo).

    Automatically resolves the shadow ticket in the booking instance,
    checks for overbooking, and logs time via Tempo.

    Examples:
        budjira workflow book EK-123 2h --profile ek-to-k
        budjira workflow book EK-123 2h30m --profile ek-to-k --comment "Analysis"
        budjira workflow book EK-123 3h --profile ek-to-k --started yesterday
    """
    try:
        service = WorkflowService.from_profile(profile_name)
        service.book_time(
            planning_issue_key=issue_key,
            time_spent=time_spent,
            comment=comment,
            started=started,
        )

    except (ShadowTicketNotFoundError, ShadowTicketAmbiguousError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except OverbookingError as e:
        console.print(f"[red]Blocked:[/red] {e}")
        raise typer.Exit(1) from e
    except WorkflowConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(1) from e
    except BudjiraError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1) from e
