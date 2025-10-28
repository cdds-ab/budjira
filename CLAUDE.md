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
│   ├── ai.py         # AI usage prompt generation
│   ├── connect.py    # Connection management (+ tempo-setup)
│   ├── create.py     # Issue creation (interactive + DoR templates)
│   ├── dor.py        # Definition of Ready template management
│   ├── epic.py       # Epic management commands
│   ├── issue.py      # Issue updates (status, fields, labels, epic linking)
│   ├── search.py     # Issue search (JQL + filters)
│   ├── show.py       # Issue detail view ✨ NEW v1.8.0
│   ├── tempo.py      # Tempo Timesheets integration ✨ NEW v1.6.0
│   ├── update.py     # Self-update commands
│   └── worklog.py    # Worklog commands (add, list)
├── core/             # Core business logic
│   ├── __init__.py
│   └── jira_client.py    # Wrapper around jira library (+ get_issue_details)
├── tempo/            # Tempo Timesheets integration ✨ NEW v1.6.0
│   ├── __init__.py
│   ├── client.py     # TempoClient - REST API integration
│   └── models.py     # Pydantic models (TempoWorklog, TempoAccount)
├── config/           # Configuration management
│   ├── __init__.py
│   ├── settings.py   # Settings using pydantic-settings
│   └── credentials.py    # Secure credential handling (+ key-based storage)
├── models/           # Pydantic data models
│   ├── __init__.py
│   ├── config.py     # GlobalConfig
│   ├── connection.py # Connection, ConnectionList (+ tempo_enabled)
│   ├── dor.py        # DoR templates and validation
│   └── issue.py      # Issue, Comment, Attachment, WorkLog, User, Status, IssueType, Priority
├── utils/            # Utilities
│   ├── __init__.py
│   ├── banner.py     # ASCII art banner
│   ├── connection.py # Connection resolution (3-tier priority)
│   ├── datetime_parser.py  # Datetime parsing (ISO, today, yesterday)
│   ├── dor_validator.py    # DoR template validation
│   ├── editor.py     # Multi-line markdown editor
│   ├── errors.py     # Custom exceptions
│   ├── formatter.py  # Output formatting (JSON, table) ✨ NEW v1.7.0
│   ├── time_parser.py      # Time string parsing (1h, 30m, 2h30m)
│   └── version.py    # Version checking via GitHub Releases
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

**3. Global Output Formatting (Typer Context Pattern):** ✨ NEW v1.7.0
- Global `--format` flag (`table` or `json`) stored in Typer context
- Context object passed to all subcommands via `ctx.obj`
- Custom JSON serializer handles Pydantic models, datetime/date, Enums
- Banner/header automatically suppressed in JSON mode
- Example: `budjira --format json tempo worklogs`

**4. Epic Information Caching:** ✨ NEW v1.7.0
- In-memory dictionary cache for epic data per command invocation
- Minimizes Jira API calls when multiple worklogs reference same issue
- Optional `--no-epic` flag for performance-critical scenarios
- Fallback: Modern (parent field) → Legacy (Epic Link custom field)

**5. Jira Library Wrapper:**
- Wraps the `jira` library (pycontribs/jira) rather than reimplementing API calls
- Provides consistent error handling and logging
- Adds caching and retry logic

**6. Error Handling Strategy:**
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
  - `get_issue_epic()`: Fetch epic info with modern/legacy fallback ✨ NEW v1.7.0
  - `get_issue_details()`: Fetch comprehensive issue data (epic, time, comments, attachments) ✨ NEW v1.8.0
- `TempoClient`: REST API client for Tempo Timesheets (v1.6.0+)
- Connection management with multi-instance support

**Configuration Layer:**
- Pydantic models for type-safe configuration
- Secure credential storage (prefer system keyring)
- Environment variable support for CI/CD

**Utils Layer:**
- Structured logging to files (per-context)
- Version checking via PyPI JSON API (24h cache)
- Custom exception hierarchy
- `OutputFormatter`: JSON/table output formatting ✨ NEW v1.7.0
  - Custom JSON serializer for Pydantic/datetime/Enums
  - Global `--format` flag support

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

### CI/CD Pipeline Consistency

**Critical:** CI and pre-commit hooks are perfectly synchronized to ensure "if pre-commit passes locally → CI passes" ✅

**Implementation (v1.7.1):**
- CI uses `pre-commit/action@v3.0.1` instead of individual tool steps
- Single source of truth: `.pre-commit-config.yaml`
- No hardcoded Python versions (works with matrix 3.10-3.13)
- Same ruff version (v0.8.4) in both environments
- Same behavior (format + check) in both environments

