# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**budjira** (pronounced "buddy-ra") is a Python CLI tool that serves as a "Jira buddy" for developers and AI-assisted project management. It provides efficient, user-friendly command-line access to Jira Cloud instances with features like ticket search, creation, time logging, and intelligent caching.

**Key Use Cases:**
- Direct command-line interaction with Jira (search, create, time logging)
- AI-assisted project management bridge between local projects and Jira
- Multi-connection management for different projects/instances
- Offline-capable with intelligent caching

## Build and Development Commands

```bash
# Install dependencies (first time setup)
uv sync

# Run the CLI during development
uv run budjira --help

# Run linting and formatting
uv run ruff check .                # Check for issues
uv run ruff check --fix .          # Auto-fix issues
uv run ruff format .               # Format code

# Type checking
uv run mypy budjira

# Security scanning
uv run bandit -r budjira

# Run tests
uv run pytest                      # Run all tests
uv run pytest -v                   # Verbose output
uv run pytest tests/test_foo.py    # Run specific test file
uv run pytest -k "test_search"     # Run tests matching pattern

# Run tests with coverage
uv run pytest --cov=budjira --cov-report=term-missing
uv run pytest --cov=budjira --cov-report=html  # Generate HTML report

# Install pre-commit hooks (required for contributors)
uv run pre-commit install
uv run pre-commit run --all-files  # Run hooks manually

# Create a conventional commit
uv run cz commit                   # Interactive commit helper

# Build package
uv build                           # Creates wheel and sdist

# Check for outdated dependencies
uv pip list --outdated
```

## Architecture Overview

### Modular Structure

budjira follows a clean, modular architecture to maintain separation of concerns:

```
budjira/
├── cli/              # Command-line interface layer (Typer commands)
│   ├── __init__.py
│   ├── main.py       # Main CLI entry point and global flags
│   ├── connect.py    # Connection management commands
│   ├── search.py     # Issue search commands
│   ├── create.py     # Issue creation commands
│   ├── time.py       # Time logging commands
│   ├── logs.py       # Log viewing commands
│   └── update.py     # Self-update commands
├── core/             # Core business logic
│   ├── __init__.py
│   ├── jira_client.py    # Wrapper around jira library
│   ├── connection.py     # Connection/context management
│   └── cache.py          # Optional caching layer
├── config/           # Configuration management
│   ├── __init__.py
│   ├── settings.py       # Settings using pydantic-settings
│   └── credentials.py    # Secure credential handling
├── models/           # Pydantic data models
│   ├── __init__.py
│   ├── issue.py          # Issue models
│   ├── connection.py     # Connection models
│   └── config.py         # Configuration models
├── utils/            # Utilities
│   ├── __init__.py
│   ├── logging.py        # Logging configuration
│   ├── version.py        # Version checking and updates
│   └── errors.py         # Custom exceptions
└── __main__.py       # Entry point for `python -m budjira`
```

### Key Design Patterns

**1. Project-Root Identifier System:**
- Each connection is identified by a project root path (default: current directory)
- Supports multiple Jira instances/projects simultaneously
- Automatic duplicate detection

**2. Configuration Storage (XDG Standard):**
Uses `xdg-base-dirs` library for cross-platform configuration paths:
- `~/.config/budjira/connections.toml` - Connection definitions
- `~/.config/budjira/credentials/` - Per-project credentials
- `~/.config/budjira/cache/` - Optional issue cache (SQLite)
- `~/.config/budjira/logs/` - Rotating log files per context
- `~/.config/budjira/config.toml` - Global settings

**3. Jira Library Wrapper:**
- Wraps the `jira` library (pycontribs/jira) rather than reimplementing API calls
- Provides consistent error handling and logging
- Adds caching and retry logic

**4. Error Handling Strategy:**
All errors produce helpful, actionable messages in English:
- **Connection errors**: Check URL, credentials, network
- **Permission errors**: Explain required Jira permissions
- **User errors**: Suggest correct syntax/usage
- **API errors**: Parse and explain Jira error responses

### Core Components

**CLI Layer (Typer):**
- Type-safe command definitions using Python type hints
- Automatic help generation
- Rich output formatting with color and tables
- Global `--debug` flag for verbose logging

**Core Layer:**
- `JiraClient`: High-level interface to Jira API
- `ConnectionManager`: Handles multiple connections, context switching
- `CacheManager`: Optional SQLite-based caching with dirty detection

