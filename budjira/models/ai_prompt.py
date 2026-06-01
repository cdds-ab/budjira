"""AI usage prompt template models.

This module provides models for managing the AI usage prompt as a structured,
editable template rather than a hardcoded string. Follows the pattern established
by the DoR template system.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiPromptSection(BaseModel):
    """Single section of the AI usage prompt."""

    title: str = Field(
        description="Section title (displayed as markdown heading)",
    )
    content: str = Field(
        description="Markdown content of the section",
    )
    order: int | float = Field(
        description="Display order (0-99, lower numbers appear first, supports decimals for fine-grained ordering)",
    )
    enabled: bool = Field(
        default=True,
        description="Whether to include this section in the rendered output",
    )


class AiPromptTemplate(BaseModel):
    """Complete AI usage prompt template."""

    version: str = Field(
        default="1.0",
        description="Template version for migration tracking",
    )
    sections: list[AiPromptSection] = Field(
        default_factory=list,
        description="List of prompt sections",
    )

    def render(self) -> str:
        """Render enabled sections to complete markdown prompt.

        Filters out disabled sections and sorts by order field before combining.

        Returns:
            Complete markdown prompt ready for AI consumption
        """
        enabled_sections = [s for s in self.sections if s.enabled]
        sorted_sections = sorted(enabled_sections, key=lambda s: s.order)
        return "\n\n".join(s.content for s in sorted_sections)

    def get_section(self, title: str) -> AiPromptSection | None:
        """Get a section by title.

        Args:
            title: Section title to search for

        Returns:
            Section if found, None otherwise
        """
        for section in self.sections:
            if section.title == title:
                return section
        return None

    def add_section(self, section: AiPromptSection) -> None:
        """Add or update a section.

        If a section with the same title exists, it will be replaced.

        Args:
            section: Section to add/update
        """
        # Remove existing section with same title if present
        self.sections = [s for s in self.sections if s.title != section.title]
        self.sections.append(section)

    def remove_section(self, title: str) -> bool:
        """Remove a section by title.

        Args:
            title: Title of section to remove

        Returns:
            True if section was removed, False if not found
        """
        original_count = len(self.sections)
        self.sections = [s for s in self.sections if s.title != title]
        return len(self.sections) < original_count


def get_default_ai_prompt_template() -> AiPromptTemplate:
    """Get the default AI usage prompt template.

    This template is extracted from the original 1100-line hardcoded string
    in budjira/cli/ai.py to enable user customization.

    Returns:
        Default template with all 21 sections from the original prompt
    """
    sections = [
        AiPromptSection(
            title="Header and Overview",
            content="""# budjira - Jira CLI Tool Usage Guide for AI Assistants

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
- Sprint querying (list sprints, view sprint contents with filters)
- Cross-instance workflow profiles (shadow ticket resolution, overbooking checks)
- Rich terminal output with tables and colors""",
            order=0,
            enabled=True,
        ),
        AiPromptSection(
            title="Connection Management",
            content="""## Connection Management

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
```""",
            order=1,
            enabled=True,
        ),
        AiPromptSection(
            title="Custom Fields Configuration",
            content="""## Custom Fields Configuration

**NEW in v1.13.0** - Configure connection-level custom fields for issue creation.

### Configuration

Custom fields are configured in `~/.config/budjira/connections.toml` under each connection:

```toml
[[connections]]
name = "my-project"
url = "https://company.atlassian.net"
email = "user@example.com"
project_key = "PROJ"

# Custom field configuration
[connections.custom_fields.affected_system]
field_id = "customfield_10001"       # Jira field ID (required)
type = "select"                       # Field type (see below)
required = true                       # Prompt if not provided
options = ["Infrastructure", "Application", "Database"]
label = "Affected System"             # Display name

[connections.custom_fields.environment]
field_id = "customfield_10002"
type = "multi_select"
options = ["Dev", "Staging", "Prod"]
label = "Environment"