**Benefits:**
- ✅ No version drift between local and CI
- ✅ Guaranteed consistency (pre-commit green → CI green)
- ✅ Easier maintenance (update versions in one place)
- ✅ Faster feedback (fail fast locally)

**Testing:** Tests run separately in CI for proper coverage reporting to Codecov.

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

## Context Management

**Session Continuity with `.claude/` Directory:**

To maintain context across session boundaries (compact/restart), use the `.claude/` directory:

```
.claude/
└── context.md    # Current project status, decisions, next steps
```

**When user says "sichere context" or "save context":**
1. Create/update `.claude/context.md` with current project status
2. Include:
   - Current version and uncommitted changes
   - Recent session summary (major changes made)
   - Pending decisions/tasks
   - Important design choices made
   - Next steps
3. Commit with message: `docs: update project context`

**Context File Template:**
```markdown
# Budjira Project Context

## Current State
- Version: [version]
- Branch: [branch]
- Uncommitted: [yes/no + description]

## Recent Changes
- [List of significant changes from this session]

## Pending Decisions
- [ ] [Decision 1]
- [ ] [Decision 2]

## Design Decisions Made
- [Important architectural or workflow decisions]

## Next Steps
- [ ] [Immediate task]
- [ ] [Short-term task]
```

**Auto-loading:**
- `.claude/context.md` is automatically loaded when Claude Code starts
- After compact, new session begins with full context from this file
- Best practice: Update at ~85-90% token budget (170k/200k tokens)

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

## Development Workflow & Checklists

This section provides structured checklists for repeatable, high-quality development. These checklists ensure nothing is forgotten and maintain consistency across features.

### Feature Development Lifecycle

#### Phase 1: Planning & Analysis
- [ ] GitHub Issue exists with clear description and use cases
- [ ] Use cases defined with examples
- [ ] API/Backend functionality checked (what exists already?)
- [ ] Architecture decisions made (where does the code belong?)
- [ ] Breaking changes identified (if yes: use `feat!`)
- [ ] Dependencies checked (new packages needed?)
- [ ] Review existing similar features for consistency

#### Phase 2: Implementation
- [ ] Tests written FIRST or PARALLEL (TDD encouraged)
- [ ] Code placed in correct module (`cli/`, `core/`, `models/`, `utils/`)
- [ ] Type hints on all functions/methods
- [ ] Docstrings for public APIs (Google style)
- [ ] Error handling with custom exceptions from `utils/errors.py`
- [ ] Logging added (`logger.info`/`logger.debug`)
- [ ] Rich Console used for user output (not `print()`)
- [ ] No hardcoded values (use config/constants)
- [ ] No debug `print()` statements left in code

#### Phase 3: Testing
- [ ] Unit tests written (pytest)
- [ ] Mocked integration tests (NO live API calls)
- [ ] Edge cases tested (empty input, None, invalid data)
- [ ] Error paths tested (`pytest.raises`)
- [ ] Coverage ≥70% overall (check with `uv run pytest --cov`)
- [ ] Coverage ≥80% for new code (aim for 90%+ for core logic)
- [ ] Tests use fixtures from `conftest.py` where appropriate
- [ ] Jira API calls mocked with `autospec=True`

#### Phase 4: Documentation
- [ ] **README.md** updated if user-facing feature
- [ ] **.claude/context.md** updated:
  - [ ] "Implementierte Features" section
  - [ ] Test statistics (`pytest --cov` output)
  - [ ] Roadmap status
  - [ ] Known limitations if any
- [ ] **AI prompt updated** if CLI commands or models changed:
  - [ ] Edit `budjira/cli/ai.py` template
  - [ ] Regenerate: `uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md`
  - [ ] Commit separately with `docs: update AI usage prompt`
- [ ] **.claude/ai-prompt-supplements.md** extended if new workflows
- [ ] **CLAUDE.md** updated if architectural changes
- [ ] Inline code comments added for complex logic
- [ ] CHANGELOG.md NOT updated (automatic via semantic-release)

#### Phase 5: Pre-Commit Checks
**Automatic (via pre-commit hooks):**
- [ ] ruff format & lint pass
- [ ] mypy type checking pass
- [ ] bandit security scan pass
- [ ] pytest with ≥70% coverage pass
- [ ] commitizen commit message validation
- [ ] Documentation update reminders shown

**Manual checks before commit:**
- [ ] No `print()` statements (use `logger` instead)
- [ ] No `# TODO` comments (create GitHub Issue instead)
- [ ] No hardcoded secrets/credentials
- [ ] No unused imports
- [ ] No commented-out code blocks
- [ ] No `# type: ignore` without explanation comment

