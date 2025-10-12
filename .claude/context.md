# Budjira Project Context

## Projekt-Übersicht

**budjira** (pronounced "buddy-ra") ist ein CLI-Tool für effiziente Interaktion mit Jira Cloud. Es richtet sich an:
- **Entwickler**: Schneller Zugriff auf Tickets, Time Tracking, Workflow-Integration
- **AI-gestützte Projektverwaltung**: Synchronisation zwischen lokaler Dokumentation und Jira, automatisierte Updates

**Kernphilosophie**: Effiziente Kommandozeilen-Interaktion ohne Browser, AI-freundliche Workflows, Multi-Connection-Support

## Aktueller Stand

### Version & Release Status
- **pyproject.toml**: 0.4.5 (letzter Release)
- **budjira/__init__.py**: 0.4.2 (veraltet, wird von semantic-release automatisch aktualisiert)
- **Branch**: master
- **Letzter Commit**: `79e6ae6` - Context Management System
- **Uncommitted Changes**: Keine
- **Ready to Push**: Ja (2 Commits bereit)

### Release-Verlauf (letzte 10 Commits)
```
79e6ae6 docs: add context management system for session continuity
7018e57 feat!: implement Jira core functionality and refactor connection model
ad09bae fix: correct semantic-release version_variable config
5490f18 chore(release): bump version to 0.4.5
fed58c2 fix: correct semantic-release version_variable config
1d287b4 chore(release): bump version to 0.4.4
5d8d074 fix: add style commits to patch version bump tags
bc4da30 style: fix ruff formatting in main.py
259fa76 chore(release): bump version to 0.4.3
9bf69eb fix: use dynamic version in banner tests and update dependencies
```

**Breaking Change noch nicht released**: Commit `7018e57` enthält Breaking Changes (Connection Model Refactoring), ist aber noch nicht gepusht/released.

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
Testing: pytest + pytest-cov (158 tests, 80% coverage)
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
├── __init__.py              # Version, Metadaten (__version__ = "0.4.2")
├── cli/                     # Command-line interface
│   ├── main.py             # Haupteinstiegspunkt, App-Setup
│   ├── connect.py          # Connection management commands
│   ├── search.py           # Issue search (JQL + Filter)
│   ├── create.py           # Issue creation (interactive + non-interactive)
│   └── update.py           # Self-update command
├── core/                    # Core business logic
│   └── jira_client.py      # Jira API wrapper mit Error Handling
├── models/                  # Pydantic data models
│   ├── connection.py       # Connection, ConnectionList
│   ├── config.py           # GlobalConfig
│   └── issue.py            # Issue, WorkLog, User, Status, IssueType, Priority
├── config/                  # Configuration management
│   ├── settings.py         # Settings singleton, TOML persistence
│   └── credentials.py      # Secure credential storage (keyring fallback to file)
└── utils/                   # Utilities
    ├── banner.py           # ASCII art banner for CLI
    ├── connection.py       # Connection resolution (3-tier priority)
    ├── errors.py           # Custom exceptions
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

**Breaking Change in 7018e57**:
- **Alt**: Directory-based (connection.project_root identifizierte Connections)
- **Neu**: Name-based (connection.name identifiziert Connections)
- **Rationale**: User wollte unabhängig vom Verzeichnis arbeiten, Connection per Shell-Session wechseln können

#### Configuration Storage (XDG)
```
~/.config/budjira/
├── config.toml              # Global config (active_connection, check_updates)
├── connections.toml         # All connection definitions
├── credentials/             # API tokens (keyring or encrypted files)
│   └── budjira_<name>       # One file per connection
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
budjira connect use NAME           # Set default connection (NEW in 7018e57)
budjira connect current            # Show active connection (NEW in 7018e57)
```

#### Features:
- Interactive prompts für URL, Email, API Token, Project Key
- Secure credential storage (system keyring or encrypted file fallback)
- Connection validation bei Creation
- Multi-connection support (switch via --connection, ENV, or default)