[connections.custom_fields.story_points]
field_id = "customfield_10003"
type = "number"
default = "3"
label = "Story Points"
```

### Field Types

| Type | Description | Jira API Format |
|------|-------------|-----------------|
| `text` | Plain text (default) | `"value"` |
| `select` | Single select dropdown | `{"value": "Option"}` |
| `multi_select` | Multi-select (comma-separated) | `[{"value": "A"}, {"value": "B"}]` |
| `user` | User picker | `{"accountId": "..."}` |
| `date` | Date field | `"YYYY-MM-DD"` |
| `number` | Numeric value | `42` or `3.14` |

### Finding Jira Field IDs

1. **Via Jira REST API:**
   ```bash
   curl -u email:token "https://company.atlassian.net/rest/api/3/field" | jq '.[] | select(.custom) | {id, name}'
   ```

2. **Via Jira UI:** Open issue → click field → check URL for `customfield_XXXXX`

### Usage

```bash
# Single custom field
budjira create issue "Bug title" --custom affected_system=Infrastructure

# Multiple custom fields
budjira create issue "Feature" --custom affected_system=Application --custom environment="Dev, Staging"

# Interactive mode prompts for required fields automatically
budjira create issue "Title"
# Prompts: "Affected System (Infrastructure, Application, Database):"
```

### Validation

- **Options validation**: Select/multi-select values are validated against configured options
- **Required fields**: Must be provided via --custom or interactively
- **Number validation**: Numeric fields validate that input is a valid number""",
            order=2,
            enabled=True,
        ),
        AiPromptSection(
            title="Connection-Specific AI Prompts",
            content="""## Connection-Specific AI Prompts

**NEW in v1.13.0** - Add project-specific instructions to the generated AI usage prompt.

### Configuration

Add an `ai_prompt` field to your connection in `~/.config/budjira/connections.toml`:

```toml
[[connections]]
name = "my-project"
url = "https://company.atlassian.net"
email = "user@example.com"
project_key = "PROJ"

# Project-specific AI prompt (multiline supported)
ai_prompt = \"\"\"
## Project Workflow

**Issue Types:**
- Change: For planned modifications
- Service Request: For user requests
- Incident: For production issues

**Required Custom Fields:**
- affected_system: Always set for bugs
- environment: Required for deployments

**Naming Conventions:**
- Bugs: "BUG: <component> - <description>"
- Features: "FEAT: <area> - <description>"
\"\"\"
```

### Usage

Generate the AI usage prompt with project-specific additions:

```bash
# Include project-specific prompt
budjira ai usage-prompt --connection my-project

# Output to file for AI assistant
budjira ai usage-prompt --connection my-project --plain > .claude/ai-usage-prompt.md

# View formatted in terminal
budjira ai usage-prompt --connection my-project
```

The project-specific prompt is appended after the standard budjira documentation.""",
            order=3,
            enabled=True,
        ),
        AiPromptSection(
            title="Searching Issues",
            content="""## Searching Issues

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
- Updated date""",
            order=4,
            enabled=True,
        ),
        AiPromptSection(
            title="Viewing Issue Details",
            content="""## Viewing Issue Details

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
- Understand issue context before making changes""",
            order=5,
            enabled=True,
        ),
        AiPromptSection(
            title="Creating Issues",
            content="""## Creating Issues

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
- `--epic KEY`: Link to epic during creation
- `--parent KEY`: Parent issue key for sub-tasks (required when the type is a sub-task)
- `--custom NAME=VALUE`: Set custom field (repeatable, requires configuration)

**Sub-tasks:** Use `--parent PROJ-123` to create a sub-task under a parent issue.
The sub-task type name varies per instance (often `Subtask`, sometimes `Sub-task`);
budjira detects sub-task types via cached project metadata (`budjira project show`)
and fails fast with a clear message if a sub-task is created without `--parent`.

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

# Sub-task under a parent issue (Epic > Story > Sub-task workflows)
budjira create issue "Implement login form" \\
  --type Subtask \\
  --parent PROJ-123 \\
  --no-interactive

# With custom fields (requires configuration in connections.toml)
budjira create issue "Production bug" \\
  --type Bug \\
  --custom affected_system=Infrastructure \\
  --custom environment=Prod \\
  --no-interactive

# Link to epic with custom fields
budjira create issue "New feature" \\
  --type Story \\
  --epic PROJ-100 \\
  --custom story_points=5 \\
  --no-interactive
```""",
            order=6,
            enabled=True,
        ),
        AiPromptSection(
            title="Definition of Ready (DoR) Templates",
            content="""## Definition of Ready (DoR) Templates

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
- Customizable per issue type""",
            order=7,
            enabled=True,
        ),
        AiPromptSection(
            title="Updating Issues",
            content="""## Updating Issues

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