#### Phase 6: Commit & Push
- [ ] Conventional Commit message prepared:
  - `feat:` for new features (MINOR bump: 1.4.0 → 1.5.0)
  - `fix:` for bug fixes (PATCH bump: 1.4.0 → 1.4.1)
  - `test:` for test additions (PATCH bump)
  - `docs:` for documentation only (NO bump)
  - `feat!:` or `fix!:` for breaking changes (MAJOR bump)
- [ ] **NO Claude attribution** in commit message
- [ ] Imperative mood ("Add feature" not "Added feature")
- [ ] Describes WHAT and WHY, not HOW
- [ ] Commit message is concise (1-2 sentences in subject)
- [ ] Commit pushed to master branch
- [ ] GitHub Actions CI passes (green checkmark)

#### Phase 7: Post-Release
- [ ] Semantic release created automatically (if `feat`/`fix` commit)
- [ ] Release notes reviewed on GitHub Releases
- [ ] **.claude/context.md** updated with new version number
- [ ] Related GitHub Issue closed with link to release
- [ ] `uv.lock` synced if needed (`uv sync`)

---

### Documentation Update Matrix

Use this matrix to determine which documentation files need updates based on the type of change:

| Change Type | README.md | CLAUDE.md | context.md | ai-usage-prompt | ai-prompt-supplements |
|-------------|-----------|-----------|------------|-----------------|----------------------|
| **New CLI command** | ✅ Yes | ✅ If architectural | ✅ Yes | ✅ Yes | ✅ Yes (workflows) |
| **New CLI flags** | ✅ If user-facing | ❌ No | ✅ Yes | ✅ Yes | ✅ If best practice |
| **Backend/Core change** | ❌ No | ✅ If pattern change | ✅ Yes | ❌ No | ❌ No |
| **New model** | ❌ No | ✅ If important | ✅ Yes | ❌ No | ❌ No |
| **Test addition** | ❌ No | ❌ No | ✅ Yes (stats) | ❌ No | ❌ No |
| **Bug fix** | ❌ No | ❌ No | ✅ If significant | ❌ No | ❌ No |
| **Breaking change** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Dependency update** | ❌ No | ✅ If major | ✅ If major | ❌ No | ❌ No |

**Quick Rules:**
- **context.md**: Always update for any significant change
- **README.md**: Only for user-facing features
- **AI prompt**: Only when CLI or models change
- **CLAUDE.md**: Only for architectural or process changes

---

### Testing Requirements by Feature Type

#### CLI Commands (`budjira/cli/`)
**Required Tests:**
- ✅ Command execution with valid inputs
- ✅ Command with all flag combinations
- ✅ Error handling (missing args, invalid input)
- ✅ Interactive mode (mock `typer.prompt()` and `typer.confirm()`)
- ✅ Non-interactive mode
- ✅ Rich Console output (verify key elements present)
- ✅ Connection resolution (`--connection` flag)

**Tools:** `typer.testing.CliRunner`, `pytest-mock`, `unittest.mock.patch`

**Target Coverage:** 85%+

**Example:**
```python
def test_command_with_valid_input(mock_jira_client):
    runner = CliRunner()
    result = runner.invoke(app, ["command", "ARG"])
    assert result.exit_code == 0
    assert "Expected output" in result.stdout
```

---

#### Core Logic (`budjira/core/`)
**Required Tests:**
- ✅ Happy path with valid data
- ✅ All method parameters tested (optional/required)
- ✅ Error scenarios (API errors, network issues, 404/403/401)
- ✅ Custom exceptions raised correctly
- ✅ Logging calls present (check with `caplog` fixture)
- ✅ Jira API calls mocked with `autospec=True`

**Tools:** `unittest.mock`, `pytest` fixtures, `caplog`

**Target Coverage:** 90%+

**Example:**
```python
@patch("budjira.core.jira_client.JIRA", autospec=True)
def test_get_issue(mock_jira):
    client = JiraClient(...)
    issue = client.get_issue("PROJ-123")
    mock_jira.return_value.issue.assert_called_once_with("PROJ-123")
```

---

#### Models (`budjira/models/`)
**Required Tests:**
- ✅ Valid data parsing
- ✅ Invalid data raises `ValidationError`
- ✅ Optional fields use default values
- ✅ Serialization works (`dict()`, `model_dump()`)
- ✅ Custom validators (if any)

**Tools:** Pydantic validation testing

**Target Coverage:** 100%

**Example:**
```python
def test_model_valid_data():
    data = {"field1": "value", "field2": 123}
    model = MyModel(**data)
    assert model.field1 == "value"

def test_model_invalid_data():
    with pytest.raises(ValidationError):
        MyModel(field1="invalid")
```

---

#### Utils (`budjira/utils/`)
**Required Tests:**
- ✅ Pure function tests (input → output)
- ✅ Edge cases (empty string, None, invalid input)
- ✅ Error handling (raise appropriate exceptions)
- ✅ Integration with dependencies (mocked)

