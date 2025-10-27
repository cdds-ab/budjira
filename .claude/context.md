# Budjira Project Context

## Projekt-Übersicht

**budjira** (pronounced "buddy-ra") ist ein CLI-Tool für effiziente Interaktion mit Jira Cloud. Es richtet sich an:
- **Entwickler**: Schneller Zugriff auf Tickets, Time Tracking, Workflow-Integration
- **AI-gestützte Projektverwaltung**: Synchronisation zwischen lokaler Dokumentation und Jira, automatisierte Updates

**Kernphilosophie**: Effiziente Kommandozeilen-Interaktion ohne Browser, AI-freundliche Workflows, Multi-Connection-Support

## Aktueller Stand

### Version & Release Status
- **Current Version**: v1.7.1 ✅ RELEASED (2025-10-27)
- **Branch**: master
- **Status**: ✅ **All features functional, CI/pre-commit perfectly synchronized**
- **Recent Releases**:
  - v1.7.1 (2025-10-27): CI/pre-commit consistency fixes (#9) 🔧
  - v1.7.0 (2025-10-26): JSON output format for automation (#8) ✨
  - v1.6.7 (2025-10-26): Fix ruff formatting in test_tempo.py 🎨
  - v1.6.6 (2025-10-26): Fix Tempo worklogs filtering by issue (#7) 🐛
  - v1.6.5 (2025-10-26): Fix Tempo issueId requirement (#5 part 2) 🐛
  - v1.6.4 (2025-10-26): Fix Tempo accountId requirement (#5 part 1) 🐛
  - v1.6.3 (2025-10-26): Fix Tempo worklogs without issue key 🐛
  - v1.6.2 (2025-10-26): Fix MyPy error in tempo error handler 🐛
  - v1.6.1 (2025-10-26): Fix Tempo setup persistence bug (#4) 🐛
  - v1.6.0 (2025-10-26): Tempo Timesheets Integration ✨
  - v1.5.5 (2025-10-25): Regex pattern fix in tests (RUF043)

### 🐛 v1.6.1-v1.6.6: Tempo Bugfixes (2025-10-26)

#### v1.6.6: Fix Tempo worklogs filtering (Bug #7) ✅
**GitHub Issue**: #7 - tempo worklogs ISSUE-KEY fails with 400 Bad Request
**Problem**: `budjira tempo worklogs AS-13` failed with 400 Bad Request from Tempo API
**Root Cause**: Same as Bug #5 - Tempo API requires numeric issueId for filtering, not issueKey
**Fix**:
- CLI now fetches issue from Jira when filtering: `issue = jira_client.client.issue(issue_key)`
- Extract numeric ID: `issue_id = int(issue.id)`
- Updated `TempoClient.get_worklogs()`: parameter `issue_key` → `issue_id`
- Updated all tests to use `issue_id`
- Added regression test: `test_tempo_worklogs_uses_issue_id_not_key`

**Impact**: Tempo worklog filtering by issue now works correctly. All Tempo commands functional.

#### v1.6.5: Fix Tempo issueId requirement (Bug #5 part 2) ✅
**GitHub Issue**: #5 - tempo log command fails with 400 Bad Request (continued)
**Problem**: After fixing accountId, still got `{"errors":[{"message":"Issue id cannot be null"}]}`
**Root Cause**: Tempo API requires numeric `issueId` (e.g., 12345), NOT string `issueKey` (e.g., "AS-13")
**User Discovery**: User tested with curl and found Tempo rejects issueKey parameter
**Fix**:
- Changed `TempoWorklogCreate` model: `issueKey: str` → `issueId: int`
- Updated `TempoClient.create_worklog()`: parameter `issue_key` → `issue_id`
- CLI now fetches issue from Jira: `issue = jira_client.client.issue(issue_key)`
- Extract numeric ID: `issue_id = int(issue.id)` (Jira returns as string)
- Updated all tests (3 files: test_tempo_e2e.py, test_client.py, test_models.py)
- Added comprehensive regression test: `test_tempo_log_uses_issue_id_not_key`

**Impact**: Tempo worklog creation now works end-to-end. Both root causes fixed.

#### v1.6.4: Fix Tempo accountId requirement (Bug #5 part 1) ✅
**GitHub Issue**: #5 - tempo log command fails with 400 Bad Request
**Problem**: `budjira tempo log PROJ-123 30m` failed with 400 Bad Request from Tempo API
**Root Cause**: Code used `current_user()` API which returns username, but Tempo API requires `accountId` from `myself()` endpoint
**Fix**:
- Changed from `jira_client.client.current_user()` to `myself()`
- Extract `accountId` from `myself()` response dict
- Updated test fixtures to mock `myself()` instead of `current_user()`
- Added regression test: `test_tempo_log_passes_correct_account_id`

**Impact**: Fixed first part of Bug #5 (accountId), but issueId still missing

#### v1.6.3: Fix Tempo worklogs without issue key
**Problem**: Pydantic ValidationError when Tempo API returns worklogs without `issue.key` field
**Root Cause**: Some worklogs (e.g., general time entries) may not be linked to a Jira issue
**Fix**:
- Made `TempoIssue.key` optional in models
- Display "N/A" in worklogs table when key is missing
- Added 2 regression tests

#### v1.6.2: Fix MyPy truthy-function error
**Problem**: `if typer.Option:` check always True, caused mypy error in CI
**Fix**: Removed incorrect condition, always show debug hint on unexpected errors

#### v1.6.1: Fix Tempo setup persistence (Bug #4) ✅
**GitHub Issue**: #4 - Tempo setup succeeds but integration remains disabled
**Problem**: `budjira connect tempo-setup` succeeded but `tempo` commands failed with "Tempo is not enabled"
**Root Cause**: `tempo_enabled` field was not serialized to `connections.toml` in `save_connections()`
**Fix**:
- Added `tempo_enabled` to TOML serialization in `settings.py`
- Enhanced `connect show` to display Tempo status
- Added 4 comprehensive tests for `tempo-setup` command
- Added 2 regression tests for `tempo_enabled` persistence

**Impact**: This test would have prevented Bug #4 from reaching production

### 🔧 v1.7.1 - CI/Pre-commit Consistency (2025-10-27)
**GitHub Issue**: #9 - Critical: CI and pre-commit hooks are out of sync

**Problem**:
Pre-commit hooks passed locally but CI failed, creating dangerous inconsistency and broken developer trust.

**Root Causes**:
1. **Ruff Version Mismatch**: Pre-commit had fixed v0.8.4, CI had floating version from pyproject.toml
2. **Behavior Difference**: Pre-commit auto-formatted, CI only checked with `--check`
3. **Python Version Issue**: Hardcoded `python3.13` in pre-commit config failed in CI matrix (3.10-3.13)

**Solution Implemented**:
- **CI Workflow**: Replace individual tool steps with single `pre-commit/action@v3.0.1`
- **Pre-commit Config**: Remove `default_language_version: python: python3.13`
- **Test Fix**: Add `type: ignore` for runtime deserialization test in test_config.py

**Benefits**:
- ✅ Single source of truth (`.pre-commit-config.yaml`)
- ✅ Guaranteed consistency (if pre-commit green → CI green)
- ✅ No version drift
- ✅ Easier maintenance (update tools in one place)
- ✅ Industry standard pattern

**Commits**:
- `96a889c` - ci: use pre-commit action for consistency with local hooks
- `bdb0d5c` - fix(ci): remove hardcoded python3.13 from pre-commit config

**Files Modified**:
- `.github/workflows/ci.yml` - Replaced 4 tool steps with 1 pre-commit action
- `.pre-commit-config.yaml` - Removed hardcoded Python version
- `tests/models/test_config.py` - Fixed MyPy error

**Impact**: Rock-solid CI/pre-commit pipeline, no more "works locally but fails CI" scenarios

### ✨ v1.7.0 - JSON Output Format for Automation (2025-10-26)
**GitHub Issue**: #8 - Add JSON output format for automation/FoU reporting

**Summary**:
Implements global `--format json` flag for all list-based commands, enabling automation workflows and FoU (Forsknings- och utvecklingsavdrag) tax reporting for Swedish companies.

**Implementation**:
- New `budjira/utils/formatter.py` module with OutputFormatter utility
- Global `--format`/`-f` flag stored in Typer context
- Custom JSON serializer handling Pydantic models, datetime/date, Enums
- `JiraClient.get_issue_epic()` method with modern/legacy fallback
- Epic information caching to minimize API calls
- Auto-suppress banner/header when JSON format selected

**Features**:
- ✅ Global `--format` flag (table|json) for all commands
- ✅ OutputFormatter with custom JSON serializer
- ✅ `tempo worklogs` JSON output with epic_key/epic_name fields
- ✅ In-memory epic caching (1 API call for multiple worklogs on same issue)
- ✅ Optional `--no-epic` flag for performance mode
- ✅ Machine-readable output for reporting/automation

**JSON Output Format Example**:
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

**Tests**:
- 26 new tests total (373 → 399 tests)
- Test coverage: **81.09%** (maintained >70% requirement)
- v1.7.0 tests:
  - `tests/utils/test_formatter.py` - 22 tests, 90% coverage ✨ NEW
  - `tests/cli/test_tempo.py` - 4 new JSON tests (20 total, 76% coverage)
    - `test_tempo_worklogs_json_output`: Basic JSON with epic info
    - `test_tempo_worklogs_json_no_epic_flag`: Performance mode
    - `test_tempo_worklogs_json_empty_results`: Empty results
    - `test_tempo_worklogs_json_epic_caching`: Epic caching verification

**Files Created**:
- `budjira/utils/formatter.py` - OutputFormatter utility (29 statements, 90% coverage)
- `tests/utils/test_formatter.py` - Comprehensive formatter tests

**Files Modified**:
- `budjira/cli/main.py` - Added global `--format`/`-f` flag, Typer context storage
- `budjira/core/jira_client.py` - Added `get_issue_epic()` method with fallback logic
- `budjira/cli/tempo.py` - JSON output support, epic caching, `--no-epic` flag
- `tests/cli/test_tempo.py` - 4 new JSON output tests

**Documentation**:
- ✅ README.md updated with JSON Output section
- ✅ .claude/context.md updated
- ✅ .claude/ai-usage-prompt.md regenerated
- ✅ .claude/ai-prompt-supplements.md extended with JSON workflows
- ✅ CLAUDE.md updated with architecture changes

**Design Decisions**:
- **Scope**: Global flag for all commands (not just tempo worklogs)
- **Implementation**: Typer context pattern (like gh --json)
- **Epic Data**: Included by default (opt-out via --no-epic)
- **Caching**: In-memory dictionary per command invocation
- **Performance**: Minimal API calls via caching strategy

### 🎼 v1.6.0 - Tempo Timesheets Integration (2025-10-26)
**GitHub Issue**: #3 - Tempo Timesheets Integration

**Summary**:
Full enterprise-grade time tracking via Tempo Cloud API for teams using Tempo instead of standard Jira time tracking.

**Implementation**:
- New `budjira/tempo/` module with TempoClient and Pydantic models
- CLI commands: `tempo log`, `tempo worklogs`, `tempo delete-worklog`, `tempo accounts`
- Connection setup: `budjira connect tempo-setup` with separate Tempo token
- Extended Connection model with `tempo_enabled` flag
- Extended CredentialStore with key-based credential storage

**Features**:
- ✅ Worklog creation with time tracking (hours, minutes, datetime)
- ✅ Worklog listing with filters (date range, issue, project)
- ✅ Worklog deletion (with confirmation)
- ✅ Tempo Accounts listing for billing
- ✅ Secure Tempo token storage (separate from Jira tokens)
- ✅ Full Tempo Cloud API v4 support
- ✅ Rich Console output with tables

**Tests** (updated with v1.6.1-v1.7.0):
- 74 new tests total since v1.5.5 (325 → 399 tests)
- Test coverage: **81.09%** (maintained >70% requirement)
- v1.7.0 tests:
  - `tests/utils/test_formatter.py` - 22 new tests, 90% coverage ✨ NEW
  - `tests/cli/test_tempo.py` - 4 new JSON tests (20 total, 76% coverage)
- v1.6.0-v1.6.6 tests (48 tests):
  - `tests/tempo/test_models.py` - 11 tests, 100% coverage (1 added in v1.6.3)
  - `tests/tempo/test_client.py` - 12 tests, 96% coverage
  - `tests/cli/test_tempo.py` - 20 tests, 76% coverage (8 added across v1.6.0-v1.6.6, 4 in v1.7.0)
  - Extended `tests/models/test_connection.py` - 3 new tests
- v1.6.1 tests:
  - `tests/config/test_settings.py` - 2 new tests for tempo_enabled persistence
  - `tests/cli/test_connect.py` - 4 new tests for tempo-setup command
- v1.6.4 tests:
  - `tests/cli/test_tempo.py` - 1 new test for Bug #5 part 1 (test_tempo_log_passes_correct_account_id)
- v1.6.5 tests:
  - `tests/cli/test_tempo.py` - 1 new test for Bug #5 part 2 (test_tempo_log_uses_issue_id_not_key)
- v1.6.6 tests:
  - `tests/cli/test_tempo.py` - 1 new test for Bug #7 (test_tempo_worklogs_uses_issue_id_not_key)

**Files Created**:
- `budjira/tempo/__init__.py`
- `budjira/tempo/client.py` - TempoClient with REST API
- `budjira/tempo/models.py` - Pydantic models (TempoWorklog, TempoAccount)
- `budjira/cli/tempo.py` - CLI commands
- Extended: `budjira/config/credentials.py` - Added `store_credential()`, `get_credential()`
- Extended: `budjira/models/connection.py` - Added `tempo_enabled`, `get_tempo_credential_key()`

**Documentation**:
- ✅ README.md updated with Tempo section
- ✅ .claude/context.md updated (v1.6.0-v1.6.3 documented)
- ✅ .claude/ai-prompt-supplements.md updated
- ✅ .claude/ai-usage-prompt.md updated
- ✅ CLAUDE.md updated with architecture changes

### ✅ RELEASED: Recent Features (v1.5.x)

#### v1.5.3: GitHub API Rate Limit Fix (2025-10-25)
**GitHub Issue**: User-reported bug - update check showing wrong version

**Changes**:
- Added optional GitHub token authentication for update checks
- Supports `GITHUB_TOKEN` or `GH_TOKEN` environment variables
- Improved error messages for rate limiting scenarios
- Better logging for diagnostics
- Avoids 60 req/hour limit (→ 5000 req/hour with auth)

#### v1.5.2: Epic Linking Compatibility (2025-10-25)
**GitHub Issue**: #2 - Epic Link field not found

**Changes**:
- Support for both modern (parent field) and legacy (Epic Link) approaches
- Two-step fallback: Try modern first, fallback to legacy if needed
- Works with team-managed AND company-managed projects
- Comprehensive tests for both scenarios

#### v1.5.0: Time Tracking Feature (2025-10-25)
**GitHub Issue**: #1 - Feature Request: Time Tracking Support for Issues

**Features**:

#### Neue Dateien (implementiert + getestet):
1. **`budjira/utils/datetime_parser.py`** - Flexible datetime parsing
   - Unterstützt: ISO format, "today", "yesterday", YYYY-MM-DD
   - 19 comprehensive tests in `tests/utils/test_datetime_parser.py`

2. **`budjira/cli/worklog.py`** - Worklog CLI commands
   - `budjira worklog add ISSUE TIME [--comment] [--started]`
   - `budjira worklog list ISSUE`
   - 17 comprehensive tests in `tests/cli/test_worklog.py`

#### Erweiterte Features:
3. **Issue Creation mit Time Tracking**
   - `--original-estimate` flag (e.g., 2h, 30m)
   - `--remaining-estimate` flag
   - 4 neue Tests in `tests/cli/test_create.py`

4. **Issue Update mit Time Tracking**
   - `--original-estimate` flag
   - `--remaining-estimate` flag
   - `--log-work TIME` flag
   - `--work-comment TEXT` flag
   - 7 neue Tests in `tests/cli/test_issue.py`

5. **Backend Extensions**
   - `JiraClient.get_worklogs()` - Retrieve worklog entries
   - 4 neue Tests in `tests/core/test_jira_client.py`

**Implementierte Features:**
- Worklog add/list commands
- Time estimates bei issue creation/update
- Datetime parser (ISO, today, yesterday)
- Time parser (1h, 30m, 2h30m, 1.5h)

**Statistiken:**
- Neue Code-Files: 2 (`datetime_parser.py`, `worklog.py`)
- Neue Test-Files: 2 (`test_datetime_parser.py`, `test_worklog.py`)
- Neue Tests: 51 (279 → 323 tests)
- Coverage: 81.26% (+2% von 79%)

---

### Release v1.4.1 (Service Release)
**Änderungen**:
- ✅ **31 neue Tests** hinzugefügt (248 → 279 Tests)
- ✅ **Coverage** von 72% auf 79% erhöht (+7%)
- ✅ **DoR CLI Coverage**: 15% → 92% (+77%)
- ✅ **Editor Utility Coverage**: 24% → 97% (+73%)
- ✅ **Create Command Coverage**: 81% → 92% (+11%)
- ✅ AI Usage Prompt aktualisiert mit DoR-Dokumentation
- ✅ Ruff-Konfiguration fixes (SIM117 ignore, RUF043 regex fix)

**Artifacts**:
- `budjira-1.4.1-py3-none-any.whl`
- `budjira-1.4.1.tar.gz`

### Release v1.4.0 (Major Feature Release)
**Features**:
- ✅ **Definition of Ready (DoR) Templates**: Vollständige Implementierung
- ✅ **Issue Updates**: Status transitions, field updates, label management
- ✅ **Epic Management**: Link to epic, view epic progress

## Architektur

### Technologie-Stack
```yaml
Language: Python 3.10+
Package Manager: uv (Astral)
CLI Framework: Typer
Output: Rich (tables, colors, formatting)
Validation: Pydantic v2
Jira API: jira-python library
Config Storage: XDG Base Directory Spec (~/.config/budjira/)
Testing: pytest + pytest-cov (362 tests, 79.5% coverage)
Linting: ruff (formatting + linting)
Type Checking: mypy (strict mode)
Security: bandit
Commit Convention: Conventional Commits (enforced by commitizen)
Versioning: Semantic Release (automatic from commits)
CI/CD: GitHub Actions
```

### Modul-Struktur
```
budjira/
├── __init__.py              # Version, Metadaten (__version__ = "1.7.0")
├── cli/                     # Command-line interface
│   ├── main.py             # Haupteinstiegspunkt, App-Setup (+ global --format flag)
│   ├── ai.py               # AI usage prompt generation
│   ├── connect.py          # Connection management commands (+ tempo-setup)
│   ├── create.py           # Issue creation (interactive + non-interactive + DoR + time estimates)
│   ├── dor.py              # DoR template management (list, show, edit, validate)
│   ├── epic.py             # Epic management commands
│   ├── issue.py            # Issue update commands (+ time tracking + worklog)
│   ├── search.py           # Issue search (JQL + Filter)
│   ├── tempo.py            # Tempo Timesheets commands (log, worklogs, accounts, JSON output) ✨ v1.6.0/v1.7.0
│   ├── update.py           # Self-update command
│   └── worklog.py          # Worklog commands (add, list)
├── core/                    # Core business logic
│   └── jira_client.py      # Jira API wrapper (+ get_worklogs, get_issue_epic) ✨ v1.7.0
├── tempo/                   # Tempo Timesheets integration ✨ v1.6.0
│   ├── __init__.py         # Tempo module exports
│   ├── client.py           # TempoClient - REST API integration
│   └── models.py           # Pydantic models (TempoWorklog, TempoAccount, etc.)
├── models/                  # Pydantic data models
│   ├── connection.py       # Connection, ConnectionList (+ tempo_enabled)
│   ├── config.py           # GlobalConfig
│   ├── dor.py              # DoR templates, validation models
│   └── issue.py            # Issue, WorkLog, User, Status, IssueType, Priority
├── config/                  # Configuration management
│   ├── settings.py         # Settings singleton, TOML persistence
│   └── credentials.py      # Secure credential storage (+ store_credential, get_credential)
└── utils/                   # Utilities
    ├── banner.py           # ASCII art banner for CLI
    ├── connection.py       # Connection resolution (3-tier priority)
    ├── datetime_parser.py  # Datetime string parsing (ISO, today, yesterday)
    ├── dor_validator.py    # DoR template validation
    ├── editor.py           # Multi-line markdown editor integration
    ├── errors.py           # Custom exceptions
    ├── formatter.py        # Output formatting (JSON, table) ✨ NEW v1.7.0
    ├── time_parser.py      # Time string parsing (1h, 30m, 2h30m)
    └── version.py          # Version checking via GitHub Releases API
```

### Design Patterns

#### Connection Management (3-Tier Priority)
```python
# Resolution order:
1. --connection flag         # CLI argument (highest)
2. BUDJIRA_CONNECTION env    # Environment variable
3. active_connection config  # Global default (budjira connect use)
4. Error if none found
```

#### Configuration Storage (XDG)
```
~/.config/budjira/
├── config.toml              # Global config (active_connection, check_updates, enforce_dor)
├── connections.toml         # All connection definitions
├── credentials/             # API tokens (keyring or encrypted files)
│   └── budjira_<name>       # One file per connection
├── dor-templates.toml       # DoR templates for issue types
├── cache/                   # Optional issue cache (not yet implemented)
└── update_check.json        # Update check cache (24h TTL)
```

#### Error Handling Hierarchy
```python
BudjiraError (base)
├── ConfigError              # Configuration issues
├── ConnectionError          # Connection-related errors
├── AuthenticationError      # Auth failures (401)
├── PermissionError          # Access denied (403)
├── ValidationError          # Input validation
├── InvalidIssueError        # Issue not found (404)
└── JiraAPIError             # General API errors
```

## Implementierte Features

### 1. Connection Management (`budjira connect`)
**Status**: ✅ Fully implemented

#### Commands:
```bash
budjira connect add [NAME]         # Add new connection (interactive)
budjira connect list               # List all connections
budjira connect show [NAME]        # Show connection details
budjira connect test [NAME]        # Test connection
budjira connect remove [NAME]      # Remove connection
budjira connect use NAME           # Set default connection
budjira connect current            # Show active connection
```

#### Features:
- Interactive prompts für URL, Email, API Token, Project Key
- Secure credential storage (system keyring or encrypted file fallback)
- Connection validation bei Creation
- Multi-connection support (switch via --connection, ENV, or default)

#### Test Coverage:
- `tests/cli/test_connect.py`: 9 tests
- `tests/config/test_credentials.py`: 8 tests
- Coverage: 53% (CLI), 100% (credentials)

### 2. Issue Search (`budjira search`)
**Status**: ✅ Fully implemented

#### Usage:
```bash
# Raw JQL query
budjira search "project = PROJ AND status = 'In Progress'"

# Filter-based search
budjira search --status "In Progress" --assignee currentUser()
budjira search --project PROJ --type Bug --max 100

# Use specific connection
budjira search --connection my-connection --status Done
```

#### Features:
- JQL query support (raw oder filter-based)
- Automatic JQL building from filters (project, status, assignee, type)
- currentUser() function support (ohne Quoting)
- Rich table output mit Truncation
- Default project from connection
- Max results limit (1-1000, default 50)

#### Test Coverage:
- `tests/cli/test_search.py`: 12 tests
- Coverage: 87%

### 3. Issue Creation (`budjira create issue`)
**Status**: ✅ Fully implemented with DoR integration

#### Usage:
```bash
# Interactive mode (default) - mit DoR template option
budjira create issue
budjira create issue "Fix login bug"

# Non-interactive with all options
budjira create issue "Fix bug" --type Bug --priority High --no-interactive
budjira create issue "New feature" \
  --type Story \
  --description "Detailed description" \
  --assignee jdoe \
  --label feature --label frontend \
  --project PROJ \
  --skip-dor \
  --no-interactive
```

#### Features:
- Interactive mode: Prompts für Summary, Type, optional Description/Priority/Assignee/Labels
- **DoR Template Integration**: Automatisches Angebot von DoR-Templates bei interaktiver Erstellung
- Non-interactive mode: Alle Felder via CLI flags
- Rich console output mit Issue URL
- Label support (multiple --label flags)
- Project override (falls nicht connection default)
- Validation: Summary + Type required in non-interactive mode
- `--skip-dor` flag: Skip DoR validation

#### Test Coverage:
- `tests/cli/test_create.py`: 17 tests (inkl. 7 DoR-Tests)
- Coverage: 92%

### 4. Definition of Ready (DoR) Templates (`budjira dor`)
**Status**: ✅ Fully implemented (v1.4.0)

#### Commands:
```bash
budjira dor list               # List all DoR templates
budjira dor show ISSUE_TYPE    # Display template for issue type
budjira dor edit ISSUE_TYPE    # Edit template in $EDITOR
budjira dor validate ISSUE_TYPE # Validate template structure
```

#### Features:
- **Default Templates**: Story, Bug, Task mit vordefinierten Sections
- **Customization**: Templates editable in $EDITOR (vim, nano, etc.)
- **Validation Levels**:
  - `strict`: Block issue creation if DoR not met
  - `warn`: Show warnings but allow creation
  - `off`: No DoR enforcement
- **Section-Based**: Templates use `## Section Name` markdown format
- **Required Sections**: Template-specific (z.B. Story: Context, User Story, Acceptance Criteria)
- **Interactive Integration**: Automatic DoR prompt during `budjira create issue`
- **Storage**: `~/.config/budjira/dor-templates.toml`

#### Implementation:
- `budjira/models/dor.py`: Models (DorTemplate, DorSection, ValidationResult)
- `budjira/cli/dor.py`: CLI commands
- `budjira/utils/dor_validator.py`: Validation logic
- `budjira/utils/editor.py`: Multi-line markdown editor integration

#### Test Coverage:
- `tests/models/test_dor.py`: 17 tests (100% coverage)
- `tests/utils/test_dor_validator.py`: 13 tests (100% coverage)
- `tests/cli/test_dor.py`: 17 tests (92% coverage)
- `tests/utils/test_editor.py`: 14 tests (97% coverage)

### 5. Issue Updates (`budjira issue update`)
**Status**: ✅ Fully implemented (v1.4.0)

#### Commands:
```bash
budjira issue update ISSUE-KEY [OPTIONS]
budjira issue transitions ISSUE-KEY    # Show available transitions
```

#### Features:
- **Status Transitions**: `--status "In Progress"`
- **Field Updates**: `--summary`, `--description`, `--priority`, `--assignee`
- **Label Management**: `--add-label TAG`, `--remove-label TAG`
- **Epic Linking**: `--epic EPIC-KEY`
- **Multiple Updates**: Combine multiple changes in one command
- **Case-Insensitive**: Status transitions (e.g., "in progress" = "In Progress")

#### Test Coverage:
- `tests/cli/test_issue.py`: 6 tests
- `tests/core/test_jira_client.py`: Extensive update/transition tests
- Coverage: 21% (CLI), 94% (JiraClient)

### 6. Epic Management (`budjira epic`)
**Status**: ✅ Fully implemented (v1.4.0)

#### Commands:
```bash
budjira epic show EPIC-KEY    # Show epic with child issues and progress
```

#### Features:
- **Progress Tracking**: X/Y issues done (percentage)
- **Child Issue Table**: All linked stories/tasks with status
- **Visual Indicators**: ✅ Done, 🔄 In Progress, 📋 To Do
- **Epic Details**: Key, summary, description, status, priority

#### Test Coverage:
- `tests/cli/test_epic.py`: 3 tests
- Coverage: 22%

### 7. Time Tracking
**Status**: ✅ Fully implemented (v1.5.0)

#### CLI Commands:
```bash
# Add worklog entry
budjira worklog add PROJ-123 2h --comment "Fixed bug"
budjira worklog add PROJ-123 3h --started "2024-10-24 14:00" --comment "Implemented feature"
budjira worklog add PROJ-123 1h --started "yesterday"

# List worklogs
budjira worklog list PROJ-123

# Create issue with time estimates
budjira create issue "Feature" --original-estimate 8h --remaining-estimate 8h

# Update time estimates
budjira issue update PROJ-123 --original-estimate 10h --remaining-estimate 5h

# Log work via issue update
budjira issue update PROJ-123 --log-work 2h --work-comment "Completed API"
```

#### Time Parser (`budjira/utils/time_parser.py`):
```python
parse_time_string("1h")      # → 60 minutes
parse_time_string("30m")     # → 30 minutes
parse_time_string("2h30m")   # → 150 minutes
parse_time_string("1.5h")    # → 90 minutes
```

#### Datetime Parser (`budjira/utils/datetime_parser.py`):
```python
parse_datetime_string("2024-10-25T14:30:00")  # ISO format
parse_datetime_string("2024-10-25 14:30")     # Space-separated
parse_datetime_string("2024-10-25")           # Date only
parse_datetime_string("today")                # Relative
parse_datetime_string("yesterday")            # Relative
```

#### Test Coverage:
- `tests/utils/test_time_parser.py`: 14 tests (100% coverage)
- `tests/utils/test_datetime_parser.py`: 19 tests (100% coverage) ✨ NEW
- `tests/cli/test_worklog.py`: 17 tests (80% coverage) ✨ NEW
- `tests/cli/test_create.py`: +4 tests for time tracking (92% total)
- `tests/cli/test_issue.py`: +7 tests for time tracking (56% total)
- `tests/core/test_jira_client.py`: +4 tests for get_worklogs() (93% total)

### 8. Self-Update (`budjira update`)
**Status**: ✅ Implemented (via curl install script)

#### Usage:
```bash
budjira update              # Interactive update
budjira update --check      # Check for updates only
budjira update --force      # Force update check (bypass cache)
```

#### Implementation:
- `budjira/utils/version.py:VersionChecker`: GitHub Releases API
- Downloads und executes `install.sh` from GitHub master branch
- 24-hour cache für update checks
- Automatic startup check (unless disabled in config)

#### Limitations:
- **Nur stable releases**: Verwendet `/releases/latest` API endpoint
- **Keine Pre-Release-Unterstützung**: User möchte aber Pre-Releases installieren können

### 9. Tempo Timesheets Integration
**Status**: ✅ Fully implemented (v1.6.0)

#### CLI Commands:
```bash
# Setup
budjira connect tempo-setup

# Log work
budjira tempo log PROJ-123 2h --comment "Development"
budjira tempo log PROJ-456 3h30m --started yesterday --comment "Meeting"

# List worklogs
budjira tempo worklogs PROJ-123
budjira tempo worklogs --from 2024-10-01 --to 2024-10-31

# Delete worklog
budjira tempo delete-worklog 12345

# List accounts
budjira tempo accounts
```

#### Features:
- Full Tempo Cloud API v4 support
- Worklog creation, listing, deletion
- Tempo Accounts management
- Secure token storage (separate from Jira)
- Date range filtering
- Rich Console output

#### Implementation:
- `budjira/tempo/client.py`: TempoClient with REST API integration
- `budjira/tempo/models.py`: Pydantic models (TempoWorklog, TempoAccount, etc.)
- `budjira/cli/tempo.py`: CLI commands
- Extended Connection model with `tempo_enabled` flag

#### Test Coverage:
- `tests/tempo/test_models.py`: 10 tests (100% coverage)
- `tests/tempo/test_client.py`: 12 tests (96% coverage)
- `tests/cli/test_tempo.py`: 12 tests (75% coverage)

### 10. AI Integration (`budjira ai usage-prompt`)
**Status**: ✅ Fully implemented with auto-generation

#### Usage:
```bash
budjira ai usage-prompt               # Display formatted guide
budjira ai usage-prompt --plain       # Output raw markdown
budjira ai usage-prompt --plain > file.md   # Save to file
```

#### Features:
- **Comprehensive Guide**: All commands with examples
- **Common Workflows**: 10 curated workflows for AI assistants
- **DoR Documentation**: Complete DoR template usage guide
- **Auto-Generation**: Hardcoded template in `budjira/cli/ai.py`
- **Pre-Commit Hook**: Warns when CLI changes but AI prompt not updated

#### Files:
- `.claude/ai-usage-prompt.md`: Generated markdown (auto-loaded by ClaudePM)
- `budjira/cli/ai.py`: Template source
- `scripts/check_ai_prompt.py`: Pre-commit validation

#### Test Coverage:
- `tests/cli/test_ai.py`: 7 tests (93% coverage)

### 11. JSON Output Format (`--format json`)
**Status**: ✅ Fully implemented (v1.7.0)

#### Usage:
```bash
# Global --format flag (works with all list-based commands)
budjira --format json tempo worklogs --from 2025-10-01 --to 2025-10-31
budjira -f json tempo worklogs PROJ-123

# Output to file for processing
budjira --format json tempo worklogs PROJ-123 > worklogs.json

# Pipe to jq for analysis
budjira --format json tempo worklogs --from 2025-10-01 | jq '.worklogs[].time_spent_seconds' | jq -s add
```

#### Features:
- **Global Flag**: `--format`/`-f` flag for all list-based commands
- **Typer Context**: Format preference stored and passed to subcommands
- **Custom Serializer**: Handles Pydantic models, datetime/date, Enums
- **Epic Information**: Includes epic_key and epic_name for worklogs
- **Epic Caching**: In-memory cache minimizes API calls
- **Performance Mode**: Optional `--no-epic` flag for faster output
- **Auto-Suppress**: Banner and headers hidden in JSON mode

#### JSON Output Structure:
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
      "description": "Testing"
    }
  ]
}
```

#### Implementation:
- `budjira/utils/formatter.py`: OutputFormatter utility
- `budjira/cli/main.py`: Global `--format` flag with Typer context
- `budjira/core/jira_client.py`: `get_issue_epic()` method
- `budjira/cli/tempo.py`: JSON output with epic caching

#### Test Coverage:
- `tests/utils/test_formatter.py`: 22 tests (90% coverage)
- `tests/cli/test_tempo.py`: 4 JSON tests (76% total coverage)

#### Use Cases:
- **Automation**: Machine-readable output for scripts and pipelines
- **FoU Reporting**: Swedish tax reporting (Forsknings- och utvecklingsavdrag)
- **Data Analysis**: Export to Excel, CSV, or BI tools
- **Integration**: Pipe to jq, Python scripts, or other tools

## Testing

### Test-Statistiken (Current: v1.7.0)
- **Total Tests**: 399 (↑ from 325 in v1.5.5, +74 total for Tempo and JSON output)
- **Coverage**: 81.09% (maintained >70% requirement)
- **Test Duration**: ~5.7 seconds
- **Framework**: pytest + pytest-cov + pytest-mock
- **Recent Additions**:
  - v1.7.0: +26 tests for JSON output (22 formatter + 4 tempo JSON)
  - v1.6.0: +37 tests for Tempo integration
  - v1.6.1: +6 tests for Tempo setup persistence (Bug #4)
  - v1.6.3: +1 test for worklogs without issue key
  - v1.6.4: +1 test for Bug #5 part 1 (accountId)
  - v1.6.5: +1 test for Bug #5 part 2 (issueId for tempo log)
  - v1.6.6: +1 test for Bug #7 (issueId for tempo worklogs)
  - v1.5.0: +51 tests for time tracking
  - v1.5.2: +6 tests for epic linking fallback

### Coverage by Module (v1.4.1)
```
budjira/config/credentials.py      100%
budjira/models/connection.py       100%
budjira/models/config.py           100%
budjira/models/dor.py              100%  ✨ NEW
budjira/models/issue.py            100%
budjira/utils/dor_validator.py     100%  ✨ NEW
budjira/utils/editor.py             97%  ✨ NEW
budjira/utils/errors.py            100%
budjira/utils/time_parser.py       100%
budjira/config/settings.py          95%
budjira/utils/banner.py             96%
budjira/cli/ai.py                   93%
budjira/cli/dor.py                  92%  ✨ NEW
budjira/cli/create.py               92%  ↑ from 81%
budjira/utils/version.py            91%
budjira/cli/search.py               87%
budjira/core/jira_client.py         94%
budjira/cli/connect.py              53%
budjira/utils/connection.py         24%
budjira/cli/epic.py                 22%
budjira/cli/issue.py                21%
```

### Test-Strategie
- **Mocking**: Alle Jira API calls gemocked (via unittest.mock)
- **Fixtures**: Shared fixtures in conftest.py (mock_connection, mock_issue)
- **CLI Testing**: Typer CliRunner für command testing
- **No Live API Calls**: Keine echten Jira-Verbindungen in Tests
- **Editor Mocking**: subprocess.run mocked für editor tests

### Test-Dateien
```
tests/
├── cli/
│   ├── test_ai.py              # AI prompt command (7 tests)
│   ├── test_connect.py         # Connection commands (9 tests)
│   ├── test_create.py          # Create command (21 tests, +4 time tracking) ✨ v1.5.0
│   ├── test_dor.py             # DoR commands (17 tests)
│   ├── test_epic.py            # Epic commands (3 tests)
│   ├── test_issue.py           # Issue update commands (13 tests, +7 time tracking) ✨ v1.5.0
│   ├── test_main.py            # Main app (3 tests)
│   ├── test_search.py          # Search command (12 tests)
│   ├── test_tempo.py           # Tempo commands (20 tests, +4 JSON tests) ✨ v1.6.0/v1.7.0
│   ├── test_worklog.py         # Worklog commands (17 tests) ✨ v1.5.0
│   └── test_update.py          # Update command
├── core/
│   └── test_jira_client.py     # JiraClient API wrapper (extensive, +4 worklog tests) ✨ v1.5.0/v1.7.0
├── models/
│   ├── test_config.py          # GlobalConfig (4 tests)
│   ├── test_connection.py      # Connection models (10 tests)
│   ├── test_dor.py             # DoR models (17 tests)
│   └── test_issue.py           # Issue models (13 tests)
├── config/
│   ├── test_credentials.py     # Credential storage (8 tests)
│   └── test_settings.py        # Settings singleton (14 tests)
├── tempo/
│   ├── test_models.py          # Tempo models (11 tests) ✨ v1.6.0
│   └── test_client.py          # TempoClient (12 tests) ✨ v1.6.0
└── utils/
    ├── test_banner.py          # Banner display (5 tests)
    ├── test_datetime_parser.py # Datetime parsing (19 tests) ✨ v1.5.0
    ├── test_dor_validator.py   # DoR validation (13 tests)
    ├── test_editor.py          # Editor utility (14 tests)
    ├── test_errors.py          # Custom exceptions (10 tests)
    ├── test_formatter.py       # Output formatting (22 tests) ✨ NEW v1.7.0
    ├── test_time_parser.py     # Time parsing (14 tests)
    └── test_version.py         # Version checker (12 tests)
```

### Pre-Commit Hooks
```yaml
- ruff (linting + formatting)
- mypy (type checking, strict mode)
- bandit (security scanning)
- pytest --cov-fail-under=70
- commitizen (conventional commit validation)
- check_ai_prompt.py (AI prompt freshness check)
- trailing whitespace, EOF, YAML/TOML validation
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. CI Workflow (`.github/workflows/ci.yml`)
**Trigger**: Push to master/develop, PRs

**Jobs**:
1. **lint-and-test** (Matrix: Python 3.10, 3.11, 3.12, 3.13)
   - Ruff linting + formatting check
   - MyPy type checking
   - Bandit security scan
   - Pytest mit 70% coverage requirement
   - Codecov upload (nur Python 3.13)

2. **build**
   - uv build (wheel + sdist)
   - Upload artifacts

#### 2. Release Workflow (`.github/workflows/release.yml`)
**Trigger**: Push to master (automatisch!)

**Jobs**:
1. **release**
   - Python Semantic Release (v9.15.2)
   - Automatic version bumping basierend auf Conventional Commits
   - CHANGELOG generation
   - GitHub Release creation
   - **PyPI publishing disabled** (commented out)

**Wichtig**: Release wird automatisch bei jedem Push auf master erstellt!

### Semantic Release Configuration

#### Version Bumping Rules:
```yaml
feat:      # → MINOR version bump (1.4.0 → 1.5.0)
fix:       # → PATCH version bump (1.4.0 → 1.4.1)
perf:      # → PATCH
style:     # → PATCH (seit v1.4.0)
test:      # → PATCH (seit v1.4.1)
refactor:  # IGNORED (no version bump)
docs:      # IGNORED
chore:     # IGNORED (außer chore(release):)
ci:        # IGNORED
build:     # IGNORED
```

#### Breaking Changes:
- `feat!:` oder `fix!:` → MAJOR version bump (1.4.0 → 2.0.0)
- Aktuell nach 1.0.0, Breaking Changes bumpen major version

#### Version Files:
```toml
version_variables = ["budjira/__init__.py:__version__"]
version_toml = ["pyproject.toml:project.version"]
```

Semantic Release aktualisiert beide Dateien automatisch.

## Dokumentation

### Existierende Dokumentation
- ✅ **README.md**: Vollständig, gut strukturiert mit Beispielen, DoR-Dokumentation
- ✅ **CLAUDE.md**: Entwickler-Guide für Claude Code
- ✅ **.claude/context.md**: Projekt-Context für Session-Kontinuität
- ✅ **.claude/ai-usage-prompt.md**: Auto-generierter AI Usage Guide
- ❌ **CONTRIBUTING.md**: "coming soon"
- ❌ **API Documentation**: "coming soon"
- ❌ **Examples**: "coming soon"

### Inline-Dokumentation
- ✅ Docstrings: Alle Funktionen und Klassen dokumentiert
- ✅ Type Hints: Vollständige Type Coverage
- ✅ CLI Help: Typer generiert automatisch aus Docstrings

### README-Qualität
- Klar strukturiert mit Emojis
- Installation instructions (curl one-liner + manual)
- Quick Start Guide mit DoR examples
- Feature overview mit Status-Flags
- Use cases für Entwickler + AI-Assistenten
- Code quality badges

## Abhängigkeiten

### Production Dependencies
```toml
jira = ">=3.8.0"                # Jira Cloud API client
typer = ">=0.12.0"              # CLI framework
rich = ">=13.7.0"               # Terminal output
pydantic = ">=2.8.0"            # Data validation
pydantic-settings = ">=2.3.0"   # Settings management
xdg-base-dirs = ">=6.0.0"       # XDG directory specification
shellingham = ">=1.5.0"         # Shell detection for Typer
tomli-w = ">=1.0.0"             # TOML writing
tomli = ">=2.0.0"               # TOML reading (Python <3.11)
requests = ">=2.31.0"           # HTTP requests (GitHub API)
```

### Development Dependencies
```toml
pytest = ">=8.3.4"
pytest-cov = ">=6.0.0"
pytest-mock = ">=3.14.0"
ruff = ">=0.8.4"                # Linting + formatting
mypy = ">=1.14.0"               # Type checking
bandit = ">=1.8.0"              # Security scanning
commitizen = ">=4.9.1"          # Commit convention
pre-commit = ">=4.0.1"          # Git hooks
python-semantic-release = ">=10.4.1"  # Automated versioning
types-requests = ">=2.32.4"     # Type stubs for requests
```

### Python Version Support
- **Minimum**: Python 3.10
- **Tested**: 3.10, 3.11, 3.12, 3.13 (CI matrix)
- **Recommended**: 3.13 (für beste Performance)

## Sicherheit

### Credential Storage
1. **System Keyring** (preferred): `keyring` library
2. **Fallback**: Encrypted file in `~/.config/budjira/credentials/`
3. Credentials niemals in Logs oder Output

### Security Scanning
- **Bandit**: Pre-commit + CI
- **Dependabot**: Automatische Dependency-Updates
- **CodeQL**: Nicht konfiguriert

### Best Practices
- API Tokens statt Passwörter
- Timeout bei API Requests (30s)
- Input validation via Pydantic
- No secrets in error messages

## Bekannte Limitierungen

### 1. Jira Cloud Only
- Jira Server / Data Center nicht unterstützt
- Grund: jira-python library optimiert für Cloud

### 2. Keine Offline-Fähigkeit (noch)
- Cache implementiert, aber nicht aktiv genutzt
- Alle Commands benötigen Internet-Verbindung

### 3. Limitierte Issue Types
- Nur Standard-Issue-Types (Bug, Task, Story, Epic, Sub-task)
- Custom issue types funktionieren, aber keine Enum-Unterstützung

### 4. Einfaches Update-Mechanism
- Update via curl install script
- Kein Rollback-Mechanismus
- Kein delta-update (kompletter re-install)

### 5. Keine Team-Features (noch)
- Keine Shared Configurations
- Keine Team-Templates
- Keine Collaboration-Features

## Nächste Schritte

### Current GitHub Issues
- No open issues ✅

### Immediate (Next Session)
- [ ] **Comment command** implementieren (wenn User benötigt)
- [ ] **Budget tracking** features (Spezifikation klären wenn User benötigt)

### Short-term (1-2 Wochen)
- [ ] **--pre flag** für `budjira update` (Pre-Release support)
- [ ] **Attachment upload/download**
- [ ] **Cache-System** aktivieren

### Medium-term (nächste Monate)
- [ ] Offline mode mit Sync
- [ ] Team collaboration features
- [ ] Dashboard/Reporting
- [ ] Sprint management

### Long-term (Roadmap)
- [ ] Integration mit anderen Tools (Git, etc.)
- [ ] Bulk operations
- [ ] Interactive issue editing
- [ ] Configuration templates

## Roadmap (aus README.md)

### Implemented ✅
- [x] Multi-connection management
- [x] Secure credential storage
- [x] Issue search (JQL and filters)
- [x] Issue creation (interactive and non-interactive)
- [x] **Definition of Ready (DoR) templates with validation** (v1.4.0)
- [x] **Issue updates (status transitions, fields, labels)** (v1.4.0)
- [x] **Epic linking and management** (v1.4.0)
- [x] **Time tracking (worklogs, time estimates)** (v1.5.0)
- [x] **Tempo Timesheets integration** (v1.6.0)
- [x] **JSON output format for automation** (v1.7.0) ✨ NEW
- [x] Self-update mechanism
- [x] Automatic update checks
- [x] AI usage prompt generation
- [x] Shell completion (bash, zsh, fish)

### Planned 📋
- [ ] Comment management
- [ ] Attachment upload/download
- [ ] Smart caching with dirty detection
- [ ] Offline mode
- [ ] Sprint management
- [ ] Dashboard/reporting commands
- [ ] Interactive issue editing
- [ ] Configuration templates
- [ ] Bulk operations
- [ ] Pre-release support in update command
- [ ] E2E Testing with Atlassian Developer Cloud (#6)

## Technische Schulden

### 1. Low CLI Coverage für Epic und Issue Commands
- `budjira/cli/epic.py`: 22% coverage
- `budjira/cli/issue.py`: 21% coverage
- **Grund**: Komplexe interaktive Workflows, schwer zu mocken
- **Lösung**: Mehr CLI-spezifische Tests mit gemockten Prompts

### 2. Connection Utility Test Coverage
- `utils/connection.py` nur 24% coverage
- **Grund**: Integration-heavy, schwer zu testen
- **Lösung**: Mehr integration tests oder mock-based unit tests

### 3. Update Mechanism Complexity
- Curl-to-bash pattern funktioniert, aber nicht ideal
- **Alternative**: Native Python install/upgrade über pip
- **Grund für aktuelles Design**: User möchte Kontrolle über Installation

## Entwicklungs-Workflow

### Etabliertes Muster
1. User identifiziert Bedarf während Nutzung in echtem Projekt
2. User beschreibt Feature-Anforderung
3. Claude implementiert Feature autonom mit Tests
4. User testet im echten Projekt
5. Bei Stabilität: User sagt **"sichere context"** oder **"aktualisiere den context"**
6. Claude aktualisiert `.claude/context.md`
7. Automatischer Release bei Push auf master (via semantic-release)

### Context Management
- `.claude/context.md`: Vollständiger Projektstatus, auto-geladen bei Session-Start
- **Trigger**: User sagt "sichere context" oder "aktualisiere den context"
- **Update**: Claude aktualisiert Datei mit aktuellem Stand
- **Post-Update**: Neue Session kann mit aktuellem Context starten

### Branch-Strategie
- **master**: Production releases (automatisch via semantic-release)
- **develop**: Optional für Pre-Releases (noch nicht genutzt)
- Aktuell: Direktes Arbeiten auf master

### Commit-Konvention
```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

**Breaking Changes**: `feat!:` oder `fix!:`

**Beispiele**:
```
feat: add worklog CLI command
feat!: remove directory-based connection lookup
fix: handle missing credentials gracefully
test: add comprehensive DoR tests
docs: update installation instructions
```

## User-Präferenzen

### Workflow
- **Sprache**: Code/Docs auf Englisch, Ansprache auf Deutsch ("duze mich")
- **Release-Philosophie**: Automatische Releases via semantic-release, Pre-Releases für Testing geplant
- **Testing**: Erst in echtem Projekt testen, dann releasen
- **Context Management**: "sichere context" oder "aktualisiere den context" bei wichtigen Milestones

### Technische Präferenzen
- **Package Manager**: uv (nicht pip/poetry)
- **Installation**: curl install script via GitHub (nicht PyPI)
- **Linting**: ruff (nicht black + flake8)
- **Type Checking**: mypy strict mode
- **Commit Convention**: Conventional Commits

### Quality Standards
- **Test Coverage**: Minimum 70%, aktuell 79%
- **Type Safety**: Strict mypy, keine `# type: ignore` ohne Grund
- **Documentation**: Docstrings für alle public APIs
- **Security**: Bandit + Dependabot

## Session-Hinweise für Claude

### Beim Session-Start
1. **Automatisch**: `.claude/context.md` ist geladen ✅
2. **Run Session Start Script**: `uv run python scripts/session_start.py`
   - Zeigt Git Status, offene Issues, Version, letzte Commits
   - Gibt automatische Reminders aus
3. Check ob neue User-Nachrichten Kontext-Updates erfordern
4. Bei Feature-Requests: Erst Architektur verstehen, dann implementieren
5. **Refer to CLAUDE.md**: Comprehensive Development Workflow & Checklists verfügbar

### Bei "sichere context" oder "aktualisiere den context"
1. Diese Datei aktualisieren mit:
   - Neuen Features/Changes
   - Updated Test-Statistiken
   - Neue offene Entscheidungen
   - Lessons learned
   - Current Version & Release Status
2. Commit mit `docs: update project context`

### Code-Richtlinien
1. **Immer Tests schreiben** (pytest, mocked, 70% minimum coverage)
2. **Type Hints überall** (mypy strict mode)
3. **Docstrings** für alle public functions
4. **Rich Console** für alle User-Outputs
5. **Error Handling** via custom Exceptions
6. **Pre-commit hooks** vor jedem Commit (automatisch via git hook)

### AI Prompt Maintenance
**WICHTIG**: Bei Änderungen an CLI-Commands oder Models:

1. **Automatischer Check**: Pre-commit hook warnt bei CLI-Änderungen
2. **Template aktualisieren**: Hardcoded template in `budjira/cli/ai.py` updaten
3. **Regenerate**: `uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md`
4. **Commit**: Mit docs: commit (nicht feat: um kein Version bump)

**Pre-Commit Hook**: `scripts/check_ai_prompt.py` prüft:
- CLI-Dateien geändert?
- AI-Prompt veraltet?
- Gibt Warnung falls Update nötig

### Testing-Richtlinien
1. **Mock alle Jira API Calls** (keine Live-Verbindungen)
2. **Fixtures** in conftest.py sharen
3. **Coverage** muss >= 70% bleiben
4. **Typer CliRunner** für CLI-Tests
5. **pytest.raises** für Exception-Tests
6. **subprocess.run mocken** für Editor-Tests

### Release-Hinweise
1. **Conventional Commits** verwenden:
   - `feat:` für neue Features (MINOR bump)
   - `fix:` für Bugfixes (PATCH bump)
   - `test:` für Test-Ergänzungen (PATCH bump)
   - `docs:` für Dokumentation (kein bump)
   - `feat!:` oder `fix!:` für Breaking Changes (MAJOR bump)
2. **Semantic Release** bumped automatisch Version
3. **Push auf master** → Auto-Release (via GitHub Actions)
4. **Release Notes**: Automatisch generiert aus Commit-Messages

---

**Letzte Aktualisierung**: 2025-10-27 (nach Issue #9 - v1.7.1 released)
**Nächste Aktualisierung**: Bei "sichere context" oder signifikanten Änderungen

**Recent Session Summary** (2025-10-27):
- ✅ Implemented Feature #8: JSON output format for automation (v1.7.0 ✅ RELEASED)
  - Global `--format json` flag for all list-based commands
  - OutputFormatter utility with custom JSON serializer
  - JiraClient.get_issue_epic() method with modern/legacy fallback
  - Tempo worklogs JSON output with epic_key/epic_name fields
  - In-memory epic caching to minimize API calls
  - Optional --no-epic flag for performance mode
- ✅ Fixed Issue #9: CI/pre-commit consistency (v1.7.1 ✅ RELEASED)
  - CI now uses `pre-commit/action@v3.0.1` for perfect sync
  - Removed hardcoded Python 3.13 from pre-commit config
  - Single source of truth: `.pre-commit-config.yaml`
  - Guaranteed "pre-commit green → CI green"
- ✅ 26 new tests (373 → 399 tests)
- ✅ Test coverage: 81.09% (maintained >70% requirement)
- ✅ All documentation updated (README, CLAUDE.md, context.md, ai-usage-prompt.md)
- 📊 Status: Production-ready, rock-solid CI/pre-commit pipeline
