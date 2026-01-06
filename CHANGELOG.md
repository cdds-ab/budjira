# CHANGELOG


## v1.12.3 (2026-01-06)

### Bug Fixes

- **tempo**: Apply issue_key backfill to table output
  ([#61](https://github.com/cdds-ab/budjira/pull/61),
  [`fdae77f`](https://github.com/cdds-ab/budjira/commit/fdae77f84843e2daf11493d97a402bbe7737b85b))

Apply the same issue_key backfill logic from JSON output to table output. When Tempo API returns
  null issue.key but valid issue.id, fetch the key from Jira API to display in the worklogs table.

- Always initialize JiraClient for worklogs command (needed for backfill) - Add issue_key_cache
  before output format branching (shared by both) - Implement backfill in table output loop with
  caching - Convert issue.id to string for mypy compatibility - Add regression test for Bug #61
  table output backfill - Update existing tests to include mock_jira_client fixture

Closes #61

### Documentation

- Update project context to v1.12.x
  ([`032be38`](https://github.com/cdds-ab/budjira/commit/032be38af723182c7b97b59f00ee60fa0fdea8cc))

- Document new features: v1.9.0-v1.12.0 (tempo update, comment, epic JSON, --epic flag) - Add new
  services/ module architecture from JiraClient decomposition - Update test statistics: 488 tests,
  84.11% coverage - Document Bug #61 and 29 refactoring issues in backlog - Update module structure
  with all new files


## v1.12.2 (2025-11-27)

### Refactoring

- Decompose monolithic classes for maintainability
  ([`0b25f67`](https://github.com/cdds-ab/budjira/commit/0b25f67913563d8dcdb1aeda8b92f8061328205f))

Addresses issues #19 (AI prompt templates) and #32 (service layer).

Issue #19 - AI Prompt Template System: - Extract 1100-line hardcoded string to TOML-based template
  system - Add Pydantic models (AiPromptSection, AiPromptTemplate) for type safety - Reduce
  budjira/cli/ai.py from 1156 to 56 lines (1100-line reduction) - Enable user customization via
  ~/.config/budjira/ai-prompt-template.toml

Issue #32 - Service Layer Refactoring: - Decompose 834-line JiraClient into focused service classes
  - Create BaseJiraService with standardized error handling - Add 7 domain services (IssueService,
  WorklogService, EpicService, TransitionService, LabelService, CommentService, MetadataService) -
  Refactor JiraClient to facade pattern maintaining backwards compatibility - Reduce
  budjira/core/jira_client.py from 834 to 318 lines (516-line reduction)

All tests passing (487 passed, 4 skipped). Coverage: 84.30%.

- Eliminate F-rated functions to reduce cyclomatic complexity
  ([`74a7df7`](https://github.com/cdds-ab/budjira/commit/74a7df7640ab1ec2209e6038cdd7bfda8f779fd4))

Resolves #60 - Refactor F-rated Functions to Reduce Cyclomatic Complexity Partially addresses #59 -
  Success Criterion 2 now fulfilled

Issue.from_jira_issue (F-44 → A-1): - Extract 8 specialized field parsers (_parse_basic_fields,
  _parse_user_fields, _parse_timestamp_fields, _parse_metadata_fields, _parse_epic_fields,
  _parse_time_tracking_fields, _parse_comments, _parse_attachments) - Main method now orchestrates
  parsing delegation (36 lines vs. 125 original) - Each parser has single responsibility and
  complexity A/B/C

cli/create.py:issue (F-53 → A-4): - Extract 11 input/validation/display helper functions - Main
  function reduced from 300 to 47 lines (orchestration only) - Helpers: _get_*_input, _validate_*,
  _prepare_time_tracking, _link_to_epic_if_specified, _display_created_issue

Impact: - F-rated functions: 2 → 0 (eliminated) - Average complexity: 4.66 → 4.30 (improved) - All
  tests passing: 488 passed, 3 skipped - Coverage: 84.04% (maintained)

Remaining complexity hotspots (out of scope for #60): - tempo_list_worklogs: E (33) - show_issue: E
  (32)


## v1.12.1 (2025-11-27)

### Bug Fixes

- **banner**: Calculate bottom line width dynamically using console.measure()
  ([`05950f3`](https://github.com/cdds-ab/budjira/commit/05950f3eeb45113274869d8acc78dd54d3f00e28))

The bottom line was hardcoded to 45 characters, which caused misalignment with the dynamic top line
  (version string and emoji width vary). Now uses Rich's console.measure() for accurate visual width
  calculation.

Fixes banner display across all version numbers.

### Documentation

- Add GITHUB_TOKEN setup instructions for update rate limit errors
  ([`cb38225`](https://github.com/cdds-ab/budjira/commit/cb38225864f81aea2eea3642f4bcd8bdaedae060))

Documents how to set GITHUB_TOKEN or GH_TOKEN environment variables to avoid GitHub API rate
  limiting when checking for updates.

Unauthenticated API calls are limited to 60/hour, causing 403 errors for frequent updaters or users
  behind shared IPs.

### Performance Improvements

- Add radon code complexity monitoring to CI pipeline
  ([`1d1fbbf`](https://github.com/cdds-ab/budjira/commit/1d1fbbf854090cb091befcedb63b35b2518acd5c))

Adds non-blocking Radon analysis to CI workflow for monitoring code complexity metrics (Cyclomatic
  Complexity and Maintainability Index).

Reports are informational only and never fail builds. Provides baseline metrics for identifying
  refactoring opportunities.


## v1.12.0 (2025-11-27)

### Features

- **create**: Add --epic flag for direct epic linking during issue creation
  ([`50accc2`](https://github.com/cdds-ab/budjira/commit/50accc2221688beb9f4e8e5d3d0df9a63b99b3c7))

Implements --epic flag that eliminates the need for a separate update step when linking issues to
  epics. This provides a streamlined one-command workflow for creating stories and immediately
  assigning them to epics.

Features: - --epic/-e flag to specify epic key during issue creation - Interactive mode prompt for
  epic assignment - Automatic epic linking after issue creation - Epic name display in creation
  confirmation table - Graceful error handling (issue created even if link fails) - Works with all
  existing flags (type, priority, labels, estimates)

Implementation: - Uses existing link_to_epic() method for robust modern/legacy support - Fetches
  epic name for user-friendly confirmation message - URL formatting fix (strip trailing slashes from
  connection URL) - Non-blocking: Issue creation succeeds even if epic link fails

Testing: - 4 new comprehensive tests for epic linking scenarios - Test coverage: Success, failure,
  no epic, combined with other fields - Fixed existing tests for URL format and interactive mode
  with epic prompt - Total: 466 tests passing, 84.57% overall coverage

Documentation: - README.md updated with epic flag examples and bulk creation workflows - Docstrings
  updated with epic flag examples - AI usage prompt regenerated

Use Cases: - Create multiple stories for same epic efficiently - Scripted story creation with epic
  assignment - Automation-friendly single-command workflow

Resolves: #58


## v1.11.0 (2025-11-27)

### Features

- **epic**: Add JSON output format for epic show command
  ([`4347f76`](https://github.com/cdds-ab/budjira/commit/4347f76d2501ef6e961f20e98aa004fa0b4e0bb5))

Implements --format json flag for epic show command to enable programmatic access to epic and story
  data including time tracking.

Features: - JSON output with epic data (key, summary, status, assignee, etc.) - Time tracking
  information (original estimate, time spent, remaining) - Story data with full details and time
  tracking - Progress metrics (total, done, in_progress, todo, percent) - Fallback handling for
  missing time tracking data - Error messages in JSON format when JSON mode active

Implementation: - Extended epic show command to support Typer context format flag - Added
  _format_time_seconds helper for human-readable time display - Proper URL formatting (strip
  trailing slash from connection URL) - Type-safe dict definitions for mypy strict mode compliance

Testing: - 9 comprehensive tests (6 new for JSON output) - Test coverage: 88% for epic.py - Tests
  cover: time tracking, empty results, error handling, regression - Total: 462 tests passing, 84.44%
  overall coverage

Documentation: - README.md updated with JSON output examples and use cases - Docstrings updated with
  JSON examples

Resolves: #57


## v1.10.0 (2025-11-04)

### Features

- **cli**: Add comment command for posting comments without time logging
  ([`a68228c`](https://github.com/cdds-ab/budjira/commit/a68228c4db77edc20a2966e120b0feff0752aff1))

Implements direct comment posting to Jira issues without worklog integration, addressing issue #18.

**New Features:** - `budjira comment add ISSUE-KEY [TEXT]` - Post comments to issues - Automatic
  editor mode when TEXT is omitted - Multi-line comment support via $EDITOR - Markdown formatting
  support - `--editor` flag for enhanced editing experience - `--connection` flag for multi-instance
  workflows

**Implementation:** - Added `JiraClient.add_comment()` method wrapping jira.add_comment() - New CLI
  module: `budjira/cli/comment.py` - Comprehensive error handling (404, 403, API errors) - Rich
  console output with comment preview

**Testing:** - 16 new tests (9 CLI + 7 core) - Total: 456 tests (↑ from 440) - Coverage: 83%
  (maintained above 70% requirement)

**Documentation:** - README.md: New section 8 "Add Comments" - AI usage prompt: New "Adding
  Comments" section - Feature list updated with Comment Management

Closes #18


## v1.9.0 (2025-11-02)

### Documentation

- Add GitHub issues scan requirement to session start checklist
  ([`64c8fbd`](https://github.com/cdds-ab/budjira/commit/64c8fbd20ea7684a4c37ff64309b4ad32ecc8976))

Added explicit instruction for Claude to scan and report open GitHub issues at the start of each
  session using 'gh issue list --state open'.

This ensures proactive issue management and allows user to prioritize work on existing issues versus
  new requests.

- Document automatic issue data sanitization system
  ([`46a8a67`](https://github.com/cdds-ab/budjira/commit/46a8a677cc470b3925da30f1295cedc99e8f4909))

Added comprehensive documentation for the GitHub Action-based issue sanitization system that
  automatically scans for sensitive data.

Updates: - CLAUDE.md: New Security & Privacy section with detection patterns, anonymization
  standards, and developer guidelines - context.md: Updated with implementation status and manual
  cleanup history - README.md: Expanded Security section with public repository warning and
  contributor guidelines for data sanitization

Related workflow: .github/workflows/issue-sanitize.yml

- Update context.md for v1.8.1 bugfix release
  ([`4b0841f`](https://github.com/cdds-ab/budjira/commit/4b0841f7d3af360689ee1f5cb4deacd97261de2c))

Updated project context to reflect Bug #14 fix:

context.md: - Updated current version to v1.8.1 - Added v1.8.1 to Recent Releases - Added Bug #14
  section with detailed documentation: - Problem description (204 No Content error) - Root cause
  analysis - Solution implementation - Testing results (423 tests, 82% coverage) - Completed steps
  checklist

No updates needed for: - CLAUDE.md: No architectural changes (bugfix only) - README.md: No
  user-facing command changes - AI prompt: No CLI syntax changes

### Features

- **tempo**: Add worklog update command
  ([`0119604`](https://github.com/cdds-ab/budjira/commit/01196049967bf5165d79ef5884d89da909760c3b))

Implement tempo update-worklog to edit existing Tempo worklogs without deletion. Supports updating
  time spent, start date/time, and comment with confirmation preview. More efficient than
  delete+recreate workflow and preserves worklog ID and audit trail.

Features: - Partial updates (only specify fields to change) - Confirmation preview showing
  before/after changes - --force flag to skip confirmation for automation - Preserves issueId and
  authorAccountId automatically - Single PUT API call instead of DELETE + POST

Implementation: - Add TempoWorklogUpdate Pydantic model for partial updates - Add update_worklog()
  method to TempoClient (PUT /worklogs/{id}) - Add PUT method support to _make_request() - Add tempo
  update-worklog CLI command with rich preview

Tests: - 4 new model tests for TempoWorklogUpdate (100% coverage) - 5 new client tests for
  update_worklog() (90% coverage) - 8 new CLI tests for update-worklog command (80% coverage) -
  Total: 73 tempo tests passing

Documentation: - Updated context.md with feature details - Added Tempo section to AI usage prompt
  template - Updated AI prompt workflows

Closes #16


## v1.8.1 (2025-10-28)

### Bug Fixes

- **tempo**: Handle 204 No Content response in delete-worklog
  ([`8777479`](https://github.com/cdds-ab/budjira/commit/877747966abb23634354a23f6eb902669e5bbfed))

Fixed error handling for Tempo API DELETE requests that return 204 No Content (empty body) instead
  of JSON.

Problem: - tempo delete-worklog reported error but successfully deleted worklog - "Expecting value:
  line 1 column 1 (char 0)" JSON parse error - Caused by trying to parse empty 204 response as JSON

Solution: - Check for 204 No Content before JSON parsing - Return None for empty responses - Safely
  handle 404 errors with empty bodies - Update _make_request return type to include None

Changes: - budjira/tempo/client.py: - _make_request: Check status_code 204, return None -
  _make_request: Check response.content before JSON parsing - _make_request: Safe JSON parsing in
  error handlers (try/except) - Updated return type: dict | list | None

- tests/tempo/test_client.py: - test_delete_worklog_success: Mock 204 No Content response -
  test_delete_worklog_not_found_empty_response: Test 404 with empty body

Testing: - All 423 tests pass - 82% overall coverage (above 70% requirement) - New test verifies 204
  handling - New test verifies 404 empty body handling

Closes #14

### Documentation

- Update CLAUDE.md and context.md for v1.8.0 release
  ([`4704559`](https://github.com/cdds-ab/budjira/commit/4704559c452a643e9213e2f1766c110d0b5a5663))

Updated architecture documentation to reflect Issue #12 Phase 0 implementation:

CLAUDE.md: - Added show.py to CLI module list - Updated issue.py models to include Comment and
  Attachment - Added get_issue_details() to JiraClient core methods - Marked new components with
  v1.8.0 version

context.md: - Updated current version to v1.8.0 RELEASED - Changed Feature #12 status from pending
  to RELEASED - Updated release date and version number - Marked all implementation steps as
  completed - Added CI/Release success information


## v1.8.0 (2025-10-28)

### Documentation

- Clarify Jira Cloud-only support in README
  ([`e633781`](https://github.com/cdds-ab/budjira/commit/e633781bff5a33624a93804ccc825477d99c8266))

Add explicit note that budjira supports Jira Cloud only, not Server/DC. Direct legacy users to
  alternatives (go-jira, Cloud migration).

Related to #11

- Update project context to v1.7.2 and roadmap integration
  ([`d3c17ba`](https://github.com/cdds-ab/budjira/commit/d3c17baa6b15f388c2dbc94983e492619f1b087f))

Updated context.md with: - Bug #10 completion (v1.7.2 release) - Issue #11 strategic decision (Jira
  Server wontfix) - Comprehensive roadmap integration (Issue #12) - 402 tests passing, 81.13%
  coverage maintained - Pending: Issue #12 comment (draft ready)

- Update roadmap with Issue #12 features
  ([`e9a496f`](https://github.com/cdds-ab/budjira/commit/e9a496f3d20255c88e4425f55e956fe1ef6c09d9))

Integrate all UX improvements from Issue #12 into product roadmap:

Phase 0 (v1.7.3 - NEW): - Issue Detail View (budjira show ISSUE-KEY) - 8h, CRITICAL

Phase 1 (v1.8.0 - EXTENDED): - Connection Auto-Detection - 12h, HIGH - Sprint Management, Quick
  Aliases, Comments (existing)

Phase 2 (v1.9.0 - EXTENDED): - Epic Detail View (--details flag) - 4h, MEDIUM - Issue Linking, Batch
  Time Logging (existing)

Phase 3 (v2.0.0 - EXTENDED): - Context Management - 8h, LOW - Standup Helper, Interactive Mode
  (existing)

Total investment increased from 100h to 132h (+32h). All features validated by real-world user
  feedback.

Related to #12

### Features

- **cli**: Add issue detail view command (budjira show)
  ([`b04a801`](https://github.com/cdds-ab/budjira/commit/b04a8012f6d739937645fa680a3543652e61929a))

Implements Phase 0 of Issue #12 - comprehensive issue detail view.

New Features: - Extended Issue model with epic, time tracking, comments, attachments - Added
  JiraClient.get_issue_details() for comprehensive data fetching - Created budjira show ISSUE-KEY
  command with rich formatting - Rich output with panels, tables, Markdown rendering, time/size
  formatters

Model Extensions (budjira/models/issue.py): - Comment and Attachment Pydantic models - Epic fields
  (epic_key, epic_name) - Time tracking fields (seconds: original_estimate, remaining, spent) -
  Comments and attachments lists - Fixed all optional fields to use Field(default=None, ...) for
  MyPy

Core Logic (budjira/core/jira_client.py): - get_issue_details() fetches issue with fields="*all" -
  Integrates with get_issue_epic() for parent epic information - Comprehensive error handling (404,
  403, API errors)

CLI Command (budjira/cli/show.py): - Rich Panel header with issue key and summary - Metadata table
  (type, status, priority, assignee, reporter, epic) - Time tracking table (original estimate,
  remaining, time spent) - Markdown-rendered description - Comments section with timestamps and
  authors - Attachments section with sizes and MIME types - Custom formatters:
  format_time_seconds(), format_file_size()

Testing: - 4 new tests in tests/core/test_jira_client.py::TestJiraClientGetIssueDetails - 16 new
  tests in tests/cli/test_show.py - Coverage: 94% (show.py), 88% (jira_client.py), 100% (issue.py) -
  Total: 422 tests, 82.53% overall coverage

Documentation: - README.md: Added Section 4 "View Issue Details" - AI usage prompt: Added "Viewing
  Issue Details" section - .claude/context.md: Updated with feature status and test statistics

Closes #12 (Phase 0)


## v1.7.2 (2025-10-27)

### Bug Fixes

- **tempo**: Backfill null issue_key from Jira API in worklogs JSON
  ([`479f844`](https://github.com/cdds-ab/budjira/commit/479f844a67547b698e4401e5e80e2fa0fc95e09e))

Tempo API returns issue.key as null even when worklog has valid issueId. This breaks automation
  workflows that rely on grouping worklogs by issue or epic, particularly FoU tax reporting in
  Sweden.

Solution: When issue.key is null but issue.id exists, fetch the key from

Jira API and cache the result to minimize API calls. This enables epic lookup and project filtering
  to work correctly.

Fixes #10

### Documentation

- Update all documentation for v1.7.1 CI/pre-commit consistency
  ([`63a6a73`](https://github.com/cdds-ab/budjira/commit/63a6a732a7a25fb750534fdc8a59848e228d3255))

Updated all project documentation to reflect v1.7.1 CI improvements:

README.md: - Added CI/Pre-commit Consistency to Code Quality section - Highlights single source of
  truth via pre-commit action

CLAUDE.md: - New CI/CD Pipeline Consistency section after Pre-commit Hooks - Explains v1.7.1
  implementation details - Documents benefits and testing separation

.claude/context.md: - Updated version to v1.7.1 RELEASED (2025-10-27) - Added comprehensive v1.7.1
  section with problem/solution/impact - Updated Recent Session Summary with Issue #9 resolution -
  Updated status line to reflect rock-solid CI/pre-commit pipeline

All documentation now consistent with v1.7.1 improvements.


## v1.7.1 (2025-10-27)

### Bug Fixes

- **ci**: Remove hardcoded python3.13 from pre-commit config
  ([`bdb0d5c`](https://github.com/cdds-ab/budjira/commit/bdb0d5c798263ea6e1ad5911979145d35ac833d5))

The default_language_version with python3.13 caused CI failures in the Python matrix (3.10, 3.11,
  3.12, 3.13) because pre-commit tried to find python3.13 even when running on python3.12.

Solution: Remove default_language_version to let pre-commit use

the current Python version from the CI matrix.

### Documentation

- Mark v1.7.0 as released in context.md
  ([`ea3075b`](https://github.com/cdds-ab/budjira/commit/ea3075b9f5866aaef4c4cf1cf84d11b3b101d58e))

- Update project documentation for v1.7.0 JSON output feature
  ([`d15427d`](https://github.com/cdds-ab/budjira/commit/d15427d1ce77444f426bc788328bdaae133e5513))

Updated all project documentation to reflect Feature #8 implementation:

.claude/context.md: - Updated version to v1.7.0 (pending) - Added comprehensive v1.7.0 section with
  implementation details - Updated test statistics (373 → 399 tests, 81.09% coverage) - Added JSON
  Output Format to Implementierte Features (Section 11) - Updated module structure with formatter.py
  - Updated Recent Session Summary

.claude/ai-prompt-supplements.md: - Added Workflow #8: JSON Output for Automation and Reporting -
  Added JSON Output tips in AI Assistant Tips section - Updated version tracking - Included jq
  examples and FoU reporting use cases

CLAUDE.md: - Updated architecture overview with formatter.py utility - Added Design Pattern #3:
  Global Output Formatting (Typer Context) - Added Design Pattern #4: Epic Information Caching -
  Updated Core Components with get_issue_epic() method - Updated Utils Layer with OutputFormatter

All documentation now consistent with v1.7.0 feature set.


## v1.7.0 (2025-10-26)

### Features

- **cli**: Add global JSON output format for automation
  ([`26b659b`](https://github.com/cdds-ab/budjira/commit/26b659bf41f52ee68923dd8d64e2678d089433ac))

Implements global --format flag (table|json) for all list-based commands with initial support for
  tempo worklogs. Enables FoU reporting automation for Swedish tax compliance (Forsknings- och
  utvecklingsavdrag).

Key features: - Global --format/-f flag stored in Typer context - OutputFormatter utility with
  Pydantic/datetime/Enum serialization - JiraClient.get_issue_epic() method with modern/legacy
  fallback - tempo worklogs JSON output with epic_key/epic_name fields - In-memory epic caching to
  minimize API calls - Optional --no-epic flag for performance mode - Auto-suppress banner/header in
  JSON mode

Output format for tempo worklogs: { "total": N, "worklogs": [ { "id": 123, "issue_key": "PROJ-1",
  "epic_key": "PROJ-100", "epic_name": "Epic Title", "time_spent_seconds": 3600,
  "time_spent_display": "1h", "date": "2025-10-26", "author_account_id": "...",
  "author_display_name": "Name", "description": "Work description" } ] }

Test coverage: 81.09% (399 tests passing) New tests: 22 formatter tests + 4 tempo JSON tests

Closes #8


## v1.6.7 (2025-10-26)

### Code Style

- Fix ruff formatting in test_tempo.py
  ([`5ed5f68`](https://github.com/cdds-ab/budjira/commit/5ed5f68942d17b1ab9ae47d01d8846f687ea30bb))

Fixes CI failures since commit 38387bc where test_tempo.py was not correctly formatted. The assert
  statement formatting was incorrect:

Before: assert ( call_kwargs["author_account_id"] == "557058:abc123def456" ), "error message"

After: assert call_kwargs["author_account_id"] == "557058:abc123def456", ( "error message" )

This fix resolves 4 consecutive CI failures on ruff format check.

### Documentation

- Remove misleading "In Progress" status for Smart Caching
  ([`c9cc51f`](https://github.com/cdds-ab/budjira/commit/c9cc51f4d95af0c74c3d1372e92e8209b56b351b))

Smart Caching feature was never implemented - only infrastructure skeleton exists (cache_dir,
  connection flags, CacheError class). The only actual caching is for update checks (24h TTL).

Moved "Smart caching with dirty detection" from "In Progress" to "Planned" section in both README.md
  and .claude/context.md to accurately reflect the project status.


## v1.6.6 (2025-10-26)

### Bug Fixes

- **tempo**: Use numeric issueId for worklogs filtering
  ([`7650356`](https://github.com/cdds-ab/budjira/commit/76503566127f040209ce3aa52a56738855f2fd2a))

Tempo Cloud API requires numeric issueId (e.g., 12345) not string issueKey (e.g., "AS-13") when
  filtering worklogs by issue. The CLI now fetches the issue from Jira API to extract the numeric ID
  before calling Tempo.

Fixes #7

Changes: - Changed TempoClient.get_worklogs: issue_key → issue_id parameter - CLI fetches issue from
  Jira to get numeric ID when filtering - Updated all tests to use issue_id - Added regression test:
  test_tempo_worklogs_uses_issue_id_not_key - Enhanced test_tempo_worklogs_success with issueId
  verification


## v1.6.5 (2025-10-26)

### Bug Fixes

- **tempo**: Use numeric issueId instead of issueKey for Tempo API
  ([`2ebd935`](https://github.com/cdds-ab/budjira/commit/2ebd935c40b2b98f408fb1e41c2b64095fb58f88))

Tempo Cloud API requires numeric issueId (e.g., 12345) not string issueKey (e.g., "AS-13"). The CLI
  now fetches the issue from Jira API to extract the numeric ID before calling Tempo.

Fixes #5 (second root cause)

Changes: - Changed TempoWorklogCreate model: issueKey → issueId (int) - Updated
  TempoClient.create_worklog: issue_key → issue_id parameter - CLI fetches issue from Jira to get
  numeric ID - Updated all tests to use issue_id - Added regression test:
  test_tempo_log_uses_issue_id_not_key


## v1.6.4 (2025-10-26)

### Bug Fixes

- Use Jira myself() API to get accountId for Tempo worklogs
  ([`38387bc`](https://github.com/cdds-ab/budjira/commit/38387bc5a0aaa37e171b0b0fae005310bcada5ad))

Fixed Bug #5 where tempo log failed with 400 Bad Request from Tempo API.

Root cause: Code used current_user() which returns username, but Tempo API requires accountId from
  the myself() endpoint.

Changes: - Changed from jira_client.client.current_user() to myself() - Extract accountId from
  myself() response dict - Updated test fixtures to mock myself() instead of current_user() - Added
  regression test: test_tempo_log_passes_correct_account_id

This fix enables tempo log command to work correctly: budjira tempo log PROJ-123 30m --comment
  "Development work"

Closes #5

### Documentation

- Update project context to v1.6.3 with bugfixes
  ([`93c7643`](https://github.com/cdds-ab/budjira/commit/93c76435af13317cd0f2883db3b26b6452790f8c))

- Update project context to v1.6.4 with Bug #5 fix
  ([`ee22c5b`](https://github.com/cdds-ab/budjira/commit/ee22c5b73be604532096ff0d3c0d6e42729a3f2d))


## v1.6.3 (2025-10-26)

### Bug Fixes

- Handle tempo worklogs without issue key
  ([`794c302`](https://github.com/cdds-ab/budjira/commit/794c3026c14751a87c654521153f87439b78dcd2))

Fixed ValidationError when Tempo API returns worklogs without issue.key field.

Changes: - Made TempoIssue.key optional (some worklogs may not have an issue) - Display "N/A" in
  worklogs table when issue.key is None - Added tests for worklogs without issue key

Resolves Pydantic validation error: "1 validation error for TempoWorklogList results.0.issue.key
  Field required"


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
