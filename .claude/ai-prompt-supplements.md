# AI Prompt Supplements

This file contains manually curated sections for the AI usage prompt that cannot be auto-generated from the CLI structure.

**Purpose:** Keep AI guide comprehensive and up-to-date across code changes.

## Version Tracking

- **Last Updated:** 2025-10-26
- **Commands Covered:** connect, search, create, update, ai, tempo, JSON output
- **Last Reviewed By:** Human developer
- **Recent Changes:** Added JSON output format workflows (v1.7.0)

## Common Workflows for AI Assistants

### 1. Search for User's Open Issues
```bash
budjira search --assignee currentUser() --status "In Progress"
```

**When to use:**
- User asks "what am I working on?"
- Need to find user's current tasks
- Daily standup preparation

### 2. Create Issue from Conversation Context
```bash
# Interactive when details are unclear
budjira create issue "Summary from conversation"

# Non-interactive when all details are known
budjira create issue "Implement feature X" \
  --type Story \
  --description "Detailed requirements..." \
  --priority High \
  --label feature \
  --no-interactive
```

**When to use:**
- User describes a problem or feature request
- Converting conversation into actionable tickets
- Batch issue creation from requirements

### 3. Find Recent Activity in Project
```bash
budjira search "project = PROJ ORDER BY updated DESC" --max 20
```

**When to use:**
- User asks "what's new in project X?"
- Understanding recent project activity
- Finding recently updated issues

### 4. Search by Keywords/Text
```bash
budjira search "project = PROJ AND text ~ 'authentication'" --max 10
```

**When to use:**
- User mentions specific terms or keywords
- Finding related issues by content
- Searching descriptions and comments

### 5. Check Bugs Assigned to User
```bash
budjira search --type Bug --assignee currentUser() --status Open
```

**When to use:**
- Bug triage sessions
- Finding issues to fix
- Sprint planning

### 6. Tempo Time Tracking (Enterprise)
```bash
# Setup Tempo for connection
budjira connect tempo-setup

# Log work to Tempo
budjira tempo log PROJ-123 2h --comment "Development work"
budjira tempo log PROJ-456 3h30m --started yesterday --comment "Client meeting"

# View worklogs
budjira tempo worklogs PROJ-123
budjira tempo worklogs --from 2024-10-01 --to 2024-10-31

# List billing accounts
budjira tempo accounts
```

**When to use:**
- Organization uses Tempo Timesheets instead of standard Jira time tracking
- Need to track time against specific Tempo accounts for billing
- Enterprise time tracking with advanced reporting
- Tempo is installed in Jira instance

**Note:** Requires separate Tempo API token (different from Jira token)

### 7. Combined Issue + Time Tracking Workflow
```bash
# Standard Jira time tracking
budjira worklog add PROJ-123 2h --comment "Bug fixing"

# OR for Tempo users
budjira tempo log PROJ-123 2h --comment "Bug fixing"

# View logged time
budjira worklog list PROJ-123    # Standard Jira
budjira tempo worklogs PROJ-123   # Tempo
```

**When to use:**
- Daily time logging
- End of day time tracking
- Tracking time across multiple issues

### 8. JSON Output for Automation and Reporting
```bash
# Export Tempo worklogs to JSON
budjira --format json tempo worklogs --from 2025-10-01 --to 2025-10-31

# Export to file for processing
budjira -f json tempo worklogs --from 2025-10-01 --to 2025-10-31 > worklogs.json

# Pipe to jq for analysis
budjira --format json tempo worklogs --from 2025-10-01 | jq '.worklogs[].time_spent_seconds' | jq -s add

# Extract epic information
budjira -f json tempo worklogs PROJ-123 | jq '.worklogs[] | {issue: .issue_key, epic: .epic_name, time: .time_spent_display}'

# Performance mode (skip epic fetching)
budjira --format json tempo worklogs --from 2025-10-01 --no-epic
```

**When to use:**
- FoU (Forsknings- och utvecklingsavdrag) reporting for Swedish tax compliance
- Exporting time tracking data for analysis
- Integration with reporting tools or data pipelines
- Automation workflows that need machine-readable output
- Batch processing of worklog data

