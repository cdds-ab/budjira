<div align="center">
  <img src="images/budjira_logo.jpg" alt="budjira - Your CLI Pal for Jira" width="600">

  # budjira

  **Your CLI Pal for Jira**

[![CI](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml/badge.svg)](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

---

**budjira** (pronounced "buddy-ra") is your CLI buddy for Jira. It provides efficient, user-friendly command-line access to Jira Cloud with features designed for both developers and AI-assisted project management.

## ✨ Features

- 🔗 **Multi-Connection**: Manage multiple Jira instances and projects
- 🎯 **Context-Aware**: Name-based connection management with environment variable and CLI override support
- 🔄 **Auto-Update**: Automatic update checks with GitHub Releases integration
- 🤖 **AI-Friendly**: Designed for seamless AI-assisted workflows with built-in usage prompt generation
- 🎨 **Rich Output**: Beautiful, colorful terminal output with tables and formatting
- 🔍 **Search & Filter**: Powerful JQL-based ticket search with filter options
- ✏️ **Create Issues**: Interactive and non-interactive issue creation
- 📋 **Definition of Ready**: Customizable templates for Story, Bug, Task with validation
- 🔄 **Update Issues**: Transition status, update fields, manage labels
- 🎯 **Epic Management**: Link stories to epics and view epic progress
- ⏱️ **Time Tracking**: Comprehensive worklog management and time estimates
- 🎼 **Tempo Integration**: Full support for Tempo Timesheets API for enterprise time tracking
- 📦 **Smart Caching**: Optional offline-capable caching *(coming soon)*

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

### 4. Create Issues

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
```

### 5. Definition of Ready (DoR) Templates

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

### 6. Update Issues

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
```

### 7. View Epic Progress

```bash
# Show epic with all child stories
budjira epic show PROJ-100
```

### 9. Check for Updates

budjira automatically checks for updates every 24 hours and notifies you when a new version is available.

```bash
# Check for updates manually
budjira update --check

# Update to latest version (interactive)
budjira update

# Force update check (bypass cache)
budjira update --check --force
```

### 10. AI Integration

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

### 8. Time Tracking

budjira provides comprehensive time tracking capabilities including worklog management and time estimates.

```bash
# Add work log entry
budjira worklog add PROJ-123 2h --comment "Fixed authentication bug"
budjira worklog add PROJ-123 1h30m --comment "Code review"

# Log work with specific start time
budjira worklog add PROJ-123 3h --started "2024-10-24 14:00" --comment "Implemented feature"
budjira worklog add PROJ-123 2h --started "yesterday" --comment "Bug fixing"

# List all worklogs for an issue
budjira worklog list PROJ-123

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
- ISO format: `2024-10-25T14:30:00`, `2024-10-25 14:30`
- Date only: `2024-10-25` (time defaults to 00:00)
- Relative: `today`, `yesterday`

### 9. Tempo Timesheets Integration

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
budjira tempo log PROJ-123 2h --started "2024-10-24 14:00" --comment "Development"

# List Tempo worklogs
budjira tempo worklogs PROJ-123                    # For specific issue
budjira tempo worklogs --from 2024-10-01 --to 2024-10-31  # Date range
budjira tempo worklogs --max 50                    # Limit results

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
- ✅ Worklog deletion
- ✅ Tempo Accounts listing for billing
- ✅ Automatic connection detection
- ✅ Secure token storage

**When to use Tempo vs. Standard Jira:**
- Use `budjira tempo` commands when your organization uses Tempo for time tracking
- Use `budjira worklog` commands for standard Jira time tracking
- Tempo integration is optional and requires a separate API token

## 🚧 Coming Soon

The following features are currently in development:

### Additional Planned Features

- **Issue Transitions**: Move issues between workflow states
- **Comment Management**: Add and view comments on issues
- **Attachment Support**: Upload and download attachments
- **Sprint Management**: View and manage sprints
- **Dashboard Commands**: View personalized dashboards
- **View Logs**: Access and filter application logs

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
- ✅ **Conventional Commits**: Semantic versioning via commit messages

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Comprehensive development guide
- [API Documentation](https://github.com/cdds-ab/budjira/wiki) (coming soon)
- [Examples](https://github.com/cdds-ab/budjira/tree/main/examples) (coming soon)

## 🔐 Security

- Credentials are stored securely using system keyring where available
- API tokens are never logged or displayed in output
- Security scanning via Bandit in CI/CD pipeline
- Regular dependency updates via Dependabot

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

### In Progress 🚧
- [ ] Smart caching with dirty detection

### Planned 📋
- [ ] Comment management
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
