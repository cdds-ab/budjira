# CHANGELOG


## v1.4.0 (2025-10-12)

### Features

- Add Definition of Ready (DoR) templates for issue types
  ([`7ebc7e8`](https://github.com/cdds-ab/budjira/commit/7ebc7e829e80a8bf84c3b8fef9d1fc1dbda6157f))

DoR Template System: - Add configurable DoR templates per issue type (Story, Bug, Task) - Default
  templates with required sections for consistent quality - Store templates in
  ~/.config/budjira/dor-templates.toml - Pydantic models for template configuration and validation

CLI Commands: - Add 'budjira dor' command group for template management - Subcommands: list, show,
  edit, validate - View and customize templates via CLI - Edit templates in $EDITOR with markdown
  support

Interactive Issue Creation with DoR: - Integrate DoR templates into 'budjira create issue' workflow
  - Open $EDITOR with pre-filled template sections for Story/Bug/Task - Validate required sections
  before issue creation - Add --skip-dor flag to bypass DoR validation

DoR Validation: - Three validation levels: strict (block), warn (allow), off (disabled) - Markdown
  section extraction (## Section Name) - Check for missing required sections - Warn on empty section
  content

Configuration: - Add enforce_dor and dor_validation_level to global config - Default validation
  level: warn - Templates customizable per project

Editor Integration: - New editor utility for multi-line markdown input - Opens $EDITOR (or vim
  fallback) with template - Temp file with .md extension for syntax highlighting - Optional
  validation loop support

Testing: - Add 36 comprehensive tests for DoR models and validation - Tests for template config,
  validation, section extraction - Basic CLI tests for dor commands - Mock get_settings in create
  tests to prevent DoR interference - 72% total coverage (exceeds 70% minimum)

Documentation: - Add DoR section to README with examples - Document template structure and
  validation - Update features list and roadmap - Configuration file documentation

This ensures consistent issue quality and helps teams maintain clear requirements for User Stories,
  Bugs, and other issue types. The system is fully customizable and can be disabled if not needed.


## v1.3.0 (2025-10-12)

### Features

- Auto-generate AI usage prompt with latest features
  ([`37c2c2d`](https://github.com/cdds-ab/budjira/commit/37c2c2d7181cec5490889e6ccb11b9af0de7e1f0))

Improve AI Prompt Generation: - Add --plain flag to output raw markdown (no terminal formatting) -
  Update AI usage prompt with Issue Update and Epic Management sections - Expand Common Workflows
  with 8 practical examples

Auto-Regeneration System: - Update pre-commit hook to automatically regenerate
  .claude/ai-usage-prompt.md - Hook triggers when CLI files are modified - Automatically stages
  updated prompt file - Prevents infinite loop by skipping when only prompt file changed - Exclude
  AI prompt from end-of-file-fixer to prevent conflicts - Ensures ClaudePM always has current
  budjira capabilities

New Sections in AI Prompt: - Updating Issues: status transitions, field updates, label management -
  Epic Management: view epics with progress - Complete Issue Workflow: 4-step workflow example

This ensures ClaudePM can discover and use all budjira features, including the newly added issue
  updates and epic management.


## v1.2.0 (2025-10-12)

### Features

- Implement issue updates and epic management (ClaudePM features)
  ([`b023b34`](https://github.com/cdds-ab/budjira/commit/b023b3471b37cc83cb18dc5fcc05d2cd5fff6b1c))

Issue Update Commands: - Add 'budjira issue update' command for status transitions - Support field
  updates: assignee, priority, summary, description - Add label management: --add-label,
  --remove-label - Support epic linking: --epic flag - Multiple updates in single command - Add
  'budjira issue transitions' to show available workflows

Epic Management Commands: - Add 'budjira epic show' to display epic with child issues - Show epic
  progress (X/Y issues done, percentage) - Display child issues in table with status icons -
  Calculate completion statistics

JiraClient Backend: - Add get_transitions() method - Add transition_issue() with case-insensitive
  matching - Add update_issue() with field validation - Add add_labels() and remove_labels() - Add
  link_to_epic() with dynamic field detection - Add get_epic_issues() via JQL query

Testing: - Add 69 new tests for JiraClient methods - Achieve 94% coverage for jira_client.py
  (target: 90%) - Total: 212 tests passing, 76% overall coverage - Comprehensive error path testing

Documentation: - Update README with issue update examples - Add epic management documentation -
  Update feature list and roadmap - Add Quick Start sections for new commands

This implements the top 2 feature requests from ClaudePM for effective project management workflows.


## v1.1.0 (2025-10-12)

### Documentation

- Add shell completion setup instructions
  ([`a51e3c4`](https://github.com/cdds-ab/budjira/commit/a51e3c46ec94785559e9f229aaae9359119aaa38))

Installation Script: - Add completion hint at end of installer output - Inform users about
  --install-completion option - Non-invasive: user decides to enable completion

README: - Add Shell Completion section after Update - Document automatic installation via
  --install-completion - Provide manual installation instructions for bash/zsh/fish - Include test
  commands to verify completion works

Shell completion is provided by Typer's built-in support for bash, zsh, and fish shells. This
  addresses the missing completion setup in the installer while keeping it non-invasive.

### Features

- Add AI usage prompt generation and maintenance system
  ([`1e56ad0`](https://github.com/cdds-ab/budjira/commit/1e56ad066bffaec6d83a243b3d26bf20933c5664))

New AI Integration Command: - Add 'budjira ai usage-prompt' command - Generate comprehensive AI
  assistant guide - Markdown-formatted output via Rich - Covers all commands, workflows, and
  examples

AI Prompt Maintenance System: - Create .claude/ai-prompt-supplements.md for manual content - Add
  pre-commit hook to detect CLI changes - Non-blocking warning when CLI files modified - Reminds to
  review AI documentation - Add maintenance instructions to .claude/context.md

Testing: - Add 7 new tests for ai commands (100% coverage) - Total: 165 tests, 80.10% coverage - All
  quality checks passing (ruff, mypy, bandit)

Documentation: - Update README with AI integration section - Add usage examples (copy to clipboard,
  save to file) - Update features list and roadmap - Document generated prompt contents


## v1.0.1 (2025-10-12)

### Bug Fixes

- Handle multiple Jira datetime formats in ISO parsing
  ([`22ad81f`](https://github.com/cdds-ab/budjira/commit/22ad81f44b2176673b25f52e3df3ad3bc0acf6b8))

Jira API returns datetime strings in multiple formats: - 2025-01-10T10:00:00.000Z (with Z suffix) -
  2025-01-10T10:00:00.000+0000 (timezone without colon) - 2025-01-10T10:00:00.000+00:00 (timezone
  with colon)

Python's datetime.fromisoformat() only accepts the colon format.

Solution: - Add _parse_jira_datetime() helper method - Normalize Z suffix to +00:00 - Fix timezone
  format: +0000 -> +00:00 - Handle both positive and negative timezones

This fixes CI failures on Python 3.10-3.13 where tests were failing with "ValueError: Invalid
  isoformat string: '..+0000'".

Fixes: - tests/models/test_issue.py::test_from_jira_issue - tests/core/test_jira_client.py (7 tests)

All 158 tests now passing.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>


## v1.0.0 (2025-10-12)

### Documentation

- Add context management system for session continuity
  ([`1804b25`](https://github.com/cdds-ab/budjira/commit/1804b25e2be62a2385347853e978a0fc470bf2a5))

- Add Context Management section to CLAUDE.md - Create .claude/context.md with comprehensive project
  status - Remove .claude/ from .gitignore to track context file - Establish "sichere context"
  command pattern for updating context

Context files will be auto-loaded by Claude Code on session start and after compacts, maintaining
  development state across boundaries.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Comprehensive project context documentation
  ([`4d75dfc`](https://github.com/cdds-ab/budjira/commit/4d75dfcfd902e2ce0e2a8697cf7eaac606437ad6))

Complete rewrite of .claude/context.md with exhaustive project documentation:

- Project overview and philosophy - Full architecture documentation (modules, patterns, tech stack)
  - Detailed feature status for all 6 implemented features - Test coverage analysis (158 tests, 80%
  coverage) - CI/CD pipeline documentation (GitHub Actions) - Semantic release configuration and
  rules - Open decisions (release workflow, pre-release support) - Development workflow and user
  preferences - Technical debt tracking - Roadmap and next steps - Session hints for Claude Code
  continuity

This provides a complete "tabula rasa" state for future work.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Update README to reflect implemented features
  ([`205db9a`](https://github.com/cdds-ab/budjira/commit/205db9a1cffc012c0882408d296f8396930203a0))

Update README.md to accurately reflect current implementation status:

Features Section: - Change "Project-root based" → "Name-based connection management" - Update Search
  & Filter: "coming soon" → "implemented" - Update Create Issues: "coming soon" → "implemented" -
  Update Time Tracking: Note backend ready, CLI pending

Quick Start: - Add search command examples (JQL + filters) - Add create command examples
  (interactive + non-interactive) - Add new connection commands: use, current - Restructure sections
  (1-5 instead of 1-3)

Coming Soon Section: - Remove Search for Issues (now implemented) - Remove Create Issues (now
  implemented) - Keep Log Work Time with note about backend being ready - Add "Additional Planned
  Features" subsection

Roadmap: - Add "Implemented ✅" section with completed features - Add "In Progress 🚧" section for
  worklog CLI - Reorganize "Planned 📋" section - Clear separation of status categories

This brings README in sync with actual codebase state (search, create, enhanced connection
  management all implemented).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### Features

- Implement Jira core functionality and refactor connection model
  ([`b31a6e4`](https://github.com/cdds-ab/budjira/commit/b31a6e44892290afa7895b7b7b9ddb3210318719))

Implement core Jira functionality with JiraClient wrapper, search and create commands. Refactor
  connection model from directory-based to name-based with environment variable support.

New Features: - JiraClient wrapper for Jira API with comprehensive error handling - Search command
  with JQL and filter support - Create command with interactive and non-interactive modes - Time
  parser utility for worklog entries - Connection resolution with priority: --connection > ENV >
  config default

Refactoring: - Remove project_root from Connection model - Change from directory-based to name-based
  connection lookup - Add active_connection field to GlobalConfig - Implement BUDJIRA_CONNECTION
  environment variable support - Add 'connect use' command to set global default connection - Add
  'connect current' command to show active connection - Replace --root parameter with --connection
  in all commands

Tests: - Add comprehensive test coverage for all new features - Update all existing tests for new
  connection model - 158 tests passing with 80% coverage

BREAKING CHANGE: Connections are now identified by name instead of project_root. The --root
  parameter has been removed from all commands. Use --connection flag or BUDJIRA_CONNECTION
  environment variable instead.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### BREAKING CHANGES

- Connections are now identified by name instead of project_root. The --root parameter has been
  removed from all commands. Use --connection flag or BUDJIRA_CONNECTION environment variable
  instead.


## v0.4.6 (2025-10-11)

### Bug Fixes

- Correct semantic-release version_variable config
  ([`ad09bae`](https://github.com/cdds-ab/budjira/commit/ad09bae50d964761136b9ee60cda520fb4ecd5d4))

Remove pyproject.toml from version_variable as it should only contain Python files. TOML files are
  handled by version_toml.


## v0.4.5 (2025-10-11)

### Bug Fixes

- Correct semantic-release version_variable config
  ([`fed58c2`](https://github.com/cdds-ab/budjira/commit/fed58c2d72aac603a4efee6a53a8c4762cfe080c))

Remove pyproject.toml from version_variable as it should only contain Python files. TOML files are
  handled by version_toml.


## v0.4.4 (2025-10-11)

### Bug Fixes

- Add style commits to patch version bump tags
  ([`5d8d074`](https://github.com/cdds-ab/budjira/commit/5d8d074793b24a2a413fd6e743ac8c17538e1b51))

Style commits should trigger patch version bumps to ensure __init__.py and pyproject.toml stay in
  sync.

### Code Style

- Fix ruff formatting in main.py
  ([`bc4da30`](https://github.com/cdds-ab/budjira/commit/bc4da30cde531653d7cc5a383f764f4b5e4663c5))

Merge concatenated f-strings into single f-string.


## v0.4.3 (2025-10-11)

### Bug Fixes

- Resolve linting errors and update documentation
  ([`bfce3d2`](https://github.com/cdds-ab/budjira/commit/bfce3d216a812e8bd053cf9ec3a56e43e0adf736))

Linting fixes: - Use ternary operators where appropriate (SIM108) - Add 'from None' to raise
  statements in except clauses (B904) - Remove unnecessary f-string prefixes (F541) - Move type-only
  imports to TYPE_CHECKING blocks (TC003/TC001) - Organize and sort import statements (I001) -
  Prefix unused unpacked variables with underscore (RUF059)

Type checking fixes: - Remove all unused type ignores - Add mypy pragmas for Pydantic model
  validation in tests - Allow untyped decorators in CLI modules (Typer) and test fixtures - Add type
  ignore for JSON cache return (no-any-return) - Add type ignore for Pydantic URL validation in
  connect.py - Update test assertions to use current version (0.4.1)

Security annotations: - Add nosec comments for intentional security patterns - Document trusted
  subprocess execution for update script - Mark expected except-pass patterns

Documentation updates: - Remove PyPI badges (project uses GitHub Releases only) - Reorganize
  features list (implemented vs. coming soon) - Add auto-update feature documentation - Update Quick
  Start to show only implemented features - Add "Coming Soon" section for planned features

Infrastructure: - Install pre-commit hooks to catch issues before commit - Configure mypy overrides
  for CLI and test modules

- Use dynamic version in banner tests and update dependencies
  ([`9bf69eb`](https://github.com/cdds-ab/budjira/commit/9bf69eb73dcb72a5e3bc532ff4cecf6d50b1e48c))

- Replace hardcoded version strings in tests with __version__ import - This ensures tests remain
  valid after automated version bumps - Update virtualenv from 20.35.1 (yanked) to 20.35.3


## v0.4.2 (2025-10-11)

### Bug Fixes

- Sync __init__.py version with pyproject.toml
  ([`9bebe51`](https://github.com/cdds-ab/budjira/commit/9bebe51e1301aaa32f9f5c237df7ffbac9ab5dc2))

Update __init__.py to version 0.4.0 to match pyproject.toml. Semantic-release automatically bumps
  both files, so they should always be in sync.

- Sync __init__.py version with pyproject.toml (0.4.1)
  ([`d98a4f1`](https://github.com/cdds-ab/budjira/commit/d98a4f10e50c6148594072f73310be3383192ece))

Update __init__.py to version 0.4.1 to match pyproject.toml after semantic-release bump.


## v0.4.1 (2025-10-11)

### Bug Fixes

- Improve update handling and version sync
  ([`83c3fec`](https://github.com/cdds-ab/budjira/commit/83c3fec67ceb0528dd1a719641b114982c081dd5))

- Update __init__.py version to 0.3.0 (sync with pyproject.toml) - Add update_check.json to
  .gitignore (runtime data) - Improve install.sh to handle dirty working copies: - Reset local
  changes with git reset --hard - Clean untracked files with git clean -fd - Ensures clean updates
  without conflicts

This fixes issues where uv.lock or update_check.json changes prevent git pull during updates.


## v0.4.0 (2025-10-11)

### Features

- **update**: Implement automatic update checker
  ([`5c03814`](https://github.com/cdds-ab/budjira/commit/5c03814534e280634bba984668fe63d2e3a965ae))

Add self-update functionality via GitHub Releases API:

Features: - Automatic update check on startup (24h cache, configurable) - GitHub Releases API
  integration (not PyPI) - Update notification with release notes - `budjira update` command for
  self-update - `budjira update check` for check-only mode - Force check with --force flag -
  One-command update via install script - Respects check_updates config setting - Silent failure on
  network errors (non-blocking)

Implementation: - VersionChecker class with caching and version comparison - JSON-based cache with
  TTL - Semantic version comparison - Release notes display with Markdown formatting -
  Subprocess-based update execution

Tests: 12 new tests, 79% overall coverage (92% for VersionChecker).

All code passes ruff and mypy checks.


## v0.3.0 (2025-10-11)

### Features

- **cli**: Implement connection management commands
  ([`796225d`](https://github.com/cdds-ab/budjira/commit/796225d16789cb4ddc495e86c81b6bc4448b248a))

Add comprehensive connection management via `budjira connect` subcommands:

Commands: - add: Create new Jira connections with interactive prompts - list: Display all configured
  connections in table format - show: Show detailed connection information - remove: Delete
  connections and their credentials - test: Verify Jira connectivity and display server info

Features: - Interactive prompts with defaults for easy setup - Secure API token storage (separate
  from connection config) - Project-root based connection identification - Update existing
  connections - Connection testing with helpful error messages - Rich CLI output with tables and
  colored status indicators

Tests: 9 new tests, 84% overall coverage.

All code passes ruff and mypy checks.


## v0.2.0 (2025-10-11)

### Documentation

- Update commit convention to exclude attribution
  ([`0526a77`](https://github.com/cdds-ab/budjira/commit/0526a777c4ea0f838e3e5719bb6308cf44b1cd81))

Commit messages should only contain functional information about the changes. Removed requirements
  for "Generated by Claude Code" and "Co-Authored-By" footers.

Added clear examples of good vs bad commit messages with focus on what changed and why, using
  imperative mood.

### Features

- **config**: Implement configuration system with XDG paths
  ([`ffc2fc3`](https://github.com/cdds-ab/budjira/commit/ffc2fc352b163afca126af74994525df37110efe))

Add comprehensive configuration and credential management:

- Connection model with project-root based identification - GlobalConfig for application-wide
  settings - Settings class managing XDG-compliant directory structure - CredentialStore for secure
  API token storage (mode 0o600) - Support for multiple Jira instances/projects simultaneously -
  TOML-based configuration with pydantic validation - Python 3.10+ compatibility with tomli fallback

Configuration locations: - ~/.config/budjira/config.toml (global settings) -
  ~/.config/budjira/connections.toml (connection definitions) - ~/.config/budjira/credentials/ (API
  tokens, restricted access) - ~/.local/share/budjira/cache/ (SQLite cache) -
  ~/.local/share/budjira/logs/ (per-connection logs)

Tests: 39 new tests with 95% overall coverage.

All code passes ruff and mypy strict checks.


## v0.1.0 (2025-10-10)

### Bug Fixes

- Correct GitHub Actions configuration
  ([`7ea5702`](https://github.com/cdds-ab/budjira/commit/7ea5702d3c08b8d16c33d75ee495fb9d019e0beb))

- Fix codecov action parameter: file -> files - Add build step before semantic release to ensure uv
  is available

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Disable semantic-release build step
  ([`7de313f`](https://github.com/cdds-ab/budjira/commit/7de313ff83a5d675db10d1c6f35acb420147ea7b))

Build is now handled externally in GitHub Actions workflow with uv. Semantic-release will only
  handle versioning, tagging, and changelog.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

### Features

- Add curl-based installation script
  ([`b0783ad`](https://github.com/cdds-ab/budjira/commit/b0783ad0a5c0d04244a0155802a0d4b7c7f346bb))

- Add install.sh for one-command installation via curl - Script installs uv if needed, clones repo,
  and sets up symlink - Update README with curl installation instructions - Remove references to
  PyPI/pipx (not published yet) - Add update instructions for existing installations

Installation is now: curl -LsSf <url>/install.sh | sh

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Initial budjira CLI setup with header banner
  ([`c876528`](https://github.com/cdds-ab/budjira/commit/c876528da5dafcd176a592342f9910597407547c))

- Add complete project structure with modular architecture - Implement simple 2-line header with
  dino emoji and version - Add --quiet/-q flag to suppress header output - Configure pyproject.toml
  with all dependencies (uv, typer, rich, etc.) - Setup pre-commit hooks (ruff, mypy, bandit,
  commitizen) - Add GitHub Actions workflows for CI and semantic release - Include MIT license and
  comprehensive documentation - Add budjira logo and integrate into README - Implement custom
  exception hierarchy - Setup testing with pytest (20 tests, 86% coverage) - All quality checks
  passing (ruff, mypy, bandit)

The header is displayed by default on all commands and can be suppressed with -q/--quiet for
  scripting use cases.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>

- Initial budjira CLI setup with header banner
  ([`d302934`](https://github.com/cdds-ab/budjira/commit/d302934e5e8864dfc910e0e8ba6f364c3be9581f))

- Add complete project structure with modular architecture - Implement simple 2-line header with
  dino emoji and version - Add --quiet/-q flag to suppress header output - Configure pyproject.toml
  with all dependencies (uv, typer, rich, etc.) - Setup pre-commit hooks (ruff, mypy, bandit,
  commitizen) - Add GitHub Actions workflows for CI and semantic release - Include MIT license and
  comprehensive documentation - Add budjira logo and integrate into README - Implement custom
  exception hierarchy - Setup testing with pytest (20 tests, 86% coverage) - All quality checks
  passing (ruff, mypy, bandit)

The header is displayed by default on all commands and can be suppressed with -q/--quiet for
  scripting use cases.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
