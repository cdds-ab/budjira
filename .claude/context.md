# Budjira Project Context

## Projekt-Übersicht

**budjira** (pronounced "buddy-ra") ist ein CLI-Tool für effiziente Interaktion mit Jira Cloud. Es richtet sich an:
- **Entwickler**: Schneller Zugriff auf Tickets, Time Tracking, Workflow-Integration
- **AI-gestützte Projektverwaltung**: Synchronisation zwischen lokaler Dokumentation und Jira, automatisierte Updates

**Kernphilosophie**: Effiziente Kommandozeilen-Interaktion ohne Browser, AI-freundliche Workflows, Multi-Connection-Support

## Aktueller Stand

### Version & Release Status
- **Current Version**: v1.22.1
- **Branch**: master
- **Status**: Local-first release workflow live (cz bump owns versioning)
- **Last Update**: 2026-07-28

### Recent Releases (seit v1.8.1)

| Version | Datum | Typ | Beschreibung |
|---------|-------|-----|--------------|
| **v1.22.0** | 2026-07-28 | feat | Worklog list: real Tempo author, JSON output, author/date filters (#92); install.sh update gating (#98) |
| **v1.21.3** | 2026-07-17 | fix | Markdown→Wiki description upload (#95/#97), credential redaction in logs (#93/#94) |
| **v1.21.2** | 2026-06-01 | fix | Guard partial-field fetch in Issue parsing (#89) |
| **v1.21.1** | 2026-06-01 | fix | Team-managed boards, skip detection with --sprint-id (#87) |
| **v1.21.0** | 2026-06-01 | feat | Sub-task creation via --parent (#85), sprint move/create/start/close (#78) |
| **v1.20.0** | 2026-04-01 | feat | Worklog delete command (#77) |
| **v1.19.2** | 2026-04-01 | chore | Version bump |
| **v1.19.1** | 2026-04-01 | fix | Tempo: correct query parameter 'issueId' for GET /worklogs (#76) |
| **v1.19.0** | 2026-03-01 | feat | Auto-discover Jira project metadata (#73) |
| **v1.18.1** | 2026-03-01 | fix | Cross-instance Tempo API issue ID resolution (#72) |
| **v1.18.0** | 2026-03-01 | feat | Sprint query commands + workflow sprint overview (#71) |
| **v1.17.0** | 2026-02-24 | feat | Tempo: enforce workflow booking policy on tempo log (#70) |
| **v1.16.2** | 2026-02-23 | fix | Handle divergent git history in install script |
| **v1.16.1** | 2026-02-23 | fix | AI usage prompt for workflow profiles |
| **v1.16.0** | 2026-02-23 | feat | Workflow profiles for cross-instance Jira operations (#67) |
| **v1.14.0** | 2026-02-08 | feat | Issue linking support (#65) |
| **v1.13.1** | 2026-02-04 | fix | AI prompt documentation for Custom Fields + AI Prompts |
| **v1.13.0** | 2026-02-03 | feat | Custom fields (#64) + Connection-specific AI prompts (#63) |
| **v1.12.4** | 2026-01-15 | fix | Epic show: query both parent and Epic Link fields (#62) |
| **v1.12.3** | 2025-11-27 | fix | Tempo issue_key backfill for table output (Issue #61) |
| v1.12.2 | 2025-11-27 | refactor | Code complexity reduction (F-rated functions eliminated) |
| **v1.12.1** | 2025-11-27 | fix | Banner width calculation, Radon CI integration |
| **v1.12.0** | 2025-11-27 | feat | `--epic` flag for issue creation (Issue #58) |
| **v1.11.0** | 2025-11-27 | feat | Epic JSON output format (Issue #57) |
| **v1.10.0** | 2025-11-04 | feat | Comment command (Issue #18) |
| **v1.9.0** | 2025-11-02 | feat | Tempo worklog update command (Issue #16) |
| v1.8.1 | 2025-10-28 | fix | Tempo delete-worklog 204 No Content handling |
| v1.8.0 | 2025-10-28 | feat | Issue detail view (`budjira show`) |

---

## Neue Features seit v1.8.1

### v1.17.0: Sprint Query Commands (#71)

**Commands**: `budjira sprint list`, `budjira sprint show`, `budjira workflow sprint`

**Features:**
- **Sprint List**: List sprints for a board, filtered by state (active/future/closed)
- **Sprint Show**: View sprint issues with filters (--mine, --status, --type)
- **Workflow Sprint**: Cross-instance sprint booking overview (planning + booking)
- Board auto-detection from project (single Scrum board)
- `board_id` configuration in connections.toml
- `--unbooked` filter for partially/unbooked issues
- JSON output support for all commands
- AI usage prompt updated with sprint documentation

**New Files:**
- `budjira/models/sprint.py` - SprintState, Board, Sprint, SprintSummary models
- `budjira/services/sprints.py` - SprintService (boards, sprints, issues)
- `budjira/cli/sprint.py` - Tier 1 CLI commands
- `tests/models/test_sprint.py` - 19 model tests
- `tests/services/test_sprints.py` - 17 service tests
- `tests/cli/test_sprint.py` - 14 CLI tests

**Modified Files:**
- `budjira/models/connection.py` - Added `board_id` field
- `budjira/services/workflow.py` - Added `get_sprint_booking_overview()`
- `budjira/cli/workflow.py` - Added `workflow sprint` command
- `budjira/models/ai_prompt.py` - Added Sprint Querying section

---

### v1.15.0 (pending): Issue Delete (#66)

**Command**: `budjira issue delete ISSUE-KEY`

**Features:**
- Delete Jira issues from the CLI
- Confirmation prompt with issue summary before deletion
- `--force / -f` flag to skip confirmation
- `--delete-subtasks` flag to also delete subtasks
- `--connection / -c` flag for connection override
- Error handling: 404 → issue not found, 403 → permission denied

**Usage:**
```bash
budjira issue delete PROJ-123
budjira issue delete PROJ-123 --force
budjira issue delete PROJ-123 --delete-subtasks --force
```

**Implementation:**
- Service: `IssueService.delete()` in `budjira/services/issues.py`
- CLI: `delete` command in `budjira/cli/issue.py`
- Tests: 5 service tests + 6 CLI tests (all passing)

---

### v1.14.0: Issue Linking (#65)

**Command**: `budjira issue link ISSUE-KEY [OPTIONS]`

**Features:**
- Create issue links (relates-to, blocks, is-blocked-by, clones, duplicates)
- Multiple links in a single command
- Link type validation against Jira instance
- Links displayed in `budjira show` output

---

### v1.13.0: Custom Fields + Connection-specific AI Prompts (#63, #64)

**Custom Fields (Issue #64)**:
Connections können jetzt custom field configurations definieren, die beim Issue-Erstellen verwendet werden.

**Command**: `budjira create issue "Title" --custom name=value`

**Features:**
- Connection-level custom field configuration in TOML
- Supported field types: text, select, multi_select, user, date, number
- Automatic value formatting for Jira API
- Validation against configured options
- Interactive prompts for required fields
- Multiple fields via repeated `--custom` flags

**TOML Configuration:**
```toml
[[connections]]
name = "my-project"
# ...

[connections.custom_fields.affected_system]
field_id = "customfield_10001"
type = "select"
required = true
options = ["Infrastructure", "Application", "Database"]
label = "Affected System"
```

**Usage:**
```bash
budjira create issue "Fix bug" --custom affected_system=Infrastructure
budjira create issue "New task" --custom env=Prod --custom priority_level=High
```

---

**Connection-specific AI Prompts (Issue #63)**:
Connections können jetzt project-specific AI prompts definieren, die an den generierten Usage-Prompt angehängt werden.

**Command**: `budjira ai usage-prompt --connection my-project`

**Features:**
- `ai_prompt` field in connection configuration
- Multiline string support in TOML
- Automatic append to generated usage prompt
- `--connection` flag for usage-prompt command

**TOML Configuration:**
```toml
[[connections]]
name = "my-project"
ai_prompt = """
## Project Workflow
- Issue Types: Change, Service Request
- Required fields: Affected System, Environment
"""
```

**Usage:**
```bash
budjira ai usage-prompt --connection my-project --plain > .claude/ai-usage-prompt.md
```

---

### v1.12.0: --epic Flag für Issue Creation (Issue #58)
**Command**: `budjira create issue "Title" --epic EPIC-KEY`

**Features:**
- Direct epic linking during issue creation (no separate update needed)
- Interactive mode prompt for epic assignment
- Epic name display in creation confirmation
- Graceful error handling (issue created even if link fails)
- Works with all existing flags

**Usage:**
```bash
budjira create issue "New Story" --type Story --epic PROJ-100
budjira create issue "Bug Fix" --type Bug -e PROJ-100 --priority High
```

### v1.11.0: Epic JSON Output (Issue #57)
**Command**: `budjira --format json epic show EPIC-KEY`

**Features:**
- JSON output with epic data (key, summary, status, assignee)
- Time tracking information (original estimate, time spent, remaining)
- Story data with full details and time tracking
- Progress metrics (total, done, in_progress, todo, percent)

### v1.10.0: Comment Command (Issue #18)
**Command**: `budjira comment add ISSUE-KEY [TEXT]`

**Features:**
- Post comments to Jira issues without time logging
- Automatic editor mode when TEXT is omitted
- Multi-line comment support via $EDITOR
- Markdown formatting support
- `--editor` flag for enhanced editing experience

**Usage:**
```bash
budjira comment add PROJ-123 "Quick comment"
budjira comment add PROJ-123 --editor  # Opens $EDITOR
budjira comment add PROJ-123           # Opens $EDITOR automatically
```

### v1.9.0: Tempo Worklog Update (Issue #16)
**Command**: `budjira tempo update-worklog ID [OPTIONS]`

**Features:**
- Update existing worklogs without deletion
- Partial updates (only specify fields to change)
- Confirmation preview showing before/after changes
- `--force` flag to skip confirmation
- Preserves worklog ID and audit trail

**Usage:**
```bash
budjira tempo update-worklog 642 --started 2025-10-28
budjira tempo update-worklog 642 --time-spent 4h --comment "Revised"
budjira tempo update-worklog 642 --started yesterday --force
```

---

## Architektur-Änderungen

### Neues Services-Modul (Refactoring v1.12.x)

Die monolithische `JiraClient`-Klasse wurde in spezialisierte Services decomposed:

```
budjira/services/
├── __init__.py         # Service exports
├── base.py             # BaseService with shared functionality
├── comments.py         # CommentService - add_comment()
├── epics.py            # EpicService - get_epic_issues(), link_to_epic()
├── issues.py           # IssueService - get_issue(), create_issue(), update_issue()
├── labels.py           # LabelService - add_labels(), remove_labels()
├── metadata.py         # MetadataService - get_issue_types(), get_priorities()
├── transitions.py      # TransitionService - get_transitions(), transition_issue()
└── worklogs.py         # WorklogService - get_worklogs(), add_worklog()
```

**Benefits:**
- Reduced cyclomatic complexity (F-rated functions eliminated)
- Better maintainability and testability
- Single Responsibility Principle
- Easier to extend with new functionality

### Code Quality Improvements
- **Radon CI Integration**: Non-blocking complexity analysis in CI pipeline
- **Cyclomatic Complexity Monitoring**: Baseline metrics for refactoring
- **F-rated Functions Eliminated**: No more overly complex methods

---

## Test-Statistiken

| Metrik | Wert |
|--------|------|
| **Total Tests** | 962 |
| **Skipped Tests** | 3 |
| **Coverage** | 86.90% |
| **Test Duration** | ~14s |

### Coverage by Module (Top)
```
budjira/models/*              100%
budjira/utils/time_parser.py  100%
budjira/utils/datetime_parser.py 100%
budjira/utils/dor_validator.py 100%
budjira/tempo/models.py       100%
budjira/services/labels.py    100%
budjira/core/jira_client.py    95%
budjira/cli/show.py            94%
budjira/services/transitions.py 95%
budjira/tempo/client.py        90%
```

### Coverage Improvements Since v1.8.1
- Total: 82% → 85% (+3%)
- New tests: 423 → 738 (+315 tests)

---

## Offene GitHub Issues

### Bugs (alle released)
- **#68** - `connect test` erkennt abgelaufene Tokens nicht → Fixed v1.16.2
- **#69** - `workflow book` Tempo API 400 beim Overbooking-Check → Fixed v1.16.3
- **#72** - Cross-instance Tempo API issue ID → Fixed v1.18.1
- **#76** - Tempo query parameter 'issueId' for GET /worklogs → Fixed v1.19.1

### Feature Issues (released)
- **#71** - Sprint query commands → Released v1.18.0
- **#73** - Auto-discover Jira project metadata → Released v1.19.0

### In Progress / Open
- **#89** - `issue delete` crash beim Pre-Delete-Fetch (`PropertyHolder has no attribute`) → fix: `_parse_basic_fields` null-safe für partielle Fetches (`fields=["summary"]`), Release 1.21.2 ausstehend
- **#87** - Sprint support for team-managed projects (board type `simple`) + `--sprint-id` skips board detection → released v1.21.1
- **#85** - Sub-task creation via `--parent` → released v1.21.0 (blockierte Epic>Story>Sub-task-Buchung)
- **#78** - Sprint move + lifecycle (move/create/start/close) → implementiert, Release ausstehend
- **#74** - Local-first release workflow → erledigt (v1.20.0, cz bump)
- **#75** - AI prompt optimization (nicht gestartet)

### Refactoring-Backlog (39 Issues)

**Priority High (3):**
- #50 - No Security Scanning in CI
- #40 - No CLI Integration Tests Against Real Jira Instance
- #32 - JiraClient Has Too Many Responsibilities ✅ (addressed in v1.12.x)

**Priority Medium (6):**
- #49 - No Dependabot or Renovate Configuration
- #44 - Dependencies Not Pinned in pyproject.toml
- #39 - CLI Commands Have No Unit Tests (Only Integration)
- #36 - Tempo Client Duplicates Jira Client Error Handling
- #34 - No Request Caching for Repeated Epic/Issue Lookups
- #33 - No Retry Logic for Transient API Failures

**Priority Low (20):**
- Various code quality, documentation, and minor improvements

---

## Modul-Struktur (Aktuell)

```
budjira/
├── __init__.py              # Version: 1.19.2
├── __main__.py              # Entry point
├── cli/                     # Command-line interface
│   ├── main.py             # Main CLI app, global flags (--format, --quiet)
│   ├── ai.py               # AI usage prompt generation (+ --connection flag) ✨ UPDATED v1.13.0
│   ├── comment.py          # Comment commands
│   ├── connect.py          # Connection management (+ tempo-setup)
│   ├── create.py           # Issue creation (+ --epic, --custom flags) ✨ UPDATED v1.13.0
│   ├── dor.py              # Definition of Ready templates
│   ├── epic.py             # Epic management (+ JSON output) ✨ UPDATED v1.11.0
│   ├── issue.py            # Issue updates + delete ✨ UPDATED v1.15.0
│   ├── search.py           # Issue search (JQL + filters)
│   ├── project.py          # ✨ NEW v1.19.0 - Project metadata commands
│   ├── show.py             # Issue detail view
│   ├── sprint.py           # Sprint query commands
│   ├── tempo.py            # Tempo Timesheets (+ update-worklog)
│   ├── update.py           # Self-update commands
│   ├── workflow.py         # Workflow profiles (cross-instance)
│   └── worklog.py          # Worklog commands
├── core/                    # Core business logic (lightweight after refactoring)
│   └── jira_client.py      # Jira API wrapper (delegates to services)
├── services/                # ✨ NEW v1.12.x - Decomposed JiraClient
│   ├── base.py             # BaseService class
│   ├── comments.py         # Comment operations
│   ├── epics.py            # Epic operations
│   ├── issues.py           # Issue operations (+ delete) ✨ UPDATED v1.15.0
│   ├── labels.py           # Label operations
│   ├── metadata.py         # Metadata operations (+ project metadata v1.19.0)
│   ├── transitions.py      # Transition operations
│   ├── sprints.py          # Sprint/board operations
│   ├── workflow.py         # Cross-instance workflow operations
│   └── worklogs.py         # Worklog operations
├── tempo/                   # Tempo Timesheets integration
│   ├── client.py           # TempoClient - REST API
│   └── models.py           # Pydantic models
├── models/                  # Pydantic data models
│   ├── ai_prompt.py        # AI prompt models
│   ├── config.py           # GlobalConfig
│   ├── connection.py       # Connection, ConnectionList (+ board_id, custom_fields, ai_prompt)
│   ├── custom_field.py     # CustomFieldConfig model
│   ├── dor.py              # DoR templates
│   ├── issue.py            # Issue, Comment, Attachment, WorkLog
│   ├── project_metadata.py # ✨ NEW v1.19.0 - Project metadata models
│   └── sprint.py           # Sprint, Board, SprintSummary models
├── config/                  # Configuration management
│   ├── settings.py         # Settings singleton
│   ├── credentials.py      # Secure credential storage
│   └── metadata_cache.py   # ✨ NEW v1.19.0 - Project metadata cache
└── utils/                   # Utilities
    ├── banner.py           # ASCII art banner (fixed width calculation)
    ├── connection.py       # Connection resolution
    ├── datetime_parser.py  # Datetime parsing
    ├── dor_validator.py    # DoR validation
    ├── editor.py           # Multi-line editor
    ├── errors.py           # Custom exceptions
    ├── formatter.py        # JSON/table output
    ├── time_parser.py      # Time string parsing
    └── version.py          # Version checking
```

---

## Implementierte Features (Vollständig)

| Feature | Version | Command |
|---------|---------|---------|
| Connection Management | v0.3.0 | `budjira connect *` |
| Issue Search | v1.0.0 | `budjira search` |
| Issue Creation | v1.0.0 | `budjira create issue` |
| Issue Updates | v1.2.0 | `budjira issue update` |
| Epic Management | v1.2.0 | `budjira epic show` |
| AI Usage Prompt | v1.1.0 | `budjira ai usage-prompt` |
| DoR Templates | v1.4.0 | `budjira dor *` |
| Time Tracking | v1.5.0 | `budjira worklog *` |
| Tempo Integration | v1.6.0 | `budjira tempo *` |
| JSON Output Format | v1.7.0 | `budjira --format json` |
| Issue Detail View | v1.8.0 | `budjira show` |
| Tempo Worklog Update | v1.9.0 | `budjira tempo update-worklog` |
| Comment Command | v1.10.0 | `budjira comment add` |
| Epic JSON Output | v1.11.0 | `budjira --format json epic show` |
| Epic Flag for Create | v1.12.0 | `budjira create issue --epic` |
| Custom Fields | v1.13.0 | `budjira create issue --custom` |
| Connection AI Prompts | v1.13.0 | `budjira ai usage-prompt --connection` |
| Issue Linking | v1.14.0 | `budjira issue link` |
| Issue Delete | v1.15.0 | `budjira issue delete` |
| Workflow Profiles | v1.16.0 | `budjira workflow *` |
| Sprint Querying | v1.17.0 | `budjira sprint list`, `sprint show` |
| Sprint Management | v1.21.0 | `budjira sprint move/create/start/close` |
| Sub-task Creation | v1.21.0 | `budjira create issue --type Subtask --parent KEY` |
| Workflow Sprint | v1.17.0 | `budjira workflow sprint` |
| Booking Policy Enforcement | v1.17.0 | `budjira tempo log` (workflow) |
| Cross-instance Tempo Fix | v1.18.1 | `budjira workflow book` |
| Project Metadata | v1.19.0 | `budjira project sync/show/clear` |
| Tempo issueId Fix | v1.19.1 | `budjira tempo worklogs` |
| Worklog List JSON + Author | v1.22.0 | `budjira worklog list --format json --mine` |
| Install-Method-Aware Update | v1.22.1 | `budjira update` |
| Transition Screen Fields | pending | `budjira issue update --status X --field k=v --dry-run` |
| Description Dialect | pending | `budjira connect add --description-dialect wiki`, `create issue/issue update --description-dialect` |
| Self-Update | v0.4.0 | `budjira update` |

---

## CI/CD Pipeline

### GitHub Actions Workflows
1. **ci.yml**: Lint, test, coverage (Python 3.10-3.13)
2. **release.yml**: Semantic release on push to master
3. **issue-sanitize.yml**: Automatic sensitive data detection

### Quality Gates
- Ruff formatting + linting
- MyPy strict type checking
- Bandit security scanning
- Pytest with 70% minimum coverage
- **Radon complexity monitoring** ✨ NEW

---

## Nächste Schritte

### Immediate
- [ ] **#74**: Local-first release workflow (in Planung)
- [ ] **#75**: AI prompt optimization

### Short-term
- [ ] Dependabot/Renovate configuration (#49)
- [ ] Pin dependencies in pyproject.toml (#44)
- [ ] Retry logic for transient API failures (#33)

### Medium-term
- [ ] Request caching for repeated lookups (#34)
- [ ] Real Jira integration tests (#40)
- [ ] Security scanning in CI (#50)

---

## Session-Hinweise für Claude

### Bei Session-Start
1. `.claude/context.md` ist automatisch geladen ✅
2. Check offene GitHub Issues: `gh issue list --state open`
3. Review uncommitted changes: `git status`
4. Refer to `CLAUDE.md` für Development Workflow & Checklists

### Bei "sichere context" oder "aktualisiere context"
1. Diese Datei mit aktuellem Stand aktualisieren
2. Version, Test-Statistiken, neue Features dokumentieren
3. Commit mit `docs: update project context`

### Code-Richtlinien
1. **Tests schreiben** (pytest, 70% minimum coverage)
2. **Type Hints** überall (mypy strict)
3. **Services nutzen** für neue Jira-Funktionalität (nicht JiraClient direkt erweitern)
4. **Rich Console** für User-Output
5. **Pre-commit hooks** vor jedem Commit

---

**Letzte Aktualisierung**: 2026-04-01
**Nächste Aktualisierung**: Bei "sichere context" oder signifikanten Änderungen