**Configuration Layer:**
- Pydantic models for type-safe configuration
- Secure credential storage (prefer system keyring)
- Environment variable support for CI/CD

**Utils Layer:**
- Structured logging to files (per-context)
- Version checking via PyPI JSON API (24h cache)
- Custom exception hierarchy

## Technology Stack

- **Package Manager**: `uv` (fast, modern, all-in-one)
- **CLI Framework**: `typer[all]` (type-safe, built on Click)
- **Jira Integration**: `jira` (pycontribs/jira, actively maintained)
- **Configuration**: `pydantic` + `pydantic-settings` + `xdg-base-dirs`
- **Rich Output**: `rich` (colors, tables, progress bars)
- **Testing**: `pytest` + `pytest-mock` (unit + mocked integration tests)
- **Linting**: `ruff` (replaces black, flake8, isort)
- **Type Checking**: `mypy` with strict settings
- **Security**: `bandit` (security vulnerability scanning)
- **Coverage**: `pytest-cov` (minimum 70% required)
- **Commits**: `commitizen` (conventional commits)
- **Releases**: `python-semantic-release` (automated versioning)

## Development Guidelines

### Code Style

**All code and documentation must be in English**, following these conventions:
- Use `ruff` for formatting (120 char line length)
- Type hints required for all functions and methods
- Docstrings for public APIs (Google style)
- Meaningful variable names (no single-letter except loop counters)

### Testing Strategy

**Philosophy**: Test behavior, not implementation. Focus on what the code does, not how.

**Test Types:**
1. **Unit Tests**: Test individual functions/methods in isolation
2. **Mocked Integration Tests**: Test component interactions with mocked external services
3. **No Live API Tests**: Never call real Jira APIs in tests

**Best Practices:**
- Use `autospec=True` when mocking to catch signature mismatches
- Use dependency injection to make code testable
- Mock at the right location (where imported, not where defined)
- Keep tests fast (<1s per test file ideal)
- Use fixtures for common test setup

**Coverage Requirements:**
- Minimum: 70% (enforced by pre-commit)
- Warning: 50-69% (shows warning)
- Target: 80%+ for core business logic

### Commit Convention

Uses **Conventional Commits** enforced by Commitizen:

```
<type>(<scope>): <subject>

<body>
```

**IMPORTANT RULES:**
- **Only functional information**: Describe WHAT changed and WHY
- **No attribution**: NO "Generated by", "Co-Authored-By", or Claude references
- **Be concise**: Focus on the change, not the process
- **Use imperative mood**: "Add feature" not "Added feature"

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring (no feature or bug fix)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependencies changes
- `ci`: CI/CD pipeline changes
- `chore`: Other changes (e.g., maintenance)

**Good Examples:**
```bash
feat(search): add JQL query support for advanced search

Implements advanced search with full JQL syntax support.
Users can now use complex queries with AND/OR operators.

fix(auth): handle expired OAuth tokens gracefully

Automatically refresh expired tokens instead of failing.
Reduces authentication errors for long-running sessions.

ci: update GitHub Actions to use master branch

Changed all workflow triggers from 'main' to 'master' to match
repository configuration. Disabled PyPI publishing.
```

**Bad Examples (DO NOT USE):**
```bash
# ❌ Contains attribution
fix(auth): handle expired tokens

Fixed the authentication issue.

🤖 Generated with [Claude Code](...)
Co-Authored-By: Claude <...>

# ❌ Too verbose, no functional value
feat: add a new feature

I added this new feature because the user asked for it.
This was implemented using Claude Code.
```

Use `uv run cz commit` for interactive commit creation.

### Pre-commit Hooks

**Hooks run on every commit:**
1. `ruff` - Format and lint code
2. `mypy` - Type checking
3. `bandit` - Security scanning
4. `commitizen` - Validate commit message
5. `pytest-cov` - Run tests with minimum 70% coverage

**If hooks fail, the commit is rejected.** Fix issues before committing.

### Error Handling

**Always provide context and actionable guidance:**

```python
# Bad
raise ValueError("Invalid issue")

# Good
raise InvalidIssueError(
    f"Issue '{issue_key}' not found. "
    f"Check that the issue exists and you have permission to view it. "
    f"Format should be: PROJECT-123"
)
```