#### Test Coverage:
- `tests/cli/test_connect.py`: All commands tested
- `tests/config/test_credentials.py`: Credential storage tested
- Mock-based (keine Live-Jira-Calls)

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

#### Implementation:
- `budjira/cli/search.py`: CLI command
- `budjira/core/jira_client.py:search_issues()`: API wrapper
- Error handling: InvalidJQL, PermissionError, NoResults

#### Test Coverage:
- `tests/cli/test_search.py`: 13 tests covering all scenarios
- Mocked JiraClient responses

### 3. Issue Creation (`budjira create issue`)
**Status**: ✅ Fully implemented

#### Usage:
```bash
# Interactive mode (default)
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
  --no-interactive
```

#### Features:
- Interactive mode: Prompts für Summary, Type, optional Description/Priority/Assignee/Labels
- Non-interactive mode: Alle Felder via CLI flags
- Rich console output mit Issue URL
- Label support (multiple --label flags)
- Project override (falls nicht connection default)
- Validation: Summary + Type required in non-interactive mode

#### Implementation:
- `budjira/cli/create.py`: CLI command mit Rich Prompts
- `budjira/core/jira_client.py:create_issue()`: API wrapper
- `budjira/models/issue.py`: IssueType, Priority enums

#### Test Coverage:
- `tests/cli/test_create.py`: 12 tests (interactive + non-interactive)
- Mocked Prompts und JiraClient

### 4. Time Tracking (`budjira/core/jira_client.py:add_worklog()`)
**Status**: ⚠️ Backend implemented, CLI command missing

#### Backend Implementation:
```python
client.add_worklog(
    issue_key="PROJ-123",
    time_spent_minutes=120,
    comment="Fixed authentication bug",
    started=datetime(2025, 10, 10, 14, 0)
)
```

#### Time Parser (`budjira/utils/time_parser.py`):
```python
parse_time_string("1h")      # → 60 minutes
parse_time_string("30m")     # → 30 minutes
parse_time_string("2h30m")   # → 150 minutes
parse_time_string("1.5h")    # → 90 minutes
```

**TODO**: CLI command `budjira worklog ISSUE-123 --time 2h30m --comment "..."` fehlt noch

#### Test Coverage:
- `tests/utils/test_time_parser.py`: Full coverage für Parser
- `tests/core/test_jira_client.py`: Mocked add_worklog tests

### 5. Self-Update (`budjira update`)
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

**Pending Decision**: `--pre` flag implementieren oder manuelle pip-Installation nutzen?

### 6. Configuration (`~/.config/budjira/config.toml`)
**Status**: ✅ Implemented

#### GlobalConfig Model:
```python
class GlobalConfig:
    active_connection: str | None = None  # Default connection (set via `budjira connect use`)
    check_updates: bool = True            # Auto-check on startup
    log_level: str = "INFO"
    cache_enabled: bool = False           # Global cache toggle (not yet used)
```

#### Persistence:
- TOML format via `tomli` (read) und `tomli-w` (write)
- Auto-created on first run
- Atomic writes (write to temp, then rename)

## Testing

### Test-Statistiken
- **Total Tests**: 158
- **Coverage**: 79.73% (requirement: 70% minimum)
- **Test Duration**: ~2 seconds
- **Framework**: pytest + pytest-cov + pytest-mock

### Coverage by Module
```
budjira/config/credentials.py      100%
budjira/models/connection.py       100%
budjira/models/issue.py            100%
budjira/utils/errors.py            100%
budjira/utils/time_parser.py       100%
budjira/config/settings.py          98%
budjira/utils/banner.py             96%
budjira/utils/version.py            91%
budjira/core/jira_client.py         86%  # Main logic, mocked Jira API
budjira/utils/connection.py         24%  # Niedrig weil Integration-heavy
```

