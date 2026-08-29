<div align="center">
  <img src="images/budjira_logo.jpg" alt="budjira - Your CLI Pal for Jira" width="600">

  # budjira

  **Your CLI Pal for Jira**

[![CI](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml/badge.svg)](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

---

**budjira** (pronounced "buddy-ra") is your CLI buddy for Jira. It provides efficient, user-friendly command-line access to **Jira Cloud** with features designed for both developers and AI-assisted project management.

> **Note:** budjira is designed for **Jira Cloud only** and does not support Jira Server or Data Center. For legacy on-premise installations, consider using [go-jira](https://github.com/go-jira/jira) or planning your Cloud migration.

## ✨ Features

- 🔗 **Multi-Connection**: Manage multiple Jira instances and projects
- 🎯 **Context-Aware**: Name-based connection management with environment variable and CLI override support
- 🔄 **Auto-Update**: Automatic update checks with GitHub Releases integration
- 🤖 **AI-Friendly**: Designed for seamless AI-assisted workflows with built-in usage prompt generation
- 🎨 **Rich Output**: Beautiful, colorful terminal output with tables and formatting
- 🔍 **Search & Filter**: Powerful JQL-based ticket search with filter options
- ✏️ **Create Issues**: Interactive and non-interactive issue creation
- 📋 **Definition of Ready**: Customizable templates for Story, Bug, Task with validation
- 🔄 **Update Issues**: Transition status, update fields, manage labels, delete issues
- 🎯 **Epic Management**: Link stories to epics and view epic progress
- 💬 **Comment Management**: Full comment CRUD (add, list, show, update, delete) without time tracking
- 📎 **Attachments**: Upload files to issues and embed images inline in comments
- ⏱️ **Time Tracking**: Comprehensive worklog management (add, list, update, delete) and time estimates
- 🎼 **Tempo Integration**: Full support for Tempo Timesheets API for enterprise time tracking
- 💶 **Billing Reports**: Billable vs. non-billable reporting for workflow profiles, table or JSON
- 📊 **JSON Output**: Machine-readable JSON format for automation and integration with other tools

## 📦 Installation

### Quick Install (Recommended)

Install with a single curl command:

```bash
curl -LsSf https://raw.githubusercontent.com/cdds-ab/budjira/master/install.sh | sh
```

This will:
- Install `uv` if not already present
- Clone the budjira repository to `~/.local/share/budjira`
- Install dependencies
- Create a symlink in `~/.local/bin/budjira`

Make sure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/cdds-ab/budjira.git
cd budjira

# Install dependencies
uv sync

# Run budjira
uv run budjira --help

# Or create a symlink
ln -s "$(pwd)/.venv/bin/budjira" ~/.local/bin/budjira
```

### Update

To update to the latest version:
```bash
curl -LsSf https://raw.githubusercontent.com/cdds-ab/budjira/master/install.sh | sh
```

Or manually:
```bash
cd ~/.local/share/budjira
git pull
uv sync
```

### Shell Completion

budjira supports tab completion for bash, zsh, and fish shells.

**Enable completion** (one-time setup):
```bash
budjira --install-completion
```

This automatically configures your shell's completion system. Restart your shell or open a new terminal for changes to take effect.

**Test completion**:
```bash
budjira <TAB>          # Shows available commands
budjira connect <TAB>  # Shows connect subcommands
```

**Manual completion** (if auto-install doesn't work):
```bash
# Bash
budjira --show-completion bash > ~/.local/share/bash-completion/completions/budjira

# Zsh
budjira --show-completion zsh > ~/.zsh/completions/_budjira

# Fish
budjira --show-completion fish > ~/.config/fish/completions/budjira.fish
```

## 🚀 Quick Start

### 1. Connect to Jira

```bash
# Create a new connection for the current project
budjira connect

# You'll be prompted for:
# - Jira URL (e.g., https://your-company.atlassian.net)
# - Email
# - API Token (create one at https://id.atlassian.com/manage-profile/security/api-tokens)
# - Default project key
```

### 2. Manage Connections

```bash
# List all connections
budjira connect list

# Show connection details
budjira connect show [NAME]

# Test connection
budjira connect test [NAME]

# Set default connection
budjira connect use NAME

# Show active connection
budjira connect current

# Remove a connection
budjira connect remove [NAME]
```

### 3. Search for Issues

```bash
# Search with JQL query
budjira search "project = PROJ AND status = 'In Progress'"

# Search with filters
budjira search --status "In Progress" --assignee currentUser()
budjira search --project PROJ --type Bug --max 100

# Use specific connection
budjira search --connection my-connection --status Done
```

### 4. View Issue Details

Get comprehensive information about a specific issue including description, comments, time tracking, attachments, and more.

```bash
# Show full issue details
budjira show PROJ-123

# Show issue from specific connection
budjira show PROJ-456 --connection my-connection
```

**Displays:**
- Summary and description (with Markdown rendering)
- Issue type, status, priority, assignee, reporter
- Epic information (if linked to an epic)
- Time tracking (original estimate, remaining, time spent)
- Labels and components
- Comments with timestamps
- Attachments with file sizes
- Creation and update timestamps

### 5. Create Issues

```bash
# Interactive mode (default)
budjira create issue "Fix login bug"

# Non-interactive with all details
budjira create issue "Fix bug" --type Bug --priority High --no-interactive

# With description and labels
budjira create issue "Add feature" \
  --type Story \
  --description "Detailed description" \
  --assignee jdoe \
  --label feature --label frontend \
  --no-interactive

# Link to epic during creation (one-step workflow)
budjira create issue "User authentication" --type Story --epic PROJ-100

# Create multiple stories for same epic (efficient bulk creation)
budjira create issue "Story 1" --type Story --epic PROJ-100 --no-interactive
budjira create issue "Story 2" --type Story --epic PROJ-100 --no-interactive
budjira create issue "Story 3" --type Story --epic PROJ-100 --no-interactive

# Create a sub-task under a parent issue
budjira create issue "Implement login form" --type Subtask --parent PROJ-123 --no-interactive
```

**Epic Linking:**
- Use `--epic PROJ-100` to link issue to epic during creation
- Eliminates need for separate update step
- Perfect for creating multiple stories for same epic
- Works in both interactive and non-interactive modes

**Sub-tasks:**
- Use `--parent PROJ-123` to create a sub-task under a parent issue
- The sub-task type name differs per instance (`Subtask` or `Sub-task`); budjira
  detects sub-task types from cached project metadata (`budjira project show`)
- Creating a sub-task without `--parent` fails fast with a clear error instead of a
  cryptic Jira API response

**Description dialect:**

Jira renders descriptions with its legacy wiki-markup renderer. Which dialect
descriptions are written in is a property of the instance, so it belongs to the
connection: choose `markdown` (the default) for an instance where authors write
Markdown — budjira converts headings, lists, links and code fences to wiki markup on
upload. Choose `wiki` for an instance whose house format is already expressed in wiki
markup, e.g. panel macros and `#` ordered lists; the description is then sent
unchanged, because converting it would rewrite `#` list items into `h1.` headings.

```bash
# Set the dialect for a connection
budjira connect add --name house --url https://company.atlassian.net \
  --email user@example.com --project PROJ --description-dialect wiki

# Deviate for a single call (works on create and update)
budjira create issue "Fix login bug" --type Bug --no-interactive \
  --description-dialect wiki --description "$(cat description.txt)"
budjira issue update PROJ-123 --description-dialect markdown --description "## Notes"
```

The option wins over the connection setting, which wins over the default. Existing
configurations keep working unchanged: a connection without the key is `markdown`.

**Project metadata:** issue types, priorities and components are discovered from Jira and
cached locally — they drive validation of `--type`/`--priority` and sub-task detection:

```bash
budjira project sync          # fetch + cache (per connection project)
budjira project show          # inspect the cache
budjira project clear         # drop the cache
budjira project sync --force  # refresh despite a valid cache
```

### 6. Definition of Ready (DoR) Templates

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

**Interactive Creation with DoR:**
When creating issues interactively, budjira will offer to open your editor with the DoR template:

```bash
$ budjira create issue "Add user login"
Issue type: Story
Use DoR template for Story? [Y/n]: y
# Opens editor with:
## Context
# Why do we need this?

## User Story
As a [role]
I want to [action]
So that [benefit]

## Acceptance Criteria
- [ ]
```

**Configuration:**
- Templates stored in `~/.config/budjira/dor-templates.toml`
- Validation level: `strict` (block), `warn` (allow), or `off`
- Skip validation with `--skip-dor` flag

### 7. Update Issues

```bash
# Transition status
budjira issue update PROJ-123 --status "In Progress"

# Assign to current user
budjira issue update PROJ-123 --assignee currentUser()

# Multiple updates at once
budjira issue update PROJ-123 \
  --status Done \
  --priority Low \
  --add-label completed

# Link to epic
budjira issue update PROJ-123 --epic PROJ-100

# Show available transitions
budjira issue transitions PROJ-123

# Delete an issue (with confirmation)
budjira issue delete PROJ-123

# Delete without confirmation
budjira issue delete PROJ-123 --force

# Delete issue and its subtasks
budjira issue delete PROJ-123 --delete-subtasks
```

**Transition screen fields**

Some transitions present a screen with fields that must be filled:

```bash
# Inspect what a transition needs, without touching the issue
budjira issue update PROJ-123 --status "Resolve" --dry-run

# Supply screen fields by id or by display name
budjira issue update PROJ-123 --status "Resolve" \
  --field resolution=Done \
  --field "Solution details=Rolled out to production"
```

Missing required fields are prompted for interactively. With `--no-interactive`,
or when stdin is not a terminal, budjira aborts and lists exactly which fields
are needed instead of hanging on a prompt.

Some fields are enforced by a workflow validator rather than by the screen. Jira
reports those without naming the field; budjira matches the message against the
transition's fields and tells you which one it means.

### 8. View Epic Progress

```bash
# Show epic with all child stories (table format)
budjira epic show PROJ-100

# JSON output with time tracking for automation/reporting
budjira --format json epic show PROJ-100
```

**JSON Output Example:**
```json
{
  "epic": {
    "key": "PROJ-100",
    "summary": "Project Infrastructure",
    "status": "In Progress",
    "assignee": "John Doe",
    "priority": "High",
    "issue_type": "Epic",
    "url": "https://your-company.atlassian.net/browse/PROJ-100",
    "timetracking": {
      "originalEstimateSeconds": 72000,
      "remainingEstimateSeconds": 36000,
      "timeSpentSeconds": 36000,
      "originalEstimate": "20h",
      "remainingEstimate": "10h",
      "timeSpent": "10h"
    }
  },
  "stories": [
    {
      "key": "PROJ-101",
      "summary": "Setup CI/CD Pipeline",
      "status": "Done",
      "assignee": "Jane Smith",
      "issue_type": "Story",
      "priority": "High",
      "url": "https://your-company.atlassian.net/browse/PROJ-101",
      "timetracking": {
        "originalEstimateSeconds": 14400,
        "timeSpentSeconds": 14400,
        "originalEstimate": "4h",
        "timeSpent": "4h"
      }
    }
  ],
  "progress": {
    "total_issues": 5,
    "done_issues": 2,
    "in_progress_issues": 1,
    "todo_issues": 3,
    "progress_percent": 40
  }
}
```

**Use Cases:**
- **Project Reporting**: Generate HTML/PDF reports with epic progress
- **Dashboard Integration**: Feed data into custom dashboards
- **Time Analysis**: Analyze time tracking data for effort estimation
- **Automation**: Use in CI/CD pipelines or scripts

### 9. Manage Sprints

Query sprints, move issues between them, and drive the sprint lifecycle from
the CLI. The board is auto-detected (or set `board_id` in `connections.toml`).
Both company-managed (Scrum) and team-managed boards are supported; for
team-managed projects you can also pass `--sprint-id` directly, which skips
board detection entirely.

```bash
# List sprints (optionally filter by state)
budjira sprint list
budjira sprint list --state active

# Show the contents of a sprint (defaults to the active sprint)
budjira sprint show
budjira sprint show "Sprint 42" --mine

# Move issues into a sprint (by name or ID)
budjira sprint move PROJ-1 PROJ-2 --to "Sprint 42"
budjira sprint move PROJ-123 --sprint-id 100

# Create a new (future) sprint; dates are optional
budjira sprint create "Sprint 43" --start today --end 2026-06-14 --goal "Ship the API"

# Start a sprint (requires start + end dates)
budjira sprint start "Sprint 43" --start today --end 2026-06-14

# Close a sprint (defaults to the active sprint)
budjira sprint close --force
```

> **Note:** Creating, starting, and closing sprints requires Jira board-admin
> permissions. `move` only needs permission to edit the issues. `start` and
> `close` ask for confirmation unless you pass `--force`.

### 10. Check for Updates

budjira automatically checks for updates every 24 hours and notifies you when a new version is available.

```bash
# Check for updates manually
budjira update --check

# Update to latest version (interactive)
budjira update

# Force update check (bypass cache)
budjira update --check --force
```

`budjira update` uses the mechanism that matches your install: the install
script for a git checkout, `uv tool upgrade` for a `uv tool install`, and
`pipx upgrade` for a pipx install. If it cannot tell how budjira was installed,
it stops and asks you to update manually instead of installing a second copy
that could shadow the first one.

**Troubleshooting: GitHub API Rate Limits**

If you see `403 Client Error: rate limit exceeded` when checking for updates, you need to authenticate with GitHub:

```bash
# Option 1: Set GitHub Personal Access Token (no scopes needed)
export GITHUB_TOKEN=ghp_your_token_here

# Option 2: Use GitHub CLI token (if gh is installed)
export GH_TOKEN=$(gh auth token)

# Make it permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
source ~/.bashrc
```

**Create a token**: Go to https://github.com/settings/tokens (no scopes required for public repos)

**Why?** Unauthenticated requests are limited to 60/hour. Authenticated requests get 5,000/hour.

### 11. AI Integration

Generate comprehensive usage guides for AI assistants.

```bash
# Generate AI usage prompt
budjira ai usage-prompt

# Copy to clipboard (Linux with xclip)
budjira ai usage-prompt | xclip -selection clipboard

# Save to file
budjira ai usage-prompt > budjira-guide.md
```

The generated prompt includes:
- Complete command reference with examples
- Connection management workflows
- Search and create patterns
- Error handling guidance
- Common use cases for AI assistants

## Time Tracking

budjira provides comprehensive time tracking capabilities including worklog management and time estimates.

```bash
# Add work log entry
budjira worklog add PROJ-123 2h --comment "Fixed authentication bug"
budjira worklog add PROJ-123 1h30m --comment "Code review"

# Log work with specific start time
budjira worklog add PROJ-123 3h --started "2025-10-24 14:00" --comment "Implemented feature"
budjira worklog add PROJ-123 2h --started "yesterday" --comment "Bug fixing"

# List all worklogs for an issue (shows worklog IDs)
budjira worklog list PROJ-123

# Correct an existing worklog (keeps ID and audit trail; only your own worklogs)
budjira worklog update PROJ-123 12345 --time-spent 6h
budjira worklog update PROJ-123 12345 --started yesterday --comment "Re-balanced estimate"
budjira worklog update PROJ-123 12345 --time-spent 2h15m --force   # Skip confirmation

# Delete a worklog entry
budjira worklog delete PROJ-123 12345
budjira worklog delete PROJ-123 12345 --force   # Skip confirmation

# Set time estimates when creating issues
budjira create issue "Add login feature" \
  --type Story \
  --original-estimate 8h \
  --remaining-estimate 8h

# Update time estimates
budjira issue update PROJ-123 --original-estimate 10h --remaining-estimate 5h

# Log work and update remaining estimate in one command
budjira issue update PROJ-123 --log-work 2h --work-comment "Implemented API endpoint"
```

**Supported Time Formats:**
- Hours: `2h`, `8h`
- Minutes: `30m`, `45m`
- Combined: `2h30m`, `1h45m`

**Supported Datetime Formats (for --started):**
- ISO format: `2025-10-25T14:30:00`, `2025-10-25 14:30`
- Date only: `2025-10-25` (time defaults to 00:00)
- Relative: `today`, `yesterday`

### Manage Comments

Add comments to Jira issues without logging time (unlike worklogs which combine comments with time tracking).

```bash
# Quick single-line comment
budjira comment add PROJ-123 "Deployed to production"

# Multi-line comment via editor
budjira comment add PROJ-123 --editor

# Editor opens automatically if no text provided
budjira comment add PROJ-123

# Use specific connection
budjira comment add PROJ-123 "Comment text" --connection my-connection

# Attach file(s) to the issue and reference them in the comment
budjira comment add PROJ-123 "See the chart" --attach chart.png

# Embed image(s) inline in the comment body (Jira Cloud)
budjira comment add PROJ-123 "Before/after:" --embed chart.png
```

Files can also be attached without a comment:

```bash
# Attach one or more files to an issue
budjira attach PROJ-123 chart.png
budjira attach PROJ-123 chart.png report.pdf
```

Existing comments can be listed, inspected, corrected and deleted without leaving the CLI:

```bash
# List comments (id, author, date, first line)
budjira comment list PROJ-123

# Show the full body of a comment
budjira comment show PROJ-123 10234

# Replace a comment body directly
budjira comment update PROJ-123 10234 "Corrected deployment note"

# Or edit the current body in your editor (prefilled)
budjira comment update PROJ-123 10234

# Delete a comment (asks for confirmation; --force skips)
budjira comment delete PROJ-123 10234
```

**Prefer `update` over `delete`:** Jira often forbids deleting comments, even for their
author (it answers with a 400 permission error). `comment update` is the reliable path
to correct a posted comment — the editor opens prefilled with the current body. If a
deletion is denied, the error message points you to `comment update`.

**Use Cases:**
- Status updates without time tracking
- Analysis results and findings
- Documentation links
- Deployment notifications
- Code review feedback

**Editor Support:**
- Opens your preferred editor (from `$EDITOR` environment variable, defaults to vim)
- Supports markdown formatting
- Multi-line content for detailed updates

### Tempo Timesheets Integration

For enterprise teams using [Tempo Timesheets](https://www.tempo.io/), budjira provides full API integration for advanced time tracking and billing.

**Setup:**

```bash
# Configure Tempo for your connection
budjira connect tempo-setup

# Create a Tempo API token at: Tempo → Settings → API Integration → Tokens
```

**Usage:**

```bash
# Log work via Tempo
budjira tempo log PROJ-123 2h --comment "Sizing analysis"
budjira tempo log PROJ-456 3h30m --started "yesterday" --comment "Client meeting"

# Log work with specific datetime
budjira tempo log PROJ-123 2h --started "2025-10-24 14:00" --comment "Development"

# List Tempo worklogs
budjira tempo worklogs PROJ-123                    # For specific issue
budjira tempo worklogs --from 2025-10-01 --to 2025-10-31  # Date range
budjira tempo worklogs --max 50                    # Limit results

# Update existing worklog (preserve ID and audit trail)
budjira tempo update-worklog 12345 --time-spent 3h
budjira tempo update-worklog 12345 --started "2025-10-28" --comment "Updated"
budjira tempo update-worklog 12345 --force        # Skip confirmation

# Delete worklog entry
budjira tempo delete-worklog 12345
budjira tempo delete-worklog 12345 --force        # Skip confirmation

# List Tempo accounts (for billing)
budjira tempo accounts
```

**Features:**
- ✅ Full Tempo Cloud API support
- ✅ Worklog creation with time tracking
- ✅ Worklog listing with filters
- ✅ Worklog updates (time, date, comment) with automatic issue ID resolution
- ✅ Worklog deletion
- ✅ Tempo Accounts listing for billing
- ✅ Automatic connection detection
- ✅ Secure token storage
- ✅ Cross-instance workflow support (planning + booking Jira with Tempo)

**Connections without Tempo (native Jira worklogs):**

The `budjira tempo` commands work transparently on connections where Tempo is not
installed (Tempo: Disabled) by falling back to the native Jira worklog API:

- `budjira tempo log PROJ-123 2h --comment "..."` creates a native Jira worklog
- `budjira tempo worklogs PROJ-123` lists the issue's worklogs (only your own);
  without an issue key, a user-scoped search (`worklogAuthor = currentUser()`)
  covers your bookings — the range defaults to the current month when `--from`
  is not set
- `budjira tempo update-worklog 67890 --issue PROJ-123 --time-spent 3h` and
  `budjira tempo delete-worklog 67890 --issue PROJ-123` update/delete native
  worklogs — `--issue` is required there because native worklog IDs are
  per-issue (find them via `budjira worklog list PROJ-123`)

Tempo-only concepts (accounts, billing keys, attributes) do not apply to native
worklogs and are silently ignored; `--no-epic` and `--format json` work on both
backends.

**When to use Tempo vs. Standard Jira:**
- Use `budjira tempo` commands for time tracking — they use Tempo where available
  and native Jira worklogs everywhere else
- Use `budjira worklog` commands for standard Jira time tracking only
- Tempo integration is optional and requires a separate API token

### Cross-Instance Workflows

Workflow profiles connect a **planning** Jira (where issues live) with a **booking** Jira
(where time is logged via Tempo), linked through shadow tickets:

```bash
# Create a profile interactively (planning/booking connection, project mappings,
# shadow strategy, overbooking policy)
budjira workflow setup

# Estimate vs. booked for a planning issue
budjira workflow status EK-123 --profile ek-to-k

# Book time on the shadow ticket (resolves shadow, checks overbooking)
budjira workflow book EK-123 2h --profile ek-to-k --comment "Development"

# Sprint booking overview across both instances
budjira workflow sprint --profile ek-to-k

# Manage profiles
budjira workflow list
budjira workflow show ek-to-k
budjira workflow remove ek-to-k
```

### Workflow Billing Reports

For cross-instance workflow profiles (planning + booking), `budjira workflow billing`
answers the monthly question: how much of the booked time is billable, how much is
covered by a retainer or warranty? The mapping from issue labels to billing buckets
is configuration, not code — an optional `billing` block in the workflow profile:

```toml
[[profiles]]
name = "acme-shadow"
planning_connection = "acme-planning"
booking_connection  = "acme-booking"
project_mappings = [{ planning_project = "PLAN", booking_project = "BOOK" }]

[profiles.billing]
# label -> bucket; buckets are free-form, the report groups by them
categories = { analysis = "billable", warranty = "non-billable", onboarding = "project" }

require_exactly_one = true        # fail loudly on issues with several category labels
exclude_from_total = ["project"]  # shown in the report, but outside the grand total
chargeable_buckets = ["billable"] # only these get amounts and feed the money total
# rate = 95                       # optional; absent or 0 => hours-only report
# currency = "EUR"
```

With a rate set, amounts and the `Chargeable:` money total cover only the
chargeable buckets — non-chargeable buckets render hours-only. The report never
sums a single currency figure across buckets with different billing semantics,
so the money total cannot be mistaken for an invoice it is not.

```bash
# Monthly report (defaults to the current month)
budjira workflow billing --profile acme-shadow --month 2026-08

# Custom period, grouping and filtering
budjira workflow billing --profile acme-shadow --from 2026-08-01 --to 2026-09-30
budjira workflow billing --profile acme-shadow --group category
budjira workflow billing --profile acme-shadow --bucket billable

# Label hygiene check (exit code 1 on violations — CI/agent friendly)
budjira workflow billing --profile acme-shadow --validate

# Machine-readable output (same data, deterministic schema)
budjira --format json workflow billing --profile acme-shadow --month 2026-08
```

Issues without a category label appear in an explicit `uncategorised` bucket, so
booked time is never silently dropped from the total.

**Scope:** the report covers exactly the profile's mapped booking projects. Bookings
on other projects of the same Tempo instance — e.g. legacy collection tickets without
a planning twin — are out of scope by design, so totals can legitimately differ from
tools that read a wider scope.

### JSON Output Format

budjira supports JSON output for automation and integration with other tools (e.g., reporting systems, data analysis).

**Usage:**

```bash
# Global --format flag (works with all list-based commands)
budjira --format json tempo worklogs --from 2025-10-01 --to 2025-10-31

# Output to file for processing
budjira --format json tempo worklogs PROJ-123 > worklogs.json

# Pipe to jq for analysis
budjira --format json tempo worklogs --from 2025-10-01 | jq '.worklogs[].time_spent_seconds' | jq -s add
```

**Example JSON Output:**

```json
{
  "total": 2,
  "worklogs": [
    {
      "id": 619,
      "issue_key": "PRD-1",
      "epic_key": "PRD-1",
      "epic_name": "budjira Development",
      "time_spent_seconds": 900,
      "time_spent_display": "15m",
      "date": "2025-10-26",
      "author_account_id": "712020:5...",
      "author_display_name": "Fred Thiele",
      "description": "Testing budjira Tempo integration"
    }
  ]
}
```

**Features:**
- ✅ Machine-readable JSON output
- ✅ Epic information included (epic_key, epic_name)
- ✅ Performance mode with `--no-epic` flag
- ✅ Works with all list-based commands
- ✅ Pipes and redirection friendly

**Performance Note:**
Epic information requires additional Jira API calls. Use `--no-epic` for faster output:

```bash
budjira --format json tempo worklogs --no-epic
```

## 🔧 Configuration

budjira follows the XDG Base Directory specification and stores configuration in:

```
~/.config/budjira/
├── connections.toml      # Connection definitions
├── credentials/          # Secure credential storage
├── dor-templates.toml   # Definition of Ready templates
├── cache/               # Optional issue cache
├── logs/                # Per-context log files
└── config.toml          # Global settings
```

## 🚧 Coming Soon

The following features are currently in development:

### Additional Planned Features

- **Comment Management**: List, edit, and delete comments (add already available)
- **Attachment Support**: Upload and download attachments
- **Sprint Management**: View and manage sprints
- **Dashboard Commands**: View personalized dashboards

## 🎯 Use Cases

### For Developers

- **Quick Ticket Lookup**: Search and view issues without opening a browser
- **Time Logging**: Track time spent on tasks directly from terminal
- **Workflow Integration**: Integrate Jira operations into shell scripts and CI/CD pipelines

### For AI-Assisted Project Management

- **Synchronization Bridge**: Keep project documentation and Jira in sync
- **Automated Updates**: Let AI assistants update Jira based on local project changes
- **Quality Checks**: Validate that Jira accurately represents project state
- **Batch Operations**: Process multiple issues efficiently via scripts

## 🤝 Contributing

Contributions are welcome! Please check out our [contributing guidelines](CONTRIBUTING.md) (coming soon).

### Development Setup

```bash
# Clone the repository
git clone https://github.com/cdds-ab/budjira.git
cd budjira

# Install dependencies with development extras
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy budjira
```

### Code Quality

budjira maintains high code quality standards:

- ✅ **Ruff**: Fast linting and formatting
- ✅ **MyPy**: Strict type checking
- ✅ **Bandit**: Security vulnerability scanning
- ✅ **70% minimum test coverage**: Enforced by pre-commit hooks
- ✅ **CI/Pre-commit Consistency**: Single source of truth via pre-commit action
- ✅ **Conventional Commits**: Semantic versioning via commit messages

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Comprehensive development guide
- [API Documentation](https://github.com/cdds-ab/budjira/wiki) (coming soon)
- [Examples](https://github.com/cdds-ab/budjira/tree/main/examples) (coming soon)

## 🔐 Security

**⚠️ IMPORTANT: This repository is PUBLIC.**

### For Users
- Credentials are stored securely using system keyring where available
- API tokens are never logged or displayed in output
- Security scanning via Bandit in CI/CD pipeline
- Regular dependency updates via Dependabot

### For Contributors
**Automatic Issue Data Sanitization** (GitHub Action):
- All issues are automatically scanned for sensitive data (emails, customer names, URLs)
- Warnings posted immediately if patterns detected
- Always use dummy data in issues: `user@example.com`, `acme-corp`, `company.atlassian.net`
- Review PR diffs before submitting to ensure no sensitive information

If you find sensitive data in existing issues, please report it immediately or submit a PR to anonymize it.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI magic
- Powered by [jira-python](https://github.com/pycontribs/jira) for Jira integration
- Fast package management by [uv](https://github.com/astral-sh/uv)
- Beautiful output via [Rich](https://github.com/Textualize/rich)

## 🐛 Issues & Support

Found a bug? Have a feature request?

- [Open an issue](https://github.com/cdds-ab/budjira/issues)
- Check [existing issues](https://github.com/cdds-ab/budjira/issues?q=is%3Aissue)

## 🗺️ Roadmap

### Implemented ✅
- [x] Multi-connection management
- [x] Secure credential storage
- [x] Issue search (JQL and filters)
- [x] Issue creation (interactive and non-interactive)
- [x] Definition of Ready (DoR) templates with validation
- [x] Issue updates (status transitions, fields, labels)
- [x] Epic linking and management
- [x] Time tracking (worklogs, time estimates)
- [x] Self-update mechanism
- [x] Automatic update checks
- [x] AI usage prompt generation

### Planned 📋
- [ ] E2E Testing with Atlassian Developer Cloud (see [#6](https://github.com/cdds-ab/budjira/issues/6))
- [ ] Smart caching with dirty detection
- [ ] Comment list/edit/delete (add already available)
- [ ] Attachment upload/download
- [ ] Offline mode
- [ ] Sprint management
- [ ] Dashboard/reporting commands
- [ ] Interactive issue editing
- [ ] Shell completion enhancements
- [ ] Configuration templates
- [ ] Bulk operations

---

Made with ❤️ by [cdds-ab](https://github.com/cdds-ab)