**Common error categories:**
- `ConnectionError`: Jira unreachable, invalid URL, network issues
- `AuthenticationError`: Invalid credentials, expired tokens
- `PermissionError`: Insufficient Jira permissions
- `ValidationError`: Invalid user input
- `JiraAPIError`: Unexpected Jira API responses

## Release Workflow

### Semantic Versioning

Uses `python-semantic-release` for fully automated releases:

1. **Commit with conventional format** (enforced by Commitizen)
2. **Push to main branch** (or merge PR)
3. **GitHub Actions runs:**
   - Analyzes commits since last release
   - Determines version bump (major.minor.patch)
   - Generates CHANGELOG.md
   - Creates Git tag
   - Builds wheel and sdist
   - Publishes to PyPI (Trusted Publishing)
   - Creates GitHub Release with notes

**Version Bump Rules:**
- `feat:` → minor version (0.1.0 → 0.2.0)
- `fix:` → patch version (0.1.0 → 0.1.1)
- `feat!:` or `BREAKING CHANGE:` → major version (0.1.0 → 1.0.0)

### GitHub Actions

**Current action versions (verified for 2025):**
- `actions/checkout@v5`
- `actions/setup-python@v6` (with built-in pip caching)
- `actions/cache@v4` (for uv cache)

**Workflows:**
- `.github/workflows/ci.yml` - Run on push/PR (lint, test, security)
- `.github/workflows/release.yml` - Run on push to main (semantic release)
- `.github/workflows/publish.yml` - Run on release (PyPI publish)

## Installation Methods

**Recommended (isolated environment):**
```bash
# Using uvx (recommended)
uvx install budjira

# Using pipx (alternative)
pipx install budjira
```

**Traditional:**
```bash
pip install budjira
```

**From source:**
```bash
git clone https://github.com/cdds-ab/budjira.git
cd budjira
uv sync
uv run budjira --help
```

## Self-Update Mechanism

**Version checking:**
- Queries PyPI JSON API: `https://pypi.org/pypi/budjira/json`
- Caches result for 24 hours
- Shows notification if update available
- Displays what's new from release notes

**Update command:**
```bash
budjira update
```
Detects installation method (uvx/pipx/pip) and runs appropriate update command.

## Common Development Tasks

### Adding a New Command

1. Create command module in `budjira/cli/` (e.g., `comment.py`)
2. Define command using Typer with type hints
3. Add business logic to `budjira/core/`
4. Create Pydantic models in `budjira/models/` if needed
5. Write unit tests in `tests/cli/test_comment.py`
6. Write core logic tests in `tests/core/`
7. Update this CLAUDE.md if architectural changes

### Adding a New Jira API Call

1. Add method to `JiraClient` class in `budjira/core/jira_client.py`
2. Wrap `jira` library call with error handling
3. Add logging for debugging
4. Write mocked tests in `tests/core/test_jira_client.py`
5. Use `autospec=True` when mocking `jira` library

### Debugging

**Enable debug output:**
```bash
budjira --debug search "project = MYPROJ"
```

**View logs:**
```bash
budjira logs              # Show recent logs
budjira logs | tail -50   # Last 50 lines
budjira logs | grep ERROR # Filter errors
```

**Log locations:**
- `~/.config/budjira/logs/{context_name}.log`

### Running Specific Tests

```bash
# Test a specific file
uv run pytest tests/test_search.py -v

# Test a specific function
uv run pytest tests/test_search.py::test_search_issues -v

# Test with debug output
uv run pytest tests/test_search.py -vv -s

# Test with coverage for specific module
uv run pytest tests/core/ --cov=budjira.core
```

## Notes for AI Assistants

**When implementing new features:**
1. Always follow the modular structure (don't put everything in main.py)
2. Delegate to the `jira` library; don't reimplement API calls
3. Write tests BEFORE or alongside implementation (TDD encouraged)
4. Ensure all error paths have helpful messages
5. Add type hints and docstrings
6. Run pre-commit hooks before committing
7. Use conventional commit messages (functional info only, NO Claude attribution)

**When fixing bugs:**
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Check for similar issues elsewhere
5. Update documentation if behavior changed

**Code quality is non-negotiable:**
- All pre-commit hooks must pass
- Coverage must be ≥70%
- Type checking must pass (mypy strict)
- Security scanning must pass (bandit)
- No TODO comments in main branch (use issues instead)