### Test-Strategie
- **Mocking**: Alle Jira API calls gemocked (via unittest.mock)
- **Fixtures**: Shared fixtures in conftest.py (mock_connection, mock_issue)
- **CLI Testing**: Typer CliRunner für command testing
- **No Live API Calls**: Keine echten Jira-Verbindungen in Tests

### Test-Dateien
```
tests/
├── cli/
│   ├── test_connect.py          # Connection commands
│   ├── test_search.py           # Search command (13 tests)
│   ├── test_create.py           # Create command (12 tests)
│   └── test_update.py           # Update command
├── core/
│   └── test_jira_client.py      # JiraClient API wrapper
├── models/
│   ├── test_connection.py       # Connection models
│   ├── test_config.py           # GlobalConfig
│   └── test_issue.py            # Issue models
├── config/
│   ├── test_credentials.py      # Credential storage
│   └── test_settings.py         # Settings singleton
└── utils/
    ├── test_time_parser.py      # Time parsing
    ├── test_version.py          # Version checker
    └── test_banner.py           # Banner display
```

### Pre-Commit Hooks
```yaml
- ruff (linting + formatting)
- mypy (type checking, strict mode)
- bandit (security scanning)
- pytest --cov-fail-under=70
- commitizen (conventional commit validation)
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
feat:      # → MINOR version bump (0.4.0 → 0.5.0)
fix:       # → PATCH version bump (0.4.0 → 0.4.1)
perf:      # → PATCH
style:     # → PATCH
refactor:  # IGNORED (no version bump)
docs:      # IGNORED
chore:     # IGNORED
ci:        # IGNORED
build:     # IGNORED
test:      # IGNORED
```

#### Breaking Changes:
- `feat!:` oder `fix!:` → MAJOR version bump (0.4.0 → 1.0.0)
- Aktuell `major_version_zero = true` → 0.x.y bleibt erhalten bis explizit auf 1.0.0 gesetzt

#### Version Files:
```toml
version_variables = ["budjira/__init__.py:__version__"]
version_toml = ["pyproject.toml:project.version"]
```

Semantic Release aktualisiert beide Dateien automatisch.

## Offene Entscheidungen & Pendenzen

### 1. Release Workflow
**Problem**: Release workflow triggert automatisch bei jedem Push auf master

**User-Wunsch**: Manuelle Kontrolle über Releases, Pre-Releases für iterative Entwicklung

**Optionen**:
```yaml
A) Ändern zu workflow_dispatch:
   on:
     workflow_dispatch:
       inputs:
         prerelease:
           description: 'Create pre-release'
           type: boolean
           default: false

B) Workflow ganz disablen, lokales semantic-release nutzen

C) Auto-Release behalten, aber branch-based pre-releases konfigurieren
   (develop → pre-release, master → stable)
```

**Workflow-Vision des Users**:
1. User testet Feature in Production
2. User sagt: "erstelle mir ein pre-release"
3. Claude erstellt Pre-Release (manual oder via workflow_dispatch)
4. User installiert via `budjira update --pre --force`

**Current Blocker**: `budjira update` unterstützt keine Pre-Releases

### 2. Pre-Release Support in Update Command
**Problem**: `VersionChecker` nutzt `/releases/latest` API, findet nur stable releases

**User-Bedarf**: Pre-Releases auf Produktionssystem installieren zum Testen

**Optionen**:
```bash
A) --pre flag implementieren:
   budjira update --pre          # Install latest pre-release
   budjira update --pre --force  # Force check

B) Manual pip workflow empfehlen:
   pip install --upgrade --pre budjira

C) Full pre-release support:
   - VersionChecker.check_for_updates(include_prerelease=True)
   - Abfrage aller releases via /releases API
   - Semantic version parsing
```

**Empfehlung**: Option A (--pre flag) für beste UX

### 3. Version Discrepancy
**Problem**: pyproject.toml zeigt 0.4.5, aber `budjira/__init__.py` zeigt 0.4.2

**Grund**: Semantic Release aktualisiert nur bei erfolgreichen Releases

