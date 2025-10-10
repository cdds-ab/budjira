<div align="center">
  <img src="images/budjira_logo.jpg" alt="budjira - Your CLI Pal for Jira" width="600">

  # budjira

  **Your CLI Pal for Jira**

[![CI](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml/badge.svg)](https://github.com/cdds-ab/budjira/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/budjira.svg)](https://badge.fury.io/py/budjira)
[![Python versions](https://img.shields.io/pypi/pyversions/budjira.svg)](https://pypi.org/project/budjira/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

---

**budjira** (pronounced "buddy-ra") is your CLI buddy for Jira. It provides efficient, user-friendly command-line access to Jira Cloud with features designed for both developers and AI-assisted project management.

## ✨ Features

- 🔍 **Search & Filter**: Powerful JQL-based ticket search
- ✏️ **Create Issues**: Quick ticket creation with templates
- ⏱️ **Time Tracking**: Log work time directly from the command line
- 🔗 **Multi-Connection**: Manage multiple Jira instances and projects
- 🎯 **Context-Aware**: Project-root based connection management
- 📦 **Smart Caching**: Optional offline-capable caching (coming soon)
- 🤖 **AI-Friendly**: Designed for seamless AI-assisted workflows
- 🎨 **Rich Output**: Beautiful, colorful terminal output with tables and formatting

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

### 2. Search for Issues

```bash
# Search in default project
budjira search "status = Open"

# Advanced JQL query
budjira search "project = MYPROJ AND assignee = currentUser() AND status != Done"

# List all issues in a sprint
budjira search "sprint = 'Sprint 42'"
```

### 3. Create an Issue

```bash
# Interactive issue creation
budjira create

# Quick creation with flags
budjira create --summary "Fix login bug" --type Bug --priority High
```

### 4. Log Work Time

```bash
# Log time on an issue
budjira log-time PROJ-123 --time 2h --comment "Fixed authentication bug"

# Log time with start date
budjira log-time PROJ-123 --time 1h30m --started "2025-10-10 14:00"
```

### 5. View Logs

```bash
# Show recent logs
budjira logs

# Pipe to standard Unix tools
budjira logs | tail -50
budjira logs | grep ERROR
```

### 6. Check for Updates

```bash
# Update to latest version
budjira update
```

## 🔧 Configuration

budjira follows the XDG Base Directory specification and stores configuration in:

```
~/.config/budjira/
├── connections.toml      # Connection definitions
├── credentials/          # Secure credential storage
├── cache/               # Optional issue cache
├── logs/                # Per-context log files
└── config.toml          # Global settings
```

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

- [ ] Smart caching with dirty detection
- [ ] Interactive issue editing
- [ ] Issue transitions (move between states)
- [ ] Comment management
- [ ] Attachment upload/download
- [ ] Sprint management
- [ ] Dashboard/reporting commands
- [ ] Shell completion enhancements
- [ ] Configuration templates
- [ ] Bulk operations

---

Made with ❤️ by [cdds-ab](https://github.com/cdds-ab)