**Output structure:**
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

**Note:** Epic information requires additional Jira API calls. Use `--no-epic` for faster output when epic data is not needed.

## AI Assistant Tips

### Connection Management
1. **Always verify connection first**: Use `budjira connect current` to check active connection
2. **Handle multiple instances**: Use `--connection NAME` when user works with multiple Jira instances
3. **Guide token creation**: If connection fails, guide user to https://id.atlassian.com/manage-profile/security/api-tokens

### Search Strategies
1. **Prefer filters over JQL**: Use `--status`, `--assignee`, `--type` for simple queries
2. **Use JQL for complex queries**: When combining multiple conditions or using advanced operators
3. **Limit results sensibly**: Default to `--max 50` or less for better performance
4. **Order results**: Add `ORDER BY updated DESC` for recent issues first

### Issue Creation
1. **Interactive for missing details**: Use interactive mode when user hasn't provided all information
2. **Non-interactive for automation**: Use `--no-interactive` when all details are available from context
3. **Suggest reasonable defaults**: Based on conversation context (priority, type, labels)
4. **Validate before creation**: Confirm key details with user before creating issues

### Tempo Integration
1. **Check if Tempo is installed**: Ask user if their organization uses Tempo
2. **Separate tokens**: Tempo requires its own API token (different from Jira)
3. **Setup first**: Run `budjira connect tempo-setup` before using tempo commands
4. **Choose correct command**: Use `tempo` commands for Tempo, `worklog` for standard Jira
5. **Account awareness**: Tempo accounts are used for billing/project tracking

### Error Handling
1. **Connection errors**: Check network, credentials, and API token validity
2. **Invalid JQL**: Simplify query or use filters instead
3. **Missing project**: Verify project key exists and user has access
4. **Authentication failures**: Guide user to regenerate API token
5. **Tempo not enabled**: Run `budjira connect tempo-setup` if "Tempo is not enabled" error occurs
6. **Missing Tempo token**: Verify Tempo API token is configured correctly

### JSON Output
1. **Use `--format json` for automation**: Machine-readable output for scripts and pipelines
2. **Combine with jq**: Powerful JSON processing (e.g., `| jq '.worklogs[].time_spent_seconds'`)
3. **Epic performance**: Use `--no-epic` flag when epic data not needed (faster, fewer API calls)
4. **Banner suppression**: Banner/header automatically hidden in JSON mode
5. **Global flag**: `--format` applies to all list-based commands (future extensibility)
6. **Export workflows**: Redirect to file (`> output.json`) or pipe to other tools

### Output Parsing
1. **Use `-q` for programmatic access**: Suppress header when parsing output (table mode)
2. **Use `--format json` for structured data**: Machine-readable JSON for automation
3. **Parse table output**: Extract key, summary, status from search results
4. **Handle empty results**: Inform user when no issues match criteria

## Edge Cases and Gotchas

### Connection Resolution
- `--connection` flag overrides environment variable
- `BUDJIRA_CONNECTION` env var overrides config default
- Always show which connection is being used for clarity

### JQL Syntax
- Status names with spaces need quotes: `status = 'In Progress'`
- Use `currentUser()` for current user, not email address
- Text search uses `~` operator: `text ~ "keyword"`
- Date comparisons: `updated > "2025-01-01"`

### Issue Creation
- Some fields are project-specific (custom fields)
- Assignee can be username or account ID
- Labels cannot contain spaces (use hyphens instead)
- Description supports Jira formatting (not Markdown)

### Performance
- Large result sets can be slow (use `--max` to limit)
- Complex JQL queries may timeout
- Connection tests should be quick (< 2 seconds)

## Update Checklist

When CLI commands change, review and update:

- [ ] Workflows still work with new parameters
- [ ] Examples reflect current command syntax
- [ ] Tips address new features or changes
- [ ] Edge cases cover new functionality
- [ ] Version tracking updated

## Notes for Future Sessions

This file should be reviewed whenever:
- New CLI commands are added
- Existing commands get new parameters
- Command behavior changes significantly
- New use cases emerge from user feedback

The pre-commit hook will remind you when CLI files change.