**Lösung**: Nach nächstem Push + Release werden beide synchron sein

### 4. Noch nicht implementierte Features

#### 4.1 Worklog CLI Command
**Backend**: ✅ Fertig (`jira_client.add_worklog`, `time_parser`)
**CLI**: ❌ Fehlt

**Geplante Signatur**:
```bash
budjira worklog ISSUE-123 --time 2h30m [--comment "..."] [--started "2025-10-10 14:00"]
budjira worklog ISSUE-123 -t 1h -c "Fixed bug"
```

**Implementation Plan**:
1. Neue Datei `budjira/cli/worklog.py`
2. Typer command mit issue_key argument, time/comment/started options
3. Time parsing via `utils/time_parser.py`
4. Register in `main.py:app.add_typer(worklog.app, name="worklog")`

#### 4.2 Comment Command
**Status**: Nicht implementiert

**Geplant**:
```bash
budjira comment ISSUE-123 "This is a comment"
budjira comment ISSUE-123 --file comment.txt
```

#### 4.3 Issue Caching
**Status**: Models vorhanden, aber nicht genutzt

- `Connection.cache_enabled` und `Connection.cache_ttl_hours` existieren
- Cache-Verzeichnis `~/.config/budjira/cache/` geplant
- Dirty detection, offline mode

#### 4.4 Budget Tracking
**User-Anforderung**: Budget tracking features

**Noch unklar**: Genaue Spezifikation fehlt

## Roadmap (aus README.md)

### Kurzfristig (Backend fertig, CLI fehlt)
- [x] Connection management
- [x] Issue search (JQL + Filters)
- [x] Issue creation (interactive + non-interactive)
- [x] Self-update mechanism
- [ ] **Worklog command** (Backend ✅, CLI ❌)

### Mittelfristig
- [ ] Comment management
- [ ] Issue transitions (status changes)
- [ ] Interactive issue editing
- [ ] Sprint management
- [ ] Attachment upload/download

### Langfristig
- [ ] Smart caching mit dirty detection
- [ ] Offline mode
- [ ] Dashboard/reporting commands
- [ ] Configuration templates
- [ ] Bulk operations
- [ ] Shell completion enhancements
- [ ] Team collaboration features

## Entwicklungs-Workflow

### Etabliertes Muster
1. User identifiziert Bedarf während Nutzung in echtem Projekt
2. User beschreibt Feature-Anforderung
3. Claude implementiert Feature autonom mit Tests
4. User testet im echten Projekt
5. Bei Stabilität: User sagt **"sichere context"**
6. Claude aktualisiert `.claude/context.md`
7. User entscheidet über Release (manual oder automatisch)

### Context Management
- `.claude/context.md`: Vollständiger Projektstatus, auto-geladen bei Session-Start
- **Trigger**: User sagt "sichere context" bei ~85-90% Token-Budget
- **Update**: Claude aktualisiert Datei mit aktuellem Stand
- **Post-Compact**: Neue Session startet mit vollem Context

