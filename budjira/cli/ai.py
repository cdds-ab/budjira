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
issue updates, epic management, and comprehensive time tracking.

**Key Features:**
- Multi-connection management with environment variable support
- JQL-based search with convenient filter options
- Interactive and non-interactive issue creation
- Definition of Ready (DoR) templates with validation
- Issue updates (status transitions, fields, labels, epic linking)
- Epic management with progress tracking
- Comprehensive time tracking (worklogs and estimates)
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

## Viewing Issue Details

### Show Full Issue Information

```bash
budjira show ISSUE-KEY
```

**Displays comprehensive information:**
- Summary and description (with Markdown rendering)
- Issue type, status, priority
- Assignee and reporter
- Epic information (if linked to an epic)
- Time tracking (original estimate, remaining, time spent)
- Labels and components
- Comments with timestamps and authors
- Attachments with file sizes and types
- Creation and update timestamps

**Examples:**

```bash
# View issue details
budjira show PROJ-123

# View issue from specific connection
budjira show PROJ-456 --connection my-connection
```

**Use Cases:**
- Read full issue descriptions and acceptance criteria
- Review comments and discussion history
- Check time tracking and estimates
- View attachments and related files
- Understand issue context before making changes

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

## Definition of Ready (DoR) Templates

### Manage DoR Templates

budjira supports customizable templates for different issue types to ensure consistent quality.

```bash
# List all DoR templates
budjira dor list

# View template for specific issue type
budjira dor show Story

# Edit template in your editor
budjira dor edit Story

# Validate template structure
budjira dor validate Story
```

**Default Templates:**
- **Story**: Context, User Story, Acceptance Criteria (all required)
- **Bug**: Steps to Reproduce, Expected Behavior, Actual Behavior, Environment
- **Task**: Description, Acceptance Criteria

### Interactive Creation with DoR

When creating issues interactively, budjira will offer to open your editor with the DoR template:

```bash
$ budjira create issue "Add user login"
Issue type: Story
Use DoR template for Story? [Y/n]: y
# Opens editor with pre-filled sections:
## Context


## User Story
As a [role]
I want to [action]
So that [benefit]

## Acceptance Criteria
- [ ]
```

**Configuration:**
- Templates stored in `~/.config/budjira/dor-templates.toml`
- Validation levels: `strict` (block), `warn` (allow), `off` (disabled)
- Skip validation with `--skip-dor` flag
- Configure via `enforce_dor` and `dor_validation_level` in global config

