# CHANGELOG


## v1.6.2 (2025-10-26)

### Bug Fixes

- Remove incorrect typer.Option check in tempo error handler
  ([`c7bdf98`](https://github.com/cdds-ab/budjira/commit/c7bdf98d131defc7134ce2bfb0647c070139ea1b))

Removed 'if typer.Option:' check which was always true and caused mypy truthy-function error. The
  debug hint should always be shown for unexpected errors.


## v1.6.1 (2025-10-26)

### Bug Fixes

- Persist tempo_enabled flag in connections.toml
  ([`fd88a3e`](https://github.com/cdds-ab/budjira/commit/fd88a3e623122bfa2a9beabc924687d9147a2b31))

Fixed Bug #4 where tempo-setup command succeeded but tempo commands failed with "Tempo is not
  enabled for connection" error.

Root cause: tempo_enabled field was not being serialized to TOML in save_connections() method.

Changes: - Added tempo_enabled to TOML serialization in settings.py - Enhanced 'connect show'
  command to display Tempo status - Added regression tests for tempo_enabled persistence

Closes #4

### Testing

- Add comprehensive tests for tempo-setup command
  ([`d69a034`](https://github.com/cdds-ab/budjira/commit/d69a03471f3b4e5eaf4fd08102c06077adea21be))

Added 4 tests to prevent regression of Bug #4: - test_tempo_setup_success_and_persistence: Verifies
  tempo_enabled persists to TOML - test_tempo_setup_with_existing_token_replacement: Tests token
  replacement flow - test_tempo_setup_api_failure_abort: Tests API failure handling -
  test_tempo_setup_no_connection: Tests missing connection error

Coverage increased from 78.80% to 81.92% (368 tests passing).


## v1.6.0 (2025-10-26)

### Documentation

- Update AI usage prompt and CLAUDE.md for Tempo
  ([`af07849`](https://github.com/cdds-ab/budjira/commit/af078495863f0182fd2faeb073f5e5b9a003b20e))

Updated comprehensive documentation with Tempo integration:

- .claude/ai-usage-prompt.md: Added Tempo Timesheets section - Setup instructions (budjira connect
  tempo-setup) - CLI commands (tempo log, tempo worklogs, tempo delete-worklog, tempo accounts) -
  When to use Tempo vs standard Jira - Tempo-specific error handling

- CLAUDE.md: Updated architecture overview - Added tempo/ module to structure diagram - Added
  tempo.py to CLI commands list - Extended Connection and CredentialStore descriptions - Added
  TempoClient to Core Layer components

- Update project context to v1.5.5
  ([`a058522`](https://github.com/cdds-ab/budjira/commit/a0585225c63c9608ec0bb46d00b0454e4178021e))

- Update project context to v1.6.0 with Tempo integration
  ([`e65c258`](https://github.com/cdds-ab/budjira/commit/e65c258b8c55c254b3113ccc57e94aff24d9dd8f))

Updated comprehensive documentation for Tempo Timesheets feature:

- .claude/context.md: Added v1.6.0 release section with full Tempo details - .claude/context.md:
  Updated test statistics (362 tests, 79.53% coverage) - .claude/context.md: Added Tempo to module
  structure and implemented features - .claude/ai-prompt-supplements.md: Added Tempo workflows and
  integration tips

### Features

- Add Tempo Timesheets integration for enterprise time tracking
  ([`af75349`](https://github.com/cdds-ab/budjira/commit/af75349d2fdaa3ba24598dd2e09cdc37fe434847))

Implements comprehensive Tempo Cloud API support for organizations using Tempo for time tracking and
  billing.

Features: - New tempo module with TempoClient for API communication - CLI commands: tempo log, tempo
  worklogs, tempo delete-worklog, tempo accounts - Connection setup: budjira connect tempo-setup -
  Pydantic models for Tempo API responses - Secure Tempo token storage via credential store - Full
  test coverage (37 new tests)

Implementation: - budjira/tempo/client.py: TempoClient with REST API integration -
  budjira/tempo/models.py: Pydantic models (TempoWorklog, TempoAccount) - budjira/cli/tempo.py: CLI
  commands for Tempo operations - Extended Connection model with tempo_enabled flag - Tests: 100%
  coverage for models, 96% for client, 75% for CLI

Breaking Changes: None Coverage: +0.19% (79.53% total, 362 tests passing)


## v1.5.5 (2025-10-25)

### Bug Fixes

- Escape regex metacharacters in pytest match pattern
  ([`1111e40`](https://github.com/cdds-ab/budjira/commit/1111e4021414868be5a093561d03aa2cb956485b))


## v1.5.4 (2025-10-25)

### Bug Fixes

- Complete AI usage prompt with time tracking documentation
  ([`f0c6173`](https://github.com/cdds-ab/budjira/commit/f0c617374c4d2f14c437f67bd276773acb5b5a3a))

The AI usage prompt was missing comprehensive documentation for the time tracking feature introduced
  in v1.5.0. This caused AI assistants to be unaware of worklog commands and time estimate options.

Added complete documentation for: - budjira worklog add command with time/datetime formats - budjira
  worklog list command - Time estimate options for issue creation/update - --log-work and
  --work-comment flags - Time tracking workflow example

Also updated overview to include all major features (DoR, epic management, time tracking).

### Documentation

- Update project context to v1.5.3
  ([`155e14b`](https://github.com/cdds-ab/budjira/commit/155e14b3373a70982023ae36ba1afc7aef71c831))


## v1.5.3 (2025-10-25)

### Bug Fixes

- Support GitHub token for update checks to avoid rate limiting
  ([`b50ba72`](https://github.com/cdds-ab/budjira/commit/b50ba72a7ca65238a40c402cec91c9493ce05fba))

GitHub API rate limits unauthenticated requests to 60/hour, causing update checks to fail with
  network errors. Added support for optional GITHUB_TOKEN or GH_TOKEN environment variables to
  authenticate requests and avoid rate limiting (5000 requests/hour for authenticated users).

Changes: - Added _get_headers() method to include GitHub token if available - Updated API request to
  use authentication headers - Improved error messages to guide users when rate limited - Added
  logging for better diagnostics

Resolves issue where 'budjira update' showed wrong version or network errors due to rate limiting.


## v1.5.2 (2025-10-25)

### Bug Fixes

- Support both modern and legacy epic linking in Jira Cloud
  ([`b883bc5`](https://github.com/cdds-ab/budjira/commit/b883bc5c5962adb38d32c0a6d02905d6a2290d58))

Fixes #2 - Epic linking now works with both team-managed and company-managed projects

Modern Jira Cloud team-managed projects use the 'parent' field for epic relationships, while older
  company-managed projects use the legacy 'Epic Link' custom field. This fix implements a two-step
  approach:

1. Try modern 'parent' field first (works in most Jira Cloud instances) 2. Fall back to legacy 'Epic
  Link' custom field if parent fails

Changes: - link_to_epic(): Try parent field, fallback to Epic Link custom field - get_epic_issues():
  Try parent JQL query, fallback to Epic Link JQL

Tests: - Added test_link_to_epic_success_modern for parent field - Added
  test_link_to_epic_success_legacy for Epic Link fallback - Updated test_link_to_epic_no_epic_field
  for both failure cases - Added test_get_epic_issues_modern for parent JQL - Added
  test_get_epic_issues_legacy_fallback for Epic Link JQL

All 325 tests pass, coverage increased to 81.38%.


## v1.5.1 (2025-10-25)

### Bug Fixes

- Add nosec comment for assert in datetime parser
  ([`8ccc9de`](https://github.com/cdds-ab/budjira/commit/8ccc9de588800d1770167d588aff6b5dced7d60f))

Bandit was failing in CI due to B101:assert_used. The assert is safe here as it's a type narrowing
  hint for mypy, not used for control flow.


## v1.5.0 (2025-10-25)

### Documentation

- Add comprehensive development workflow specifications
  ([`1f88554`](https://github.com/cdds-ab/budjira/commit/1f88554f3507091ff61b594aa26a59dfc9675ea7))

Implements structured checklists for repeatable, high-quality development:

**New Files:** - scripts/session_start.py: Automated session start checker - Shows git status,
  recent commits, open issues, version - Provides session reminders -
  scripts/check_documentation_updates.py: Pre-commit doc reminder hook - Detects CLI/model/test
  changes - Reminds about documentation updates - Non-blocking warnings only

**CLAUDE.md Extended:** - Feature Development Lifecycle (7 phases with detailed checklists) -
  Documentation Update Matrix (when to update which docs) - Testing Requirements by Feature Type
  (CLI/Core/Models/Utils) - Definition of Done (code quality, testing, docs, release) - Quick
  Pre-Commit Checklist (manual checks) - Session Start Checklist (automated + manual) - Post-Release
  Checklist (verify, update, cleanup)

**Pre-Commit Hook:** - Added check-documentation-updates hook to .pre-commit-config.yaml - Provides
  reminders based on staged files and commit type - Always exits 0 (warnings only)

**context.md Updated:** - Session-Hinweise references new scripts - Links to CLAUDE.md workflow
  checklists

**pyproject.toml:** - Excluded scripts/ from bandit scanning (subprocess usage is intentional)

**Benefits:** - Nothing forgotten during feature development - Consistent development process -
  Automatic reminders for documentation updates - Clear Definition of Done - Repeatable quality
  standards

- Update project context to v1.4.1
  ([`f06cdc1`](https://github.com/cdds-ab/budjira/commit/f06cdc1ad8149255102c28339fd191a8368f5a48))

- Update version and release status to v1.4.1 - Document comprehensive test coverage improvements
  (72% → 79%) - Add DoR feature documentation across all sections - Update test statistics (248 →
  279 tests) - Document new modules (dor.py, dor_validator.py, editor.py) - Update coverage
  breakdown with new DoR components - Clarify semantic release workflow and version bumping rules

### Features

- Add comprehensive time tracking support
  ([`36f260f`](https://github.com/cdds-ab/budjira/commit/36f260f2ef234bce15de8cdaf72593f6a6bedf74))

Implements GitHub Issue #1 - Time Tracking Support for Issues

New Features: - Worklog management: budjira worklog add/list commands - Time estimates for issue
  creation: --original-estimate, --remaining-estimate - Time tracking for issue updates:
  --original-estimate, --remaining-estimate, --log-work - Flexible datetime parsing: support for
  "today", "yesterday", ISO formats

CLI Commands: - budjira worklog add ISSUE TIME [--comment] [--started] - budjira worklog list ISSUE
  - budjira create issue ... --original-estimate 2h --remaining-estimate 2h - budjira issue update
  ISSUE --log-work 2h --work-comment "..."

Backend: - JiraClient.get_worklogs() - Retrieve worklog entries - datetime_parser.py - Flexible
  datetime string parsing

Tests: - 51 new tests added (279 → 323 tests) - All Jira API calls mocked (no live API) - Coverage
  increased to 81.26% (+2%)

Documentation: - README.md updated with time tracking examples - AI usage prompt regenerated -
  .claude/context.md updated with v1.5.0 feature documentation


## v1.4.2 (2025-10-12)

### Bug Fixes

- Ignore SIM117 and fix RUF043 regex pattern
  ([`6abca6f`](https://github.com/cdds-ab/budjira/commit/6abca6f67f0315d4279f24bd899eb953d4558a14))

- Add SIM117 to ruff ignore list (nested with statements acceptable in tests) - Fix regex pattern in
  test to use raw string (RUF043)


## v1.4.1 (2025-10-12)

### Code Style

- Apply ruff auto-fixes to test_editor.py
  ([`f586de0`](https://github.com/cdds-ab/budjira/commit/f586de04e3a7ba8b9b1dd2127401cd04251701da))

- Combine nested with statements where possible - Apply SIM117 ruff rule fixes

### Documentation

- Add DoR templates to AI usage prompt
  ([`d359cad`](https://github.com/cdds-ab/budjira/commit/d359cad8173ecd4c564bc511b255c49edf6e72b9))

- Add comprehensive DoR Templates section with management commands - Document default templates
  (Story, Bug, Task) - Add interactive creation workflow with DoR - Include configuration and
  validation details - Add DoR workflow to Common Workflows section - Update workflow numbering (now
  10 workflows)

This ensures AI assistants (like ClaudePM) can discover and use the DoR template feature for better
  issue quality.

### Testing

- Add comprehensive tests for DoR feature
  ([`107d1e1`](https://github.com/cdds-ab/budjira/commit/107d1e15994a7c7e1786ef929e944b0ae12e27ec))

- Add 17 tests for DoR CLI commands (list, show, edit, validate) - Add 14 tests for editor utility
  (open_editor, validation loop) - Add 7 tests for DoR integration in create command - Fix test
  isolation issues in validate test - Improve DoR CLI coverage from 15% to 92% - Improve editor
  utility coverage from 24% to 97% - Improve create command coverage from 81% to 92% - Total
  coverage increased from 72% to 79% (279 tests passing)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>


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