### Branch-Strategie
- **master**: Production releases (automatisch oder manual)
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
docs: update installation instructions
```

## Dokumentation

### Existierende Dokumentation
- ✅ **README.md**: Vollständig, gut strukturiert mit Beispielen
- ✅ **CLAUDE.md**: Entwickler-Guide für Claude Code
- ✅ **.claude/context.md**: Projekt-Context für Session-Kontinuität
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
- Quick Start Guide
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
- **Dependabot**: Automatische Dependency-Updates (konfiguriert?)
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

### Immediate (Ready to Push)
- [x] Context Management System implementiert
- [ ] **Push 2 commits to GitHub**: 7018e57 + 79e6ae6
- [ ] **Release-Entscheidung treffen**: Auto vs. Manual workflow

### Short-term (1-2 Sessions)
- [ ] **Worklog CLI command** implementieren (Backend fertig!)
- [ ] **--pre flag** für `budjira update` (falls entschieden)
- [ ] **First stable release** erstellen und testen

### Medium-term (nächste Wochen)
- [ ] Comment command implementieren
- [ ] Issue transitions (status changes)
- [ ] Budget tracking features (Spezifikation klären)
- [ ] Cache-System aktivieren

### Long-term (Roadmap)
- [ ] Offline mode mit Sync
- [ ] Team collaboration features
- [ ] Dashboard/Reporting
- [ ] Integration mit anderen Tools (Git, etc.)

## Technische Schulden

### 1. Version Discrepancy
- `budjira/__init__.py` manuell auf 0.4.5 aktualisieren (oder via nächstes Release)

### 2. Connection Utility Test Coverage
- `utils/connection.py` nur 24% coverage
- Grund: Integration-heavy, schwer zu testen
- Lösung: Mehr integration tests oder mock-based unit tests

### 3. Error Handling in JiraClient
- Manche Exception-Branches nicht getestet (86% coverage)
- Grund: Schwer zu simulieren ohne Live API
- Lösung: Mehr Mock-Szenarien in Tests

### 4. Update Mechanism Complexity
- Curl-to-bash pattern funktioniert, aber nicht ideal
- Alternative: Native Python install/upgrade über pip
- Grund für aktuelles Design: User möchte Kontrolle über Installation

## User-Präferenzen

### Workflow
- **Sprache**: Code/Docs auf Englisch, Ansprache auf Deutsch
- **Release-Philosophie**: Manuelle Kontrolle, Pre-Releases für Testing
- **Testing**: Erst in echtem Projekt testen, dann releasen
- **Context Management**: "sichere context" bei ~85-90% Token-Budget

### Technische Präferenzen
- **Package Manager**: uv (nicht pip/poetry)
- **Installation**: curl install script via GitHub (nicht PyPI)
- **Linting**: ruff (nicht black + flake8)
- **Type Checking**: mypy strict mode
- **Commit Convention**: Conventional Commits mit Emojis

### Quality Standards
- **Test Coverage**: Minimum 70%, aktuell 80%
- **Type Safety**: Strict mypy, keine `# type: ignore` ohne Grund
- **Documentation**: Docstrings für alle public APIs
- **Security**: Bandit + Dependabot

## Session-Hinweise für Claude

### Beim Session-Start
1. `.claude/context.md` ist automatisch geladen ✅
2. Check ob neue User-Nachrichten Kontext-Updates erfordern
3. Bei Feature-Requests: Erst Architektur verstehen, dann implementieren

### Bei "sichere context"
1. Diese Datei aktualisieren mit:
   - Neuen Features/Changes
   - Updated Test-Statistiken
   - Neue offene Entscheidungen
   - Lessons learned
2. Commit mit `docs: update project context`

### Code-Richtlinien
1. **Immer Tests schreiben** (pytest, mocked)
2. **Type Hints überall** (mypy strict mode)
3. **Docstrings** für alle public functions
4. **Rich Console** für alle User-Outputs
5. **Error Handling** via custom Exceptions
6. **Pre-commit hooks** vor jedem Commit (automatisch via git hook)

### Testing-Richtlinien
1. **Mock alle Jira API Calls** (keine Live-Verbindungen)
2. **Fixtures** in conftest.py sharen
3. **Coverage** muss >= 70% bleiben
4. **Typer CliRunner** für CLI-Tests
5. **pytest.raises** für Exception-Tests

### Release-Hinweise
1. **Conventional Commits** verwenden:
   - `feat:` für neue Features
   - `fix:` für Bugfixes
   - `feat!:` oder `fix!:` für Breaking Changes
2. **Semantic Release** bumped automatisch Version
3. **Push auf master** → Auto-Release (aktueller Stand)
4. **Pre-Releases**: Noch zu entscheiden (siehe Offene Entscheidungen)

---

**Letzte Aktualisierung**: 2025-10-12 (Session nach Compact)
**Nächste Aktualisierung**: Bei "sichere context" oder signifikanten Änderungen