**Validation:**
- Checks for required sections (## Section Name format)
- Warns on empty section content
- Customizable per issue type

---

## Updating Issues

### Update Issue Fields and Status

```bash
budjira issue update ISSUE-KEY [OPTIONS]
```

Update existing issues with status transitions, field changes, and label management.

**Options:**
- `--status STATUS`, `-s`: Transition to new status
- `--assignee USER`, `-a`: Assign to user (username, accountId, or `currentUser()`)
- `--priority PRIORITY`, `-p`: Set priority (Highest, High, Medium, Low, Lowest)
- `--summary TEXT`: Update summary/title
- `--description TEXT`: Update description
- `--add-label TAG`: Add label (repeatable)
- `--remove-label TAG`: Remove label (repeatable)
- `--epic EPIC-KEY`, `-e`: Link issue to epic

**Examples:**

```bash
# Transition status
budjira issue update PROJ-123 --status "In Progress"

# Assign to current user
budjira issue update PROJ-123 --assignee currentUser()

# Multiple updates at once
budjira issue update PROJ-123 \\
  --status Done \\
  --priority Low \\
  --add-label completed

# Update summary and description
budjira issue update PROJ-456 \\
  --summary "New title for issue" \\
  --description "Updated detailed description"

# Link to epic
budjira issue update PROJ-789 --epic PROJ-100

# Add multiple labels
budjira issue update PROJ-123 \\
  --add-label urgent \\
  --add-label backend \\
  --add-label security
```

### Show Available Transitions

```bash
budjira issue transitions ISSUE-KEY
```

Display all workflow transitions available from the issue's current status.

**Example:**
```bash
budjira issue transitions PROJ-123
# Shows: To Do, In Progress, In Review, Done, etc.
```

**Note:** Status transitions are case-insensitive, so "in progress", "In Progress", and "IN PROGRESS" all work.

---

## Epic Management

### View Epic with Child Issues

```bash
budjira epic show EPIC-KEY
```

Display epic details including all linked child issues and progress.

**Output includes:**
- Epic key, summary, and description
- Status and priority
- Progress: X/Y issues done (percentage)
- Table of all child issues with their status
- Visual status indicators:
  - ✅ Done/Closed/Resolved
  - 🔄 In Progress/In Review
  - 📋 To Do/Open/Backlog

**Example:**
```bash
budjira epic show PROJ-100
# Shows epic with all stories and tasks
# Progress: 12/20 issues done (60%)
```

---

## Time Tracking

### Add Worklog Entry

```bash
budjira worklog add ISSUE-KEY TIME [OPTIONS]
```

Log time spent on an issue. Time can be specified in hours (h), minutes (m), or combined (e.g., 2h30m).

**Time Formats:**
- `1h` - 1 hour
- `30m` - 30 minutes
- `2h30m` - 2 hours 30 minutes
- `1.5h` - 1.5 hours (90 minutes)

**Options:**
- `--comment TEXT`, `-c`: Add comment to worklog entry
- `--started DATETIME`, `-s`: Specify when work started (default: now)

**Datetime Formats for --started:**
- ISO format: `2024-10-25T14:30:00` or `2024-10-25 14:30:00`
- Date only: `2024-10-25` (time defaults to 00:00)
- Relative: `today` or `yesterday`

**Examples:**

```bash
# Log 2 hours of work
budjira worklog add PROJ-123 2h

# Log work with comment
budjira worklog add PROJ-123 3h --comment "Implemented user authentication"

# Log work started at specific time
budjira worklog add PROJ-123 1h30m --started "2024-10-24 14:00" --comment "Code review"

# Log work from yesterday
budjira worklog add PROJ-123 4h --started yesterday --comment "Bug fixing"

# Log work from today at specific time
budjira worklog add PROJ-123 2h --started "today"
```

### List Worklog Entries

```bash
budjira worklog list ISSUE-KEY
```

Display all worklog entries for an issue.

**Output includes:**
- Author
- Time spent
- Started date/time
- Comment (if any)

**Example:**
```bash
budjira worklog list PROJ-123
# Shows table of all worklog entries
```

### Time Estimates

Set time estimates when creating or updating issues.

**During Issue Creation:**

```bash
budjira create issue "Feature implementation" \\
  --type Story \\
  --original-estimate 8h \\
  --remaining-estimate 8h \\
  --no-interactive
```

**During Issue Update:**

```bash
# Update time estimates
budjira issue update PROJ-123 \\
  --original-estimate 10h \\
  --remaining-estimate 5h

# Log work while updating
budjira issue update PROJ-456 \\
  --log-work 2h \\
  --work-comment "Completed API integration"
```

**Time Estimate Options:**
- `--original-estimate TIME`: Initial time estimate for the issue
- `--remaining-estimate TIME`: Remaining time estimate
- `--log-work TIME`: Log work time (alternative to `worklog add`)
- `--work-comment TEXT`: Comment for work logged via `--log-work`

**Combined Example:**

```bash
# Create issue with time tracking
budjira create issue "Implement feature X" \\
  --type Story \\
  --description "Full feature description" \\
  --original-estimate 16h \\
  --remaining-estimate 16h \\
  --no-interactive

# Log work and update remaining estimate
budjira issue update PROJ-789 \\
  --log-work 4h \\
  --work-comment "Completed backend API" \\
  --remaining-estimate 12h
```

---

## Tempo Timesheets Integration

**Note:** Tempo integration requires separate setup and API token.

### Setup Tempo Integration

```bash
budjira connect tempo-setup
```

Interactive setup that:
1. Prompts for Tempo API token (create at: Tempo → Settings → API Integration)
2. Enables Tempo for the active connection
3. Securely stores token separately from Jira credentials

### Log Work to Tempo

```bash
budjira tempo log ISSUE-KEY TIME [OPTIONS]
```

Log time spent on an issue directly to Tempo Timesheets.

**Time Formats:**
- `1h` - 1 hour
- `30m` - 30 minutes
- `2h30m` - 2 hours 30 minutes
- `1.5h` - 1.5 hours (90 minutes)

**Options:**
- `--comment TEXT`, `-c`: Add comment/description to worklog
- `--started DATETIME`, `-s`: When work started (default: now)

**Datetime Formats for --started:**
- ISO format: `2025-10-28T14:30:00` or `2025-10-28 14:30:00`
- Date only: `2025-10-28` (time defaults to 09:00)
- Relative: `today` or `yesterday`

**Examples:**

```bash
# Log 2 hours of work
budjira tempo log PROJ-123 2h

# Log work with comment
budjira tempo log PROJ-123 3h --comment "Development work"

# Log work started yesterday
budjira tempo log PROJ-456 3h30m --started yesterday --comment "Client meeting"

# Log work at specific datetime
budjira tempo log PROJ-123 2h --started "2025-10-24 14:00" --comment "Code review"
```

### List Tempo Worklogs

```bash
budjira tempo worklogs [ISSUE-KEY] [OPTIONS]
```

Display worklog entries from Tempo with filtering options.

**Options:**
- `--from DATE`: Start date filter (YYYY-MM-DD)
- `--to DATE`: End date filter (YYYY-MM-DD)
- `--max N`, `-m`: Maximum results (default: 50)
- `--no-epic`: Skip epic information for faster output (JSON mode only)

**Examples:**

```bash
# List all worklogs for an issue
budjira tempo worklogs PROJ-123

# List worklogs for date range
budjira tempo worklogs --from 2025-10-01 --to 2025-10-31

# List recent worklogs across all issues
budjira tempo worklogs --max 20

# JSON output for automation
budjira --format json tempo worklogs --from 2025-10-01 --to 2025-10-31
```

**Output includes:**
- Tempo worklog ID
- Issue key and epic information
- Time spent (seconds and display format)
- Start date and time
- Author information
- Description/comment

### Update Tempo Worklog

```bash
budjira tempo update-worklog WORKLOG_ID [OPTIONS]
```

**NEW in v1.9.0** - Update existing Tempo worklog without deletion. More efficient than delete+recreate and preserves worklog ID and audit trail.

**Options:**
- `--time-spent TIME`, `-t`: Update time spent (e.g., 2h, 30m, 2h30m)
- `--started DATETIME`, `-s`: Update start date/time
- `--comment TEXT`, `-c`: Update worklog comment/description
- `--force`, `-f`: Skip confirmation prompt

**Features:**
- **Partial updates**: Only specify fields you want to change
- **Confirmation preview**: Shows before/after comparison (unless --force)
- **Preserves worklog ID**: No need to delete and recreate
- **Efficient**: Single API call instead of two

**Examples:**

```bash
# Update only the date
budjira tempo update-worklog 642 --started 2025-10-28

# Update time and comment
budjira tempo update-worklog 642 --time-spent 4h --comment "Revised estimate"

# Update all fields with confirmation
budjira tempo update-worklog 642 --started "2025-10-28 14:00" --time-spent 3h30m --comment "Final"

# Force update without confirmation (for automation)
budjira tempo update-worklog 642 --started yesterday --force

# Update only comment
budjira tempo update-worklog 642 --comment "Updated description"
```

**Use Cases:**
- Correct wrong date without losing worklog ID
- Adjust time spent after review
- Update comment with additional details
- Automation scripts that need to modify worklogs

### Delete Tempo Worklog

```bash
budjira tempo delete-worklog WORKLOG_ID [OPTIONS]
```

Delete a worklog entry from Tempo by its ID.

**Options:**
- `--force`, `-f`: Skip confirmation prompt

**Examples:**

```bash
# Delete with confirmation
budjira tempo delete-worklog 12345

# Delete without confirmation
budjira tempo delete-worklog 12345 --force
```

### List Tempo Accounts

```bash
budjira tempo accounts [OPTIONS]
```

List Tempo Accounts for billing and project tracking.

**Options:**
- `--max N`, `-m`: Maximum results (default: 50)

**Example:**

```bash
budjira tempo accounts
```

**Output includes:**
- Account key
- Account name
- Status (OPEN/CLOSED)
- Account ID

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

### 2. Create Issue with DoR Template

```bash
# Interactive with DoR template (Story)
budjira create issue "Add user authentication"
# Prompts for issue type, then opens editor with template

# Skip DoR validation if needed
budjira create issue "Quick fix" --type Task --skip-dor --no-interactive
```

### 3. Create Issue from Context

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

### 4. Update Issue Status and Fields

```bash
# Move issue to In Progress and assign to current user
budjira issue update PROJ-123 \\
  --status "In Progress" \\
  --assignee currentUser()

# Mark issue done with label
budjira issue update PROJ-456 \\
  --status Done \\
  --add-label completed
```

### 5. Manage DoR Templates

```bash
# View available templates
budjira dor list

# Customize Story template
budjira dor edit Story

# Check template is valid
budjira dor validate Story
```

### 6. View Epic Progress

```bash
# Check epic status and progress
budjira epic show PROJ-100

# Find epic issues that are still open
budjira search "Epic Link = PROJ-100 AND status != Done"
```

### 7. Find Recent Issues in Project

```bash
budjira search "project = PROJ ORDER BY updated DESC" --max 20
```

### 8. Search by Keywords

```bash
budjira search "project = PROJ AND text ~ 'authentication'" --max 10
```

### 9. Check Bugs Assigned to User

```bash
budjira search --type Bug --assignee currentUser() --status Open
```

### 10. Complete Issue Workflow

```bash
# 1. Find issue
budjira search --assignee currentUser() --status "To Do"

# 2. Start work
budjira issue update PROJ-789 --status "In Progress"

# 3. Update as work progresses
budjira issue update PROJ-789 \\
  --add-label in-review \\
  --summary "Updated title with clarification"

# 4. Complete
budjira issue update PROJ-789 \\
  --status Done \\
  --add-label completed
```

### 11. Time Tracking Workflow

```bash
# 1. Create issue with time estimate
budjira create issue "Implement API endpoint" \\
  --type Story \\
  --original-estimate 8h \\
  --remaining-estimate 8h \\
  --no-interactive

# 2. Log work as you progress
budjira worklog add PROJ-456 2h --comment "Set up project structure"

# 3. Update remaining estimate
budjira issue update PROJ-456 --remaining-estimate 6h

# 4. Log more work
budjira worklog add PROJ-456 3h --comment "Implemented core functionality"

# 5. View all logged time
budjira worklog list PROJ-456

# 6. Final work log and complete
budjira issue update PROJ-456 \\
  --log-work 3h \\
  --work-comment "Completed testing and documentation" \\
  --remaining-estimate 0h \\
  --status Done
```

### 12. Tempo Time Tracking Workflow

```bash
# 1. Setup Tempo integration (one-time)
budjira connect tempo-setup

# 2. Log work to Tempo
budjira tempo log PROJ-123 2h --comment "Development work"

# 3. Log work from yesterday
budjira tempo log PROJ-456 3h30m --started yesterday --comment "Client meeting"

# 4. Check logged time for an issue
budjira tempo worklogs PROJ-123

# 5. Correct a wrong date (without deleting)
budjira tempo update-worklog 642 --started 2025-10-28

# 6. Adjust time after review
budjira tempo update-worklog 642 --time-spent 4h --comment "Revised after review"

# 7. View worklogs for date range (automation)
budjira --format json tempo worklogs --from 2025-10-01 --to 2025-10-31

# 8. Delete incorrect worklog
budjira tempo delete-worklog 999 --force
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
def usage_prompt(
    plain: bool = typer.Option(False, "--plain", "-p", help="Output plain markdown without terminal formatting"),
) -> None:
    """Generate comprehensive usage guide for AI assistants.

    Outputs a detailed, markdown-formatted guide explaining all budjira
    functionality. This prompt can be provided to AI assistants to help
    them understand and use budjira effectively.

    The guide includes:
    - Connection management
    - Issue search (JQL and filters)
    - Issue creation (interactive and non-interactive)
    - Issue updates and transitions
    - Epic management
    - Update management
    - Common workflows and examples
    - Error handling patterns

    Examples:
        # Display the guide in terminal (formatted)
        budjira ai usage-prompt

        # Output plain markdown for files/clipboard
        budjira ai usage-prompt --plain

        # Save to file
        budjira ai usage-prompt --plain > .claude/ai-usage-prompt.md

        # Copy to clipboard (requires xclip/pbcopy)
        budjira ai usage-prompt --plain | xclip -selection clipboard
    """
    prompt = _generate_usage_prompt()

    if plain:
        # Output raw markdown for file/clipboard
        print(prompt)
    else:
        # Render as Markdown for beautiful terminal output
        md = Markdown(prompt)
        console.print(md)
