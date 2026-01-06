# Budjira Project Context

## Projekt-Übersicht

**budjira** (pronounced "buddy-ra") ist ein CLI-Tool für effiziente Interaktion mit Jira Cloud. Es richtet sich an:
- **Entwickler**: Schneller Zugriff auf Tickets, Time Tracking, Workflow-Integration
- **AI-gestützte Projektverwaltung**: Synchronisation zwischen lokaler Dokumentation und Jira, automatisierte Updates

**Kernphilosophie**: Effiziente Kommandozeilen-Interaktion ohne Browser, AI-freundliche Workflows, Multi-Connection-Support

## Aktueller Stand

### Version & Release Status
- **Current Version**: v1.12.1 (Latest: v1.12.2)
- **Branch**: master
- **Status**: Clean working tree
- **Last Update**: 2025-11-27

### Recent Releases (seit v1.8.1)

| Version | Datum | Typ | Beschreibung |
|---------|-------|-----|--------------|
| **v1.12.2** | 2025-11-27 | refactor | Code complexity reduction (F-rated functions eliminated) |
| **v1.12.1** | 2025-11-27 | fix | Banner width calculation, Radon CI integration |
| **v1.12.0** | 2025-11-27 | feat | `--epic` flag for issue creation (Issue #58) |
| **v1.11.0** | 2025-11-27 | feat | Epic JSON output format (Issue #57) |
| **v1.10.0** | 2025-11-04 | feat | Comment command (Issue #18) |
| **v1.9.0** | 2025-11-02 | feat | Tempo worklog update command (Issue #16) |
| v1.8.1 | 2025-10-28 | fix | Tempo delete-worklog 204 No Content handling |
| v1.8.0 | 2025-10-28 | feat | Issue detail view (`budjira show`) |

---

## Neue Features seit v1.8.1

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
| **Total Tests** | 488 |
| **Skipped Tests** | 3 |
| **Coverage** | 84.11% |
| **Test Duration** | ~6.8s |

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
- Total: 82% → 84% (+2%)
- New tests: 423 → 488 (+65 tests)

---

## Offene GitHub Issues

### Bug (Aktiv)
| # | Titel | Status |
|---|-------|--------|
| **#61** | Tempo worklogs show N/A for issue despite being correctly linked | Open |

**Bug #61 Details:**
- Tempo API returns `issue.key` as `None` but `issue.id` is present
- JSON output already has backfill logic (lines 264-278)
- Table output missing the same backfill
- **Workaround**: Use `--format json`

### Refactoring-Backlog (29 Issues)

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
├── __init__.py              # Version: 1.12.1
├── __main__.py              # Entry point
├── cli/                     # Command-line interface
│   ├── main.py             # Main CLI app, global flags (--format, --quiet)
│   ├── ai.py               # AI usage prompt generation
│   ├── comment.py          # Comment commands ✨ NEW v1.10.0
│   ├── connect.py          # Connection management (+ tempo-setup)
│   ├── create.py           # Issue creation (+ --epic flag) ✨ UPDATED v1.12.0
│   ├── dor.py              # Definition of Ready templates
│   ├── epic.py             # Epic management (+ JSON output) ✨ UPDATED v1.11.0
│   ├── issue.py            # Issue updates
│   ├── search.py           # Issue search (JQL + filters)
│   ├── show.py             # Issue detail view
│   ├── tempo.py            # Tempo Timesheets (+ update-worklog) ✨ UPDATED v1.9.0
│   ├── update.py           # Self-update commands
│   └── worklog.py          # Worklog commands
├── core/                    # Core business logic (lightweight after refactoring)
│   └── jira_client.py      # Jira API wrapper (delegates to services)
├── services/                # ✨ NEW v1.12.x - Decomposed JiraClient
│   ├── base.py             # BaseService class
│   ├── comments.py         # Comment operations
│   ├── epics.py            # Epic operations
│   ├── issues.py           # Issue operations
│   ├── labels.py           # Label operations
│   ├── metadata.py         # Metadata operations
│   ├── transitions.py      # Transition operations
│   └── worklogs.py         # Worklog operations
├── tempo/                   # Tempo Timesheets integration
│   ├── client.py           # TempoClient - REST API
│   └── models.py           # Pydantic models
├── models/                  # Pydantic data models
│   ├── ai_prompt.py        # ✨ NEW - AI prompt models
│   ├── config.py           # GlobalConfig
│   ├── connection.py       # Connection, ConnectionList
│   ├── dor.py              # DoR templates
│   └── issue.py            # Issue, Comment, Attachment, WorkLog
├── config/                  # Configuration management
│   ├── settings.py         # Settings singleton
│   └── credentials.py      # Secure credential storage
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
- [ ] **Bug #61**: Apply issue_key backfill to table output in tempo worklogs
- [ ] Review remaining refactoring issues

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

**Letzte Aktualisierung**: 2026-01-06
**Nächste Aktualisierung**: Bei "sichere context" oder signifikanten Änderungen