### Delete Issue

```bash
budjira issue delete ISSUE-KEY [OPTIONS]
```

Permanently delete a Jira issue. This action cannot be undone.

**Options:**
- `--force`, `-f`: Skip confirmation prompt
- `--delete-subtasks`: Also delete subtasks of the issue
- `--connection NAME`, `-c`: Use specific connection

**Examples:**

```bash
# Delete issue with confirmation prompt
budjira issue delete PROJ-123

# Delete without confirmation (for automation)
budjira issue delete PROJ-123 --force

# Delete issue and all its subtasks
budjira issue delete PROJ-123 --delete-subtasks

# Delete with force and subtasks
budjira issue delete PROJ-123 --force --delete-subtasks
```

**Note:** Deleting an issue requires the 'Delete Issues' permission in Jira. The confirmation prompt shows the issue summary before deletion.

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

**Note:** Status transitions are case-insensitive, so "in progress", "In Progress", and "IN PROGRESS" all work.""",
            order=8,
            enabled=True,
        ),
        AiPromptSection(
            title="Issue Linking",
            content="""## Issue Linking

### Create Issue Links

```bash
budjira issue link ISSUE-KEY [OPTIONS]
```

Create relationships between issues to express dependencies, related work, or duplicates.

**Options:**
- `--relates-to ISSUE-KEY`: Generic relationship
- `--blocks ISSUE-KEY`: This issue blocks another issue
- `--is-blocked-by ISSUE-KEY`: This issue is blocked by another issue
- `--clones ISSUE-KEY`: This issue clones another issue
- `--is-cloned-by ISSUE-KEY`: This issue is cloned by another issue
- `--duplicates ISSUE-KEY`: This issue duplicates another issue
- `--is-duplicated-by ISSUE-KEY`: This issue is duplicated by another issue

**Examples:**

```bash
# Link two issues with a relationship
budjira issue link PROJ-123 --relates-to PROJ-456

# Express blocking relationships
budjira issue link PROJ-123 --blocks PROJ-456
budjira issue link PROJ-123 --is-blocked-by PROJ-789

# Mark duplicates
budjira issue link PROJ-123 --duplicates PROJ-100

# Create multiple links in one command
budjira issue link PROJ-123 --relates-to PROJ-456 --relates-to PROJ-789
budjira issue link PROJ-123 --relates-to PROJ-200 --blocks PROJ-300
```

### View Issue Links

Links are displayed in the issue detail view:

```bash
budjira show PROJ-123
```

**Output includes link table:**
```
🔗 Issue Links (2)
┌─────────┬───────────┬──────────┬─────────────────────┐
│ Type    │ Direction │ Issue    │ Summary             │
├─────────┼───────────┼──────────┼─────────────────────┤
│ Relates │ outward   │ PROJ-456 │ Related feature     │
│ Blocks  │ inward    │ PROJ-789 │ Dependent task      │
└─────────┴───────────┴──────────┴─────────────────────┘
```

