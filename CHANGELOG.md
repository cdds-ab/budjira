# CHANGELOG


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
