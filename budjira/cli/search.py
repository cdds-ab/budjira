"""Search for Jira issues."""

from __future__ import annotations

import re

import typer
from rich.console import Console
from rich.table import Table

from budjira.core.jira_client import JiraClient
from budjira.utils.connection import get_active_connection
from budjira.utils.errors import BudjiraError

# String literals are blanked (length-preserving) before clause detection so
# their contents (e.g. summary ~ "project in scope") cannot fake a clause.
# Backslash escapes are honoured so \" does not end the literal early.
_JQL_LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')

# A raw JQL already scoping or historicising itself:
# project = X / project != X / project in (...) / project was X / project changed
_JQL_PROJECT_CLAUSE_RE = re.compile(
    r"\bproject\s*(=|!=|(not\s+)?in\b|was\b(\s+not\b)?(\s+in\b)?|changed\b)",
    re.IGNORECASE,
)

# Quoted field names survive the blanking of literals, so they need a
# separate check against the original JQL
_JQL_QUOTED_PROJECT_RE = re.compile(
    r"[\"']project[\"']\s*(=|!=|(not\s+)?in\b|was\b|changed\b)",
    re.IGNORECASE,
)

# ORDER BY must stay outside the parenthesised scoped query
_JQL_ORDER_BY_RE = re.compile(r"\border\s+by\b", re.IGNORECASE)

app = typer.Typer(
    name="search",
    help="Search for Jira issues",
    no_args_is_help=True,
)
console = Console()


@app.command()
def search(
    jql: str = typer.Argument(
        None,
        help="JQL query string (if not provided, search parameters are used)",
    ),
    project: str = typer.Option(
        None,
        "--project",
        "-p",
        help="Project key to search in (uses connection default if not specified)",
    ),
    status: str = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (e.g., 'In Progress', 'Done')",
    ),
    assignee: str = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Filter by assignee (username or 'currentUser()')",
    ),
    issue_type: str = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by issue type (Bug, Task, Story, etc.)",
    ),
    max_results: int = typer.Option(
        50,
        "--max",
        "-m",
        "--limit",
        "-n",
        "--max-results",
        help="Maximum total number of results to return (across pages)",
        min=1,
        max=1000,
    ),
    connection: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Connection name to use (overrides BUDJIRA_CONNECTION env var)",
    ),
    all_projects: bool = typer.Option(
        False,
        "--all-projects",
        help="Disable project scoping: raw JQL is sent unchanged, filters get no project clause",
    ),
) -> None:
    """Search for Jira issues using JQL or filters.

    You can either provide a raw JQL query string or use the filter options
    (project, status, assignee, type) to build a query automatically.
    Raw JQL without a project clause is scoped to the connection's project
    by default; --all-projects disables that.

    Examples:

        # Search by raw JQL
        budjira search "project = PROJ AND status = 'In Progress'"

        # Search using filters
        budjira search --status "In Progress" --assignee currentUser()

        # Search for bugs in specific project
        budjira search --project PROJ --type Bug
    """
    try:
        # Get active connection (from --connection, env var, or config)
        active_connection = get_active_connection(connection)

        if project and all_projects:
            console.print("[red]✗[/red] --project and --all-projects cannot be used together", style="red")
            raise typer.Exit(1)

        # Build JQL query if not provided
        if jql is None:
            jql_parts: list[str] = []

            # Use provided project or connection default
            if not all_projects:
                search_project = project or active_connection.project_key
                jql_parts.append(f"project = {search_project}")

            if status:
                jql_parts.append(f"status = '{status}'")
            if assignee:
                # If assignee looks like a function call, don't quote it
                if "(" in assignee:
                    jql_parts.append(f"assignee = {assignee}")
                else:
                    jql_parts.append(f"assignee = '{assignee}'")
            if issue_type:
                jql_parts.append(f"type = '{issue_type}'")

            jql = " AND ".join(jql_parts)

            if not jql:
                console.print("[red]✗[/red] No search criteria provided", style="red")
                console.print(
                    "[dim]Provide either a JQL query or use filter options (--status, --assignee, etc.)[/dim]"
                )
                raise typer.Exit(1)

        elif not all_projects:
            # Raw JQL without a project clause: scope to the connection's
            # project. Literals are blanked (length-preserving) so quoted
            # text cannot fake a clause; quoted field names are checked on the
            # original; ORDER BY stays outside the parens.
            blanked = _JQL_LITERAL_RE.sub(lambda m: " " * len(m.group(0)), jql)
            if not _JQL_PROJECT_CLAUSE_RE.search(blanked) and not _JQL_QUOTED_PROJECT_RE.search(jql):
                order_match = _JQL_ORDER_BY_RE.search(blanked)
                head = (jql[: order_match.start()] if order_match else jql).strip()
                tail = jql[order_match.start() :] if order_match else ""
                scoped = (
                    f"project = {active_connection.project_key} AND ({head})"
                    if head
                    else f"project = {active_connection.project_key}"
                )
                jql = f"{scoped} {tail}".strip()

        console.print(f"[dim]Searching with JQL:[/dim] [cyan]{jql}[/cyan]\n")

        # Create client and search
        client = JiraClient.from_connection(active_connection)
        issues = client.search_issues(jql, max_results=max_results)

        if not issues:
            console.print("[yellow]⚠[/yellow] No issues found", style="yellow")
            return

        # Display results in table
        table = Table(
            title=f"Search Results ({len(issues)} issue{'s' if len(issues) != 1 else ''})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="blue")
        table.add_column("Priority", style="yellow")
        table.add_column("Summary")
        table.add_column("Assignee", style="green")

        for issue in issues:
            table.add_row(
                issue.key,
                issue.issue_type,
                issue.status,
                issue.priority or "-",
                issue.summary[:60] + "..." if len(issue.summary) > 60 else issue.summary,
                issue.assignee or "Unassigned",
            )

        console.print(table)

        # Show summary
        console.print(f"\n[dim]Found {len(issues)} issue{'s' if len(issues) != 1 else ''}[/dim]")
        if len(issues) == max_results:
            console.print(f"[dim]Limited to {max_results} results. Use --max/--limit to increase.[/dim]")

    except BudjiraError as e:
        console.print(f"[red]✗[/red] {e}", style="red")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}", style="red")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