**Use Cases:**
- **Dependency Tracking**: Express which issues block others
- **Related Work**: Link issues that are related but not dependent
- **Duplicate Management**: Mark duplicate issues
- **Impact Analysis**: Understand issue relationships for planning""",
            order=8.5,
            enabled=True,
        ),
        AiPromptSection(
            title="Epic Management",
            content="""## Epic Management

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
```""",
            order=9,
            enabled=True,
        ),
        AiPromptSection(
            title="Adding Comments",
            content="""## Adding Comments

### Add Comment to Issue

```bash
budjira comment add ISSUE-KEY [TEXT] [OPTIONS]
```

Add comments to Jira issues without logging time (unlike worklogs which combine comments with time tracking).

**Options:**
- `--editor`, `-e`: Open editor for multi-line comment
- `--connection NAME`, `-c`: Use specific connection

**Behavior:**
- If TEXT is omitted, editor opens automatically
- If TEXT is provided with `--editor`, editor opens with TEXT as initial content
- Supports markdown formatting
- Comments are posted immediately without time tracking

**Examples:**

```bash
# Quick single-line comment
budjira comment add PROJ-123 "Deployed to production environment"

# Multi-line comment via editor
budjira comment add PROJ-123 --editor

# Editor opens automatically if no text provided
budjira comment add PROJ-123

# Edit initial text in editor
budjira comment add PROJ-456 "Initial text" --editor

# Use specific connection
budjira comment add PROJ-789 "Status update" --connection prod-jira
```

**Use Cases:**
- Status updates without time tracking
- Analysis results and findings
- Documentation links
- Deployment notifications
- Code review feedback
- VM provisioning completion details

**Editor Support:**
- Opens `$EDITOR` environment variable (defaults to vim)
- Supports markdown formatting for rich text
- Multi-line content for detailed updates
- Empty content (whitespace only) aborts comment creation""",
            order=10,
            enabled=True,
        ),
        AiPromptSection(
            title="Time Tracking",
            content="""## Time Tracking

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
- Worklog ID
- Author
- Time spent
- Started date/time
- Comment (if any)

**Example:**
```bash
budjira worklog list PROJ-123
# Shows table with ID, author, time, started, comment
```

### Delete Worklog Entry

```bash
budjira worklog delete ISSUE-KEY WORKLOG_ID [OPTIONS]
```

Delete a native Jira worklog entry by its ID. Use `budjira worklog list` to find worklog IDs.

**Options:**
- `--force`, `-f`: Skip confirmation prompt
- `--connection`, `-c`: Connection to use

**Examples:**
```bash
# Delete with confirmation (shows worklog details first)
budjira worklog delete PROJ-123 12345

# Delete without confirmation
budjira worklog delete PROJ-123 12345 --force
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
```""",
            order=11,
            enabled=True,
        ),
        AiPromptSection(
            title="Tempo Timesheets Integration",
            content="""## Tempo Timesheets Integration

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
- **Automatic ID resolution**: If Tempo returns a worklog without a valid issue ID, budjira resolves it from the Jira API automatically

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
- Account ID""",
            order=12,
            enabled=True,
        ),
        AiPromptSection(
            title="Workflow Profiles (Cross-Instance)",
            content="""## Workflow Profiles (Cross-Instance)

**NEW in v1.16.0** - Automate cross-instance workflows between a planning Jira and a booking Jira (Tempo-enabled).

### Concept

Workflow profiles connect two Jira instances:
- **Planning instance**: Where issues are planned and estimated (e.g., "EK" project)
- **Booking instance**: Where time is logged via Tempo (e.g., "K" project with shadow tickets)

Shadow tickets in the booking instance mirror planning tickets (e.g., EK-123 has a shadow K-456 with "EK-123" in its summary).

**Cross-instance ID resolution** (v1.19.0): Issue IDs are always resolved from the booking Jira instance to ensure Tempo API calls use the correct internal ID. Mismatches between Tempo-stored and Jira-resolved IDs are logged as warnings.

### Setup a Workflow Profile

```bash
budjira workflow setup
```

Interactive setup prompts for:
- Profile name (e.g., "ek-to-k")
- Planning connection name
- Booking connection name (must have Tempo enabled)
- Project mappings (e.g., EK -> K)
- Shadow resolution strategy (default: summary search)
- Overbooking policy (warn, confirm, or block)

### Manage Profiles

```bash
# List all profiles
budjira workflow list

