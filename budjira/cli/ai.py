"""AI-related commands for budjira."""

import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(
    name="ai",
    help="AI integration commands - generate prompts and guides for AI assistants",
    no_args_is_help=True,
)

console = Console()


def _generate_usage_prompt() -> str:
    """Generate comprehensive AI usage prompt for budjira.

    Returns:
        Markdown-formatted prompt text explaining all budjira functionality
    """
    return """# budjira - Jira CLI Tool Usage Guide for AI Assistants

## Overview

**budjira** (pronounced "buddy-ra") is a command-line interface for Jira Cloud. It provides efficient,
AI-friendly access to Jira functionality including connection management, issue search, issue creation,
and time tracking.

**Key Features:**
- Multi-connection management with environment variable support
- JQL-based search with convenient filter options
- Interactive and non-interactive issue creation
- Automatic update checking via GitHub Releases
- Rich terminal output with tables and colors

---

## Connection Management

### Setup and Configuration

Connections are stored in `~/.config/budjira/` following XDG Base Directory specification.

#### Create New Connection
```bash
budjira connect
```
Interactive prompts for:
- Jira URL (e.g., https://your-company.atlassian.net)
- Email address
- API Token (create at: https://id.atlassian.com/manage-profile/security/api-tokens)
- Default project key

#### List All Connections
```bash
budjira connect list
```
Shows table with name, URL, email, project, and default status.

#### Show Connection Details
```bash
budjira connect show [NAME]
```
Display detailed information for specific connection (or current if no name provided).

#### Test Connection
```bash
budjira connect test [NAME]
```
Verify connectivity and display Jira server information.

#### Set Default Connection
```bash
budjira connect use NAME
```
Set a connection as the global default.

#### Show Active Connection
```bash
budjira connect current
```
Display which connection is currently active (considering all resolution methods).

#### Remove Connection
```bash
budjira connect remove [NAME]
```
Delete connection and its credentials.

### Connection Resolution Priority

budjira resolves the active connection using this hierarchy (highest priority first):

1. **CLI flag**: `--connection NAME`
2. **Environment variable**: `BUDJIRA_CONNECTION=NAME`
3. **Config default**: Set via `budjira connect use NAME`

Example:
```bash
# Use specific connection for one command
budjira search --connection prod-jira "project = PROJ"

# Set environment variable for session
export BUDJIRA_CONNECTION=prod-jira
budjira search "project = PROJ"
```

---

## Searching Issues

### JQL Query Search

```bash
budjira search "JQL_QUERY"
```

Examples:
```bash
# Search by project and status
budjira search "project = MYPROJ AND status = 'In Progress'"

# Complex query
budjira search "project = MYPROJ AND assignee = currentUser() AND status != Done ORDER BY updated DESC"
```

### Filter-Based Search

Convenient alternative to writing JQL manually:

```bash
# Filter by status
budjira search --status "In Progress"

# Filter by assignee
budjira search --assignee currentUser()

# Multiple filters (combined with AND)
budjira search --project MYPROJ --type Bug --status Open

# Limit results
budjira search --status "To Do" --max 50
```

**Available Filters:**
- `--project KEY`: Filter by project key
- `--status STATUS`: Filter by status name
- `--assignee USER`: Filter by assignee (supports currentUser())
- `--type TYPE`: Filter by issue type (Bug, Story, Task, etc.)
- `--max N`: Limit number of results (default: 50)

### Search Output

Results display as a table with:
- Issue Key
- Summary
- Status
- Assignee
- Type
- Priority
- Created date
- Updated date

---

## Creating Issues

### Interactive Mode (Default)

```bash
budjira create issue "Issue summary"
```

Prompts for:
- Issue type (Story, Bug, Task, etc.)
- Description (optional)
- Priority (optional)
- Assignee (optional)
- Labels (optional)

### Non-Interactive Mode

```bash
budjira create issue "Issue summary" --no-interactive [OPTIONS]
```

**Options:**
- `--type TYPE`: Issue type (Bug, Story, Task, Epic, Sub-task)
- `--description TEXT`: Full description
- `--priority PRIORITY`: Priority level (Highest, High, Medium, Low, Lowest)
- `--assignee USER`: Assign to user (username or account ID)
- `--label TAG`: Add label (can be used multiple times)
- `--project KEY`: Override default project

**Examples:**

```bash
# Simple bug with type and priority
budjira create issue "Login button not working" \\
  --type Bug \\
  --priority High \\
  --no-interactive

# Feature story with full details
budjira create issue "Add export functionality" \\
  --type Story \\
  --description "Users should be able to export data to CSV and JSON formats" \\
  --assignee jdoe \\
  --label feature \\
  --label backend \\
  --priority Medium \\
  --no-interactive

# Quick task creation
budjira create issue "Update documentation" \\
  --type Task \\
  --no-interactive
```

---

## Update Management

### Check for Updates

```bash
budjira update --check
```

Checks GitHub Releases for newer versions (respects 24h cache).

### Install Latest Version

```bash
budjira update
```

Interactive update process:
1. Shows available version and release notes
2. Asks for confirmation
3. Runs installation script
4. Restarts with new version

### Force Update Check

```bash
budjira update --check --force
```

Bypass cache and check immediately.

### Automatic Update Notifications

budjira automatically checks for updates on startup (once per 24h) unless disabled in config.

Disable automatic checks:
```bash
# Edit ~/.config/budjira/config.toml
[global]
check_updates = false
```

---

## Shell Completion

### Enable Completion

One-time setup for bash/zsh/fish:
```bash
budjira --install-completion
```

Restart shell or open new terminal for changes to take effect.

### Test Completion

```bash
budjira <TAB>          # Shows available commands
budjira connect <TAB>  # Shows connect subcommands
```

### Manual Installation

If auto-install doesn't work:

```bash
# Bash
budjira --show-completion bash > ~/.local/share/bash-completion/completions/budjira

# Zsh
budjira --show-completion zsh > ~/.zsh/completions/_budjira

# Fish
budjira --show-completion fish > ~/.config/fish/completions/budjira.fish
```

---

## Global Options

Available on all commands:

- `--quiet`, `-q`: Suppress header output (useful for scripts)
- `--debug`, `-d`: Enable debug output
- `--version`, `-v`: Show version and exit
- `--help`, `-h`: Show help message

---

## Common Workflows for AI Assistants

### 1. Search for User's Open Issues

```bash
budjira search --assignee currentUser() --status "In Progress"
```

### 2. Create Issue from Context

```bash
# Interactive for clarification
budjira create issue "Summary from conversation"

# Non-interactive when all details are known
budjira create issue "Implement feature X" \\
  --type Story \\
  --description "Detailed requirements..." \\
  --priority High \\
  --label feature \\
  --no-interactive
```

### 3. Find Recent Issues in Project

```bash
budjira search "project = PROJ ORDER BY updated DESC" --max 20
```

### 4. Search by Keywords

```bash
budjira search "project = PROJ AND text ~ 'authentication'" --max 10
```

### 5. Check Bugs Assigned to User

```bash
budjira search --type Bug --assignee currentUser() --status Open
```

---

## Error Handling

### Connection Errors

If no connection is configured:
```
Error: No connection configured. Run 'budjira connect' to set up.
```

If connection fails:
```
Error: Failed to connect to Jira. Check your credentials and network.
```

### Authentication Errors

Invalid API token:
```
Error: Authentication failed. Check your API token.
```

### Search Errors

Invalid JQL:
```
Error: Invalid JQL query: [Jira error message]
```

---

## Configuration Files

Located in `~/.config/budjira/`:

- `connections.toml` - Connection definitions
- `credentials/` - Secure credential storage (mode 0o600)
- `config.toml` - Global settings
- `cache/` - Optional issue cache (future feature)
- `logs/` - Per-context log files

---

## Tips for AI Assistants

1. **Always check connection first**: Use `budjira connect current` to verify setup
2. **Use filters over JQL**: More user-friendly for simple queries
3. **Interactive mode for missing details**: Use interactive create when user hasn't provided all info
4. **Non-interactive for automation**: Use `--no-interactive` when all details are available
5. **Respect quiet mode**: Add `-q` flag when parsing output programmatically
6. **Connection override**: Use `--connection NAME` when user has multiple Jira instances

---

## Version Information

Current version can be checked with:
```bash
budjira --version
```

Update to latest:
```bash
budjira update
```

---

## Support and Documentation

- GitHub: https://github.com/cdds-ab/budjira
- Issues: https://github.com/cdds-ab/budjira/issues
- Releases: https://github.com/cdds-ab/budjira/releases

---

**This guide is generated by budjira itself and reflects the current feature set.**
"""


@app.command("usage-prompt")
def usage_prompt() -> None:
    """Generate comprehensive usage guide for AI assistants.

    Outputs a detailed, markdown-formatted guide explaining all budjira
    functionality. This prompt can be provided to AI assistants to help
    them understand and use budjira effectively.

    The guide includes:
    - Connection management
    - Issue search (JQL and filters)
    - Issue creation (interactive and non-interactive)
    - Update management
    - Common workflows and examples
    - Error handling patterns

    Examples:
        # Display the guide in terminal
        budjira ai usage-prompt

        # Copy to clipboard (requires xclip/pbcopy)
        budjira ai usage-prompt | xclip -selection clipboard

        # Save to file
        budjira ai usage-prompt > budjira-guide.md
    """
    prompt = _generate_usage_prompt()

    # Render as Markdown for beautiful terminal output
    md = Markdown(prompt)
    console.print(md)
