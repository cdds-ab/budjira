# AI Prompt Supplements

This file contains manually curated sections for the AI usage prompt that cannot be auto-generated from the CLI structure.

**Purpose:** Keep AI guide comprehensive and up-to-date across code changes.

## Version Tracking

- **Last Updated:** 2025-10-12
- **Commands Covered:** connect, search, create, update, ai
- **Last Reviewed By:** Human developer

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

### Error Handling
1. **Connection errors**: Check network, credentials, and API token validity
2. **Invalid JQL**: Simplify query or use filters instead
3. **Missing project**: Verify project key exists and user has access
4. **Authentication failures**: Guide user to regenerate API token

### Output Parsing
1. **Use `-q` for programmatic access**: Suppress header when parsing output
2. **Parse table output**: Extract key, summary, status from search results
3. **Handle empty results**: Inform user when no issues match criteria

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