# Show profile details
budjira workflow show ek-to-k

# Remove profile
budjira workflow remove ek-to-k
```

### Check Booking Status

```bash
budjira workflow status EK-123 --profile ek-to-k
```

Shows estimate (from planning) vs spent time (from booking/Tempo):
- Planning issue summary and connection
- Shadow ticket in booking instance
- Estimate, spent, remaining time
- Progress bar with percentage
- Overbooking warning if applicable

If the shadow ticket has not been synced yet, a helpful message is shown instead of an error.

### Book Time via Workflow

```bash
budjira workflow book EK-123 2h --profile ek-to-k
budjira workflow book EK-123 2h30m --profile ek-to-k --comment "Analysis work"
budjira workflow book EK-123 3h --profile ek-to-k --started yesterday
```

Automated flow:
1. Resolves shadow ticket in booking instance (EK-123 -> K-456)
2. Fetches estimate from planning issue
3. Checks current Tempo spent on shadow ticket
4. Applies overbooking policy (warn/confirm/block)
5. Logs time to shadow ticket via Tempo

**Overbooking Policies:**
- `warn`: Show warning but continue booking (default)
- `confirm`: Ask for confirmation before booking
- `block`: Refuse to book if estimate would be exceeded

**If no estimate is set on the planning issue, overbooking checks are skipped.**

### Configuration

Profiles are stored in `~/.config/budjira/workflows.toml`:

```toml
[[profiles]]
name = "ek-to-k"
planning_connection = "ek-planning"
booking_connection = "k-booking"
shadow_strategy = "summary"
overbooking_policy = "warn"

[[profiles.project_mappings]]
planning_project = "EK"
booking_project = "K"
```

### JSON Output

All workflow commands support `--format json`:

```bash
budjira --format json workflow list
budjira --format json workflow show ek-to-k
budjira --format json workflow status EK-123 --profile ek-to-k
```""",
            order=12.5,
            enabled=True,
        ),
        AiPromptSection(
            title="Sprint Querying",
            content="""## Sprint Querying

**NEW in v1.17.0** - Query sprints and sprint contents from Scrum boards.

### List Sprints

```bash
budjira sprint list [OPTIONS]
```

Show all sprints for a board, optionally filtered by state.

**Options:**
- `--state STATE`, `-s`: Filter by state (active, future, closed)
- `--board ID`, `-b`: Board ID (auto-detected from project if not provided)
- `--connection NAME`, `-c`: Use specific connection

**Examples:**

```bash
# List all sprints (auto-detects board)
budjira sprint list

# List only active sprints
budjira sprint list --state active

# Use specific board
budjira sprint list --board 42

# JSON output
budjira --format json sprint list
```

### Show Sprint Contents

```bash
budjira sprint show [SPRINT_NAME] [OPTIONS]
```

Display issues in a sprint. Defaults to the active sprint if no name given.

**Options:**
- `--mine`, `-m`: Show only issues assigned to me
- `--status STATUS`: Filter by issue status (e.g., "In Progress")
- `--type TYPE`, `-t`: Filter by issue type (e.g., Story, Bug)
- `--board ID`, `-b`: Board ID (auto-detected if not provided)
- `--connection NAME`, `-c`: Use specific connection

**Examples:**

```bash
# Show active sprint contents
budjira sprint show

# Show only my issues in active sprint
budjira sprint show --mine

# Show specific sprint
budjira sprint show "Sprint 42"