**Target Coverage:** 95%+

**Example:**
```python
def test_parse_time_string():
    assert parse_time_string("1h") == 60
    assert parse_time_string("2h30m") == 150
    with pytest.raises(ValueError):
        parse_time_string("invalid")
```

---

### Definition of Done

A feature is considered **DONE** when ALL of the following are met:

#### Code Quality
- [ ] Implementation complete in correct module
- [ ] Type hints on all functions/methods (mypy strict passes)
- [ ] Docstrings on all public APIs (Google style)
- [ ] Error handling with custom exceptions
- [ ] Logging added (`logger.info`/`debug`)
- [ ] No `# TODO` comments (moved to GitHub Issues)
- [ ] No hardcoded values (use config/constants)
- [ ] No `print()` statements (use logger or Rich Console)

#### Testing
- [ ] Unit tests written (pytest)
- [ ] Integration tests mocked (no live API)
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Coverage ≥70% overall
- [ ] Coverage ≥80% for new code
- [ ] All tests pass locally

#### Quality Checks
- [ ] `ruff format` and `ruff check` pass
- [ ] `mypy --strict` passes
- [ ] `bandit` security scan passes
- [ ] All pre-commit hooks pass
- [ ] No `# type: ignore` without explanation

#### Documentation
- [ ] README.md updated (if user-facing)
- [ ] .claude/context.md updated (stats, status, roadmap)
- [ ] AI prompt updated (if CLI/models changed)
- [ ] Inline comments for complex logic

#### Release
- [ ] Conventional commit message (no Claude attribution)
- [ ] Pushed to master
- [ ] CI/CD pipeline green
- [ ] Semantic release created (if `feat`/`fix`)
- [ ] GitHub Issue closed with release link

---

### Quick Pre-Commit Checklist

Run this mental checklist **BEFORE** running `git commit`:

#### Code Cleanup
- [ ] No `print()` statements (use `logger` instead)
- [ ] No `# TODO` comments (create GitHub Issue)
- [ ] No hardcoded secrets/credentials
- [ ] No unused imports
- [ ] No commented-out code
- [ ] No debug breakpoints (`import pdb; pdb.set_trace()`)

#### Documentation
- [ ] If CLI changed → AI prompt updated?
- [ ] If new feature → context.md updated?
- [ ] If user-facing → README.md updated?

#### Testing
- [ ] `uv run pytest --cov` passes locally
- [ ] New tests added for new code
- [ ] Coverage not decreased

#### Commit Message
- [ ] Conventional format (`feat`/`fix`/`docs`/`test`/`chore`)
- [ ] **NO** Claude attribution
- [ ] Imperative mood ("Add" not "Added")
- [ ] Describes WHAT and WHY, not HOW

---

### Session Start Checklist (for Claude)

**Automated via `scripts/session_start.py`:**

Run at the beginning of each development session:
```bash
uv run python scripts/session_start.py
```

This script automatically checks:
- [ ] Current project version
- [ ] Git status (clean/dirty)
- [ ] Current branch
- [ ] Recent commits (last 3)
- [ ] Open GitHub Issues
- [ ] Latest release

**Manual checks after running script:**
- [ ] Review open issues: Are there feature requests?
- [ ] Check if uncommitted changes need to be committed
- [ ] Verify no merge conflicts or issues
- [ ] Understand user's intent before starting work

**During development:**
- [ ] Use `TodoWrite` tool to track progress
- [ ] Update user regularly on progress
- [ ] Ask clarifying questions if requirements unclear
- [ ] Write tests alongside implementation
- [ ] Run `uv run pytest` frequently

---

### Post-Release Checklist

After semantic-release creates a new release (automatic on push to master):

#### Verify Release
- [ ] Check GitHub Release created: `gh release list`
- [ ] Verify CI/CD success: `gh run list --limit 1`
- [ ] Review release notes on GitHub Releases page
- [ ] Check version number is correct

#### Update Documentation
- [ ] Update `.claude/context.md`:
  - [ ] Current Version section
  - [ ] Release Status
  - [ ] Implementierte Features (if new feature)
  - [ ] Updated test statistics
  - [ ] Updated coverage stats
- [ ] Commit context update: `docs: update project context to vX.Y.Z`

#### Cleanup
- [ ] Close related GitHub Issues with release link
- [ ] Sync `uv.lock` if needed: `uv sync`
- [ ] Commit lock file if changed: `chore(deps): update uv.lock to vX.Y.Z`
- [ ] Push final commits

#### Verification
- [ ] Install released version: `uvx budjira@latest --version`
- [ ] Test basic commands work
- [ ] Check PyPI page (if publishing enabled)
