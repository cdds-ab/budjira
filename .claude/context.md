# Budjira Project Context

## Current State
- **Version:** 0.1.0 (code ready for v0.2.0)
- **Branch:** master
- **Last Commit:** 7018e57 - feat!: implement Jira core functionality and refactor connection model
- **Uncommitted:** No (all changes committed, not yet pushed)

## Recent Changes (This Session)

### Major Implementation
- Implemented core Jira functionality:
  - `JiraClient` wrapper around jira library with comprehensive error handling
  - `search` command with JQL query and filter support
  - `create` command with interactive and non-interactive modes
  - Time parser utility for worklog entries (1h, 30m, 2h30m, 1.5h formats)

### Connection Model Refactoring
- **BREAKING CHANGE:** Removed `project_root` from Connection model
- Changed from directory-based to name-based connection lookup
- Added `active_connection` field to GlobalConfig
- Implemented connection resolution utility with 3-tier priority:
  1. `--connection` flag (highest priority)
  2. `BUDJIRA_CONNECTION` environment variable
  3. Global default from config (via `budjira connect use`)

### New Commands
- `budjira connect use <name>` - Set global default connection
- `budjira connect current` - Show currently active connection
- `budjira search` - Search with JQL or filters
- `budjira create issue` - Create issues interactively or with flags

### Testing
- All 158 tests passing with 80% coverage
- Updated all test fixtures for new connection model
- Added mypy disable comments for test-specific arg-type issues

## Pending Decisions

### Release Workflow
- [ ] **Decision needed:** Auto-release on push vs manual workflow_dispatch
  - Current: `.github/workflows/release.yml` triggers on every push to master
  - User prefers: Manual pre-releases for iterative development
  - Options discussed:
    - A) Change to `workflow_dispatch` with optional pre-release flag
    - B) Disable workflow entirely, use local `semantic-release`
    - C) Keep auto but configure branch-based pre-releases

### Pre-Release Support in Update Command
- [ ] **Decision needed:** How to handle pre-releases in `budjira update`
  - Current: Only finds stable releases via `/releases/latest` API
  - User wants: Install pre-releases on production system for testing
  - Options:
    - A) Add `--pre` flag to `budjira update` command
    - B) Use `pip install --upgrade --pre budjira` workflow
    - C) Implement full pre-release support in VersionChecker

## Design Decisions Made

### Connection Management
- **Decision:** Name-based connections instead of directory-based
- **Rationale:** User wanted to work independent of directory location, switch connections per shell session
- **Impact:** Simpler, more flexible workflow; breaking change for users

### Environment Variable Priority
- **Decision:** `--connection` > `BUDJIRA_CONNECTION` > config default
- **Rationale:** CLI flag should always win, ENV for shell sessions, config for global default
- **Implementation:** `utils/connection.py:get_active_connection()`

### Installation Method
- **Decision:** GitHub releases with curl install script (NO PyPI auto-publish)
- **Rationale:** More control over releases, easier for user's internal setup
- **Update mechanism:** Downloads install.sh from GitHub, executes via curl-to-bash

### Test Coverage Strategy
- **Decision:** 70% minimum coverage enforced by pre-commit hooks
- **Rationale:** Balance between quality and development speed
- **Current:** 80% coverage achieved

## Development Workflow

### Established Pattern
1. User requests feature or identifies need while using tool
2. Claude implements feature autonomously with comprehensive tests
3. User tests in real project environment
4. When stable, user says "sichere context" and "create pre-release"
5. Claude updates this context file and creates pre-release
6. User updates production system: `budjira update --pre --force` (once implemented)

### Context Management
- This file created to maintain continuity across session boundaries
- Pattern: User says "sichere context" → Claude updates this file
- Auto-loaded by Claude Code on session start and after compact

## Next Steps

### Immediate
- [ ] Push commit 7018e57 to GitHub (when user ready)
- [ ] Decide on release workflow (auto vs manual)
- [ ] Test update mechanism with first release

### Short-term
- [ ] Implement `--pre` flag for `budjira update` command
- [ ] Add `worklog` command for time logging
- [ ] Add `comment` command for adding comments to issues
- [ ] Implement budget tracking features

### Future
- [ ] Offline cache support for issues
- [ ] Team collaboration features
- [ ] Integration with other tools (Git, etc.)

## Technical Notes

### Key Files Changed in Last Session
- `budjira/models/connection.py` - Removed project_root
- `budjira/models/config.py` - Added active_connection
- `budjira/utils/connection.py` - NEW: Connection resolution utility
- `budjira/cli/connect.py` - Complete refactor for name-based connections
- `budjira/cli/search.py` - NEW: Search command
- `budjira/cli/create.py` - NEW: Create command
- `budjira/core/jira_client.py` - NEW: Jira API wrapper
- `budjira/models/issue.py` - NEW: Issue models
- `budjira/utils/time_parser.py` - NEW: Time parsing utility

### Test Files Updated
- All connection model tests updated (removed project_root dependencies)
- New test files: test_jira_client.py, test_search.py, test_create.py, test_issue.py, test_time_parser.py
- 158 total tests, all passing

### Pre-commit Hooks Status
- ✅ All hooks passing (ruff, mypy, bandit, pytest, commitizen)
- Commit message follows conventional format with `feat!:` for breaking change

## Known Issues/TODOs
- None currently - all planned features implemented and tested