# Filter by status and type
budjira sprint show --status "In Progress" --type Bug

# JSON output
budjira --format json sprint show
```

**Output includes:**
- Sprint header with name, state, and dates
- Table of issues with: Key, Type, Status, Priority, Summary, Assignee

### Sprint Management (Write Operations)

Move issues into sprints and manage the sprint lifecycle. Lifecycle and
delete operations require Jira board-admin permissions; a 403 is reported as
a permission error.

```bash
# Move one or more issues into a sprint (by name or ID)
budjira sprint move ISSUE-KEY [ISSUE-KEY ...] --to "Sprint 42"
budjira sprint move PROJ-1 PROJ-2 --sprint-id 100

# Create a new (future) sprint; dates are optional
budjira sprint create "Sprint 43"
budjira sprint create "Sprint 43" --start today --end 2026-06-14 --goal "Ship the API"

# Start a sprint (-> active); Jira requires start+end dates
budjira sprint start "Sprint 43" --start today --end 2026-06-14
budjira sprint start --sprint-id 100 --force

# Close a sprint (-> closed); defaults to the active sprint
budjira sprint close
budjira sprint close "Sprint 42" --force
```

**Key points:**
- `move` is additive and needs no confirmation. Target via `--to NAME` or `--sprint-id ID` (one is required).
- `start`/`close` prompt for confirmation; use `--force`/`-f` to skip. In JSON mode `--force` is mandatory.
- Sprint dates accept ISO (`2026-06-14`), `today`, `tomorrow`, or `yesterday`.
- All commands support `--board`, `--connection`, and `--format json`.

### Board Configuration

The board is resolved in this order:
1. `--board` CLI flag (highest priority)
2. `board_id` from connection config (set in connections.toml)
3. Auto-detection from project (works when exactly one sprint-capable board exists)

Both company-managed (board type `scrum`) and team-managed (board type `simple`)
projects are supported. For team-managed projects, passing `--sprint-id`
directly to `sprint move/start/close` skips board detection entirely and
operates on the sprint via the agile API.

To configure a default board in `connections.toml`:
```toml
[[connections]]
name = "my-project"
board_id = 42
```

### Sprint Booking Overview (Workflow)

```bash
budjira workflow sprint [SPRINT_NAME] --profile PROFILE [OPTIONS]
```

Cross-instance sprint overview showing booking status for each issue.

**Options:**
- `--profile NAME`, `-p`: Workflow profile to use (required)
- `--board ID`, `-b`: Board ID on planning instance
- `--unbooked`, `-u`: Show only unbooked or partially booked issues
- `--mine`, `-m`: Show only issues assigned to me

**Examples:**

```bash
# Show sprint booking overview
budjira workflow sprint --profile ek-to-k

# Show only unbooked issues
budjira workflow sprint --profile ek-to-k --unbooked

# Show specific sprint
budjira workflow sprint "Sprint 42" --profile ek-to-k --mine

# JSON output for reporting
budjira --format json workflow sprint --profile ek-to-k
```

**Output includes:**
- Planning key and shadow ticket mapping
- Estimate vs spent time per issue
- Remaining time or overbooking indicator
- Summary row with total spent / total estimate (percentage)""",
            order=12.7,
            enabled=True,
        ),
        AiPromptSection(
            title="Update Management",
            content="""## Update Management

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
```""",
            order=13,
            enabled=True,
        ),
        AiPromptSection(
            title="Shell Completion",
            content="""## Shell Completion

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
```""",
            order=14,
            enabled=True,
        ),
        AiPromptSection(
            title="Global Options",
            content="""## Global Options

Available on all commands:

- `--quiet`, `-q`: Suppress header output (useful for scripts)
- `--debug`, `-d`: Enable debug output
- `--version`, `-v`: Show version and exit
- `--help`, `-h`: Show help message""",
            order=15,
            enabled=True,
        ),
        AiPromptSection(
            title="Common Workflows for AI Assistants",
            content="""## Common Workflows for AI Assistants

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

# 5. View all logged time (shows worklog IDs)
budjira worklog list PROJ-456

# 5b. Delete wrong worklog entry
budjira worklog delete PROJ-456 12345 --force

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

### 13. Cross-Instance Workflow (Planning + Booking)

```bash
# 1. Setup workflow profile (one-time)
budjira workflow setup

# 2. Check booking status before starting work
budjira workflow status EK-123 --profile ek-to-k

# 3. Book time to shadow ticket via workflow
budjira workflow book EK-123 2h --profile ek-to-k --comment "Development work"

# 4. Book time from yesterday
budjira workflow book EK-456 3h30m --profile ek-to-k --started yesterday

# 5. Check updated status after booking
budjira workflow status EK-123 --profile ek-to-k

# 6. List all workflow profiles
budjira workflow list

# 7. JSON output for reporting
budjira --format json workflow status EK-123 --profile ek-to-k
```

### 14. Sprint Query Workflow

```bash
# 1. List available sprints
budjira sprint list --state active

# 2. View active sprint contents
budjira sprint show

# 3. Show only my issues in active sprint
budjira sprint show --mine

# 4. Show specific sprint filtered by status
budjira sprint show "Sprint 42" --status "In Progress"

# 5. Cross-instance sprint booking overview
budjira workflow sprint --profile ek-to-k

# 6. Show only unbooked sprint items
budjira workflow sprint --profile ek-to-k --unbooked --mine

# 7. JSON output for reporting
budjira --format json sprint show
```""",
            order=16,
            enabled=True,
        ),
        AiPromptSection(
            title="Error Handling",
            content="""## Error Handling

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
```""",
            order=17,
            enabled=True,
        ),
        AiPromptSection(
            title="Configuration Files",
            content="""## Configuration Files

Located in `~/.config/budjira/`:

- `connections.toml` - Connection definitions
- `credentials/` - Secure credential storage (mode 0o600)
- `config.toml` - Global settings
- `cache/` - Optional issue cache (future feature)
- `logs/` - Per-context log files""",
            order=18,
            enabled=True,
        ),
        AiPromptSection(
            title="Tips for AI Assistants",
            content="""## Tips for AI Assistants

1. **Always check connection first**: Use `budjira connect current` to verify setup
2. **Use filters over JQL**: More user-friendly for simple queries
3. **Interactive mode for missing details**: Use interactive create when user hasn't provided all info
4. **Non-interactive for automation**: Use `--no-interactive` when all details are available
5. **Respect quiet mode**: Add `-q` flag when parsing output programmatically
6. **Connection override**: Use `--connection NAME` when user has multiple Jira instances
7. **Custom fields**: Check connection config for required custom fields before creating issues
8. **Project-specific prompts**: Use `budjira ai usage-prompt --connection NAME` for project-specific guidance
9. **Sprint overview**: Use `budjira sprint show --mine` to quickly see user's current sprint work
10. **Cross-instance sprint**: Use `budjira workflow sprint --profile NAME --unbooked` to find items needing time booking""",
            order=19,
            enabled=True,
        ),
        AiPromptSection(
            title="Version Information",
            content="""## Version Information

Current version can be checked with:
```bash
budjira --version
```

Update to latest:
```bash
budjira update
```""",
            order=20,
            enabled=True,
        ),
        AiPromptSection(
            title="Support and Documentation",
            content="""## Support and Documentation

- GitHub: https://github.com/cdds-ab/budjira
- Issues: https://github.com/cdds-ab/budjira/issues
- Releases: https://github.com/cdds-ab/budjira/releases""",
            order=21,
            enabled=True,
        ),
        AiPromptSection(
            title="Footer",
            content="""**This guide is generated by budjira itself and reflects the current feature set.**""",
            order=22,
            enabled=True,
        ),
    ]

    return AiPromptTemplate(version="1.0", sections=sections)
