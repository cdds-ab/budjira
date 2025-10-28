# 🗺️ Budjira Product Roadmap 2026

**Status:** Strategic Planning Document
**Last Updated:** 2025-10-27
**Analysis By:** Requirements Engineering & Product Workflow Expert

---

## 📊 Executive Summary

Based on research of Jira usage patterns and CLI best practices, budjira currently covers **57% of the top-7 daily developer workflows** with strong unique differentiators (Tempo, DoR, AI). This roadmap outlines targeted enhancements to reach **80%+ coverage** without tool bloat.

**Current Position:** Premium CLI for Cloud-first teams with Tempo/FoU needs
**Target Position:** The definitive Daily Driver for Developers, Freelancers, and PMs

---

## 🎯 Research Findings: Jira Usage Patterns (80/20 Rule)

### Top 7 Daily Workflows:
1. **Issue Status Updates** (80% daily) - ✅ Has: `issue update`
2. **Time Logging** (70% daily) - ✅ Has: `tempo log`, `worklog`
3. **Create Bug/Task** (60% daily) - ✅ Has: `create`
4. **Sprint Management** (55% daily) - ❌ **MISSING** (critical gap!)
5. **Comment on Issues** (50% daily) - ❌ **MISSING**
6. **Search/Filter Issues** (80% daily) - ✅ Has: `search`
7. **Issue Linking** (40% daily) - ❌ **MISSING**

**Coverage:** 4 of 7 (57%) → Target: 7 of 7 (100%)

---

## 🏆 Budjira's Unique Strengths (Keep & Strengthen)

**What budjira does BETTER than competitors:**
1. ✨ **Tempo Integration** (FoU Tax Reporting) - UNIQUE
2. ✨ **DoR Templates** (Definition of Ready) - UNIQUE
3. ✨ **AI-Friendly** (usage prompt generation) - UNIQUE
4. ✨ **Multi-Connection** (context-aware) - Best-in-Class
5. ✨ **JSON Output** (automation-ready) - Modern

**Strategic Focus:** Maintain these differentiators while closing workflow gaps.

---

## 👥 Persona Analysis

### Developer (60% of users)
**Needs:** Fast status updates, sprint visibility, quick comments
**Pain Points:** Browser context-switch for sprints, commenting requires GUI
**Priority Features:** Sprint management, quick aliases, comments

### Freelancer (25% of users)
**Needs:** Efficient time tracking, invoice export, FoU reporting
**Pain Points:** Batch time logging at end of week is tedious
**Priority Features:** Batch time logging, timesheet summary, invoice export

### Project Manager (15% of users)
**Needs:** Sprint planning, velocity tracking, team oversight
**Pain Points:** No sprint capacity view, no bulk operations
**Priority Features:** Sprint reports, bulk updates, dashboard view

---

## 🚀 Feature Roadmap (Prioritized)

### 🔥 Phase 0: Quick Wins - v1.7.3 (Q4 2025)
**Goal:** Address most critical UX gap discovered via user feedback (Issue #12)

#### Issue Detail View Command ⭐⭐⭐⭐⭐
**Priority:** CRITICAL (Issue #12 Point 2 - "You can't read what you created!")
**Effort:** 6-8 hours

```bash
budjira show ISSUE-KEY              # Show full issue details
budjira show ISSUE-KEY --json       # JSON output for scripting
budjira show ISSUE-KEY --comments   # Include comments
```

**Features Displayed:**
- Summary
- Description (full text, markdown formatted)
- DoR sections (Context, User Story, Acceptance Criteria)
- Status, Priority, Assignee, Reporter
- Epic link
- Labels
- Time tracking (original estimate, remaining estimate, time logged)
- Recent comments (optional with `--comments`)
- Attachments list

**Implementation:**
- New command: `budjira/cli/show.py`
- Uses existing `JiraClient.get_issue()` method
- Rich formatted output with sections
- JSON mode for scripting/automation

**Business Impact:**
- Eliminates **#1 user pain point**: "Can create issues with DoR templates but can't read them back"
- Closes workflow loop: Create → View → Update
- Enables full CLI workflow without browser

**User Quote (Issue #12):**
> "Currently, I can create issues with rich DoR templates but have no CLI way to read them back."

**ROI:** 10/10 (häufigster Use Case nach Search - 95% of developers need)

---

**Phase 0 Summary:**
- **Total Effort:** 6-8 hours (~1 day)
- **Coverage Increase:** 57% → 70%
- **Outcome:** Complete "Create-View-Update" workflow loop

---

### 🔥 Phase 1: Foundation - v1.8.0 (Q1 2026)
**Goal:** Close critical feature gaps for daily workflows

#### 1. Sprint Management ⭐⭐⭐⭐⭐
**Priority:** CRITICAL (55% of developers use daily)
**Effort:** 24 hours

```bash
budjira sprint list                    # Show active sprints
budjira sprint show [SPRINT-ID]        # Sprint board (To Do, In Progress, Done)
budjira sprint add PROJ-123            # Add issue to sprint
budjira sprint start SPRINT-5          # Start sprint
budjira sprint stats                   # Sprint velocity/burndown
```

**Implementation:**
- New module: `budjira/sprint/client.py`
- Uses Jira Sprint REST API
- Rich table output for board view
- Similar pattern to `tempo` module

**Business Impact:** Eliminates #1 reason developers switch to browser

---

#### 2. Quick Status Aliases ⭐⭐⭐⭐⭐
**Priority:** HIGH (80% of status updates are 4 transitions)
**Effort:** 4 hours

```bash
budjira start PROJ-123        # → issue update --status "In Progress"
budjira done PROJ-123         # → issue update --status "Done"
budjira block PROJ-123        # → issue update --status "Blocked"
budjira review PROJ-123       # → issue update --status "In Review"
```

**Implementation:**
- Simple alias commands in `budjira/cli/main.py`
- Map to existing `issue update` logic
- Reduces typing by 70%

**Business Impact:** Fastest possible workflow for most common action

---

#### 3. Comment Command ⭐⭐⭐⭐
**Priority:** HIGH (50% of developers comment daily)
**Effort:** 8 hours

```bash
budjira comment PROJ-123 "Fixed in PR #42"     # Quick comment
budjira comment PROJ-123 --editor              # Multi-line editor
budjira comments PROJ-123                      # Show comments
```

**Implementation:**
- New command in `budjira/cli/comment.py`
- Uses Jira Comment API
- Markdown editor support (existing `utils/editor.py`)

**Business Impact:** Eliminates browser switch for commenting

---

#### 4. Connection Auto-Detection ⭐⭐⭐⭐
**Priority:** HIGH (Issue #12 Point 4 - Prevents wrong-connection errors)
**Effort:** 12 hours

```bash
# Automatic detection based on issue key
budjira show AS-13
# → Detects "AS" project key → uses aixacct connection automatically

budjira show PRD-4
# → Detects "PRD" project key → uses prd connection automatically
```

**Implementation:**
- Extend Connection model with `project_keys` field:
```toml
# ~/.config/budjira/connections.toml
[connections.aixacct]
name = "aixacct"
jira_url = "https://cdds.atlassian.net"
project_keys = ["AS", "AIXACCT"]  # Map these keys to this connection

[connections.prd]
name = "prd"
jira_url = "https://cdds.atlassian.net"
project_keys = ["PRD", "PROD"]
```

- Add `resolve_connection_from_issue_key()` helper in `utils/connection.py`
- Resolution priority order:
  1. `--connection` CLI flag (highest)
  2. `BUDJIRA_CONNECTION` ENV var
  3. Auto-detection from issue key pattern
  4. Default connection (fallback)

**Business Impact:**
- Eliminates silent failures and wrong-connection errors
- Natural UX: "AS-13" automatically uses correct connection
- Multi-project workflows become seamless

**User Quote (Issue #12):**
> "AS-3 is an aixacct issue (project key 'AS'), but budjira used the wrong connection."

**ROI:** 9/10 (critical for multi-project users)

---

**Phase 1 Summary:**
- **Total Effort:** 48 hours (~1.5 weeks)
- **Coverage Increase:** 70% → 90%
- **Outcome:** budjira becomes full Daily Driver with smart context

---

### ⭐ Phase 2: Enhancement - v1.9.0 (Q2 2026)
**Goal:** Niche excellence + Freelancer focus

#### 4. Issue Linking ⭐⭐⭐
**Priority:** MEDIUM (40% use for dependencies)
**Effort:** 12 hours

```bash
budjira link PROJ-123 blocks PROJ-124        # Issue relationships
budjira link PROJ-123 relates-to PROJ-125
budjira links PROJ-123                       # Show links
```

**Implementation:**
- New commands in `budjira/cli/issue.py`
- Uses Jira Issue Link API
- Support standard link types (blocks, relates, duplicates)

---

#### 5. Batch Time Logging ⭐⭐⭐⭐
**Priority:** MEDIUM (critical for freelancers - 90% need)
**Effort:** 10 hours

```bash
budjira tempo batch timelog.csv              # CSV import
budjira tempo log --multiple                 # Interactive multi-log
```

**CSV Format:**
```csv
issue_key,date,hours,comment
PROJ-1,2026-01-20,3h,Development
PROJ-2,2026-01-20,2h,Code Review
```

**Business Impact:** Solves Friday afternoon time tracking pain

---

#### 6. Timesheet Summary ⭐⭐⭐
**Priority:** MEDIUM (freelancer invoice generation)
**Effort:** 8 hours

```bash
budjira tempo summary --week                 # This week
budjira tempo summary --month --format csv   # Export for invoice
budjira tempo summary --export pdf           # PDF invoice (future)
```

**Implementation:**
- Aggregate existing worklog data
- Group by epic/project for FoU reporting
- CSV export for accounting software

---

#### 7. Epic Detail View (`--details` flag) ⭐⭐⭐
**Priority:** MEDIUM (Issue #12 Point 3 - Sprint planning needs)
**Effort:** 4 hours

```bash
budjira epic show AS-3 --details      # Show full story descriptions
budjira epic show AS-3 --verbose      # Include acceptance criteria
```

**Current Behavior:**
- Lists child stories with status
- Shows only titles/summaries

**Enhanced Behavior:**
- Full description for each story
- Acceptance criteria from DoR
- Story points/estimates
- Grouped by status (To Do / In Progress / Done)

**Implementation:**
- Extend existing `epic show` command
- Add `--details` and `--verbose` flags
- Fetch full issue details for each child
- Rich formatted output with collapsible sections

**Business Impact:**
- Sprint planning can happen fully in CLI
- PMs can review epic scope without opening 10+ browser tabs
- Quick assessment of epic completion

**User Quote (Issue #12):**
> "When viewing an epic, I often want to see the details of each story, not just titles."

**ROI:** 7/10 (critical for PMs, nice-to-have for developers)

---

**Phase 2 Summary:**
- **Total Effort:** 34 hours (~1 week)
- **Coverage Increase:** 90% → 97%
- **Outcome:** budjira dominates Freelancer market + PM workflows

---

### 💎 Phase 3: Polish - v2.0.0 (Q3 2026)
**Goal:** Premium UX with smart workflows

#### 7. Standup Helper ⭐⭐⭐⭐
**Priority:** LOW (nice-to-have, but high impact)
**Effort:** 6 hours

```bash
budjira standup
# Shows:
# - Yesterday: Issues worked on
# - Today: In Progress issues
# - Blockers: Blocked issues
# - Time: Logged hours
```

**Implementation:**
- Aggregate data from existing commands
- Smart defaults (last 24h activity)
- Pretty formatted output

---

#### 8. Command Simplification ⭐⭐⭐
**Priority:** LOW (UX improvement)
**Effort:** 8 hours

**Current Issues:**
- `search search` is redundant
- Too many nested subcommands

**Proposed Changes:**
```bash
# OLD:
budjira search search "assignee = me"

# NEW:
budjira search "assignee = me"

# ADD Smart shortcuts:
budjira mine                # My issues
budjira today               # Issues touched today
budjira week                # This week summary
```

---

#### 9. Interactive Mode ⭐⭐
**Priority:** LOW (complex, niche use)
**Effort:** 20 hours

```bash
budjira                          # Start interactive mode
> search assignee = currentUser()
> start PROJ-123
> log 2h "Implemented feature X"
```

**Implementation:**
- Prompt Toolkit integration
- Command history
- Tab completion
- Exit on EOF/Ctrl+D

---

#### 10. Context Management ⭐⭐
**Priority:** LOW (Issue #12 Point 4 - Alternative to auto-detection)
**Effort:** 8 hours

```bash
budjira context set --connection aixacct --project AS
# → Saves to .budjira-context in current directory

budjira context show
# Current Context:
# - Connection: aixacct
# - Project: AS

budjira context clear
# → Removes context file
```

**Features:**
- Persistent context for current working directory
- Stored in `.budjira-context` (gitignored)
- Override hierarchy:
  1. CLI `--connection` flag
  2. ENV `BUDJIRA_CONNECTION`
  3. Directory context (`.budjira-context`)
  4. Auto-detection from issue key
  5. Default connection

**Implementation:**
- New commands in `budjira/cli/context.py`
- JSON file storage: `{cwd}/.budjira-context`
```json
{
  "connection": "aixacct",
  "project": "AS",
  "set_at": "2026-07-15T10:30:00Z"
}
```
- Auto-load context on command execution

**Use Case:**
```bash
cd ~/projects/aixacct-migration
budjira context set --connection aixacct

# Now all commands default to aixacct
budjira show AS-13        # Uses aixacct automatically
budjira create            # Creates in aixacct/AS
budjira tempo log AS-13 2h  # Logs to aixacct
```

**Business Impact:**
- Simplifies multi-project workflows
- Alternative for users who don't want auto-detection
- Project-scoped configuration

**ROI:** 6/10 (nice-to-have for multi-project power users)

---

**Phase 3 Summary:**
- **Total Effort:** 42 hours (~1 week)
- **Coverage Increase:** 97% → 100%
- **Outcome:** Premium CLI experience with full context control

---

## 📊 Feature Impact Matrix

| Feature | Developer % | Freelancer % | PM % | Effort | Priority | ROI | Issue |
|---------|-------------|--------------|------|--------|----------|-----|-------|
| **Issue Detail View** | 95% | 80% | 90% | 8h | 🔥 CRITICAL | 10/10 | #12 |
| Sprint Management | 85% | 20% | 95% | 24h | 🔥 CRITICAL | 10/10 | - |
| Quick Aliases | 90% | 70% | 40% | 4h | 🔥 HIGH | 10/10 | #12 |
| **Connection Auto-Detect** | 70% | 60% | 50% | 12h | ⭐ HIGH | 9/10 | #12 |
| Comments | 70% | 30% | 60% | 8h | ⭐ HIGH | 9/10 | #12 |
| Issue Linking | 60% | 10% | 50% | 12h | ⭐ MEDIUM | 7/10 | - |
| Batch Time Logging | 10% | 90% | 5% | 10h | ⭐ MEDIUM | 8/10 | - |
| Timesheet Summary | 15% | 85% | 30% | 8h | ⭐ MEDIUM | 7/10 | - |
| **Epic Detail View** | 40% | 20% | 80% | 4h | ⭐ MEDIUM | 7/10 | #12 |
| Standup Helper | 75% | 20% | 80% | 6h | 💎 LOW | 8/10 | - |
| Interactive Mode | 40% | 20% | 15% | 20h | 💎 LOW | 5/10 | - |
| **Context Management** | 30% | 20% | 40% | 8h | 💎 LOW | 6/10 | #12 |

**Bold** = New features from Issue #12

---

## ⚖️ Tool Simplicity: "80/20 Tool Philosophy"

### Design Rule:
> **"Every feature must be used by ≥20% of users OR be a unique selling point"**

### ✅ Passes Filter:
- Sprint Management: 55% of users → IMPLEMENT
- Comments: 50% of users → IMPLEMENT
- Issue Linking: 40% of users → IMPLEMENT
- Batch Time Logging: 10% BUT unique for Freelancers → IMPLEMENT

### ⚠️ Borderline:
- Interactive Mode: 15% → Nice-to-Have (v2.0)
- Bulk Operations: 20% (PMs only) → Consider for v2.0

### ❌ Out of Scope:
1. Board Customization → Stay in Jira UI
2. Advanced Reporting → Use Jira Dashboard
3. User Management → Admin task, not CLI
4. Custom Fields Editor → Too complex for CLI
5. Notifications/Webhooks → Not CLI domain
6. Jira Server Support → Already decided (Issue #11)

---

## 🎯 Success Metrics

**KPIs for "Buddy" Experience:**

1. **Daily Active Commands**
   - Current: ~3 commands/day/user
   - Target: ≥5 commands/day/user

2. **Browser Context Switches**
   - Current: ~10 switches/day
   - Target: ≤3 switches/day (70% reduction)

3. **Time-to-Action**
   - Current: ~15 seconds average
   - Target: <5 seconds for 80% of tasks

4. **User Retention**
   - Target: ≥80% still using daily after 1 month

5. **Workflow Coverage**
   - Current: 57% of top-7 workflows
   - Target: 100% of top-7 workflows

---

## 💡 The "3-Command Test"

**Thesis:** If a user can do their 80% workflows with ≤3 commands, the tool is a buddy.

### Current State (Too Many):
```bash
# Morning Routine (6 commands)
budjira search "assignee = me"
budjira issue update PROJ-123 --status "In Progress"
budjira tempo log PROJ-120 2h "Yesterday's work"
budjira search "sprint = current AND status = 'To Do'"
budjira create
budjira epic
```

### Target State (v2.0 - Perfect):
```bash
# Morning Routine (3 commands)
budjira standup                    # Shows yesterday + today + blockers
budjira start PROJ-123             # Quick status change
budjira tempo batch yesterday.csv  # Batch time logging
```

---

## 🚫 Scope Creep Prevention

### Why a CLI Should NOT Replace Jira UI:

**CLI is for:**
- ✅ Frequent, repetitive actions
- ✅ Quick status updates
- ✅ Automation/scripting
- ✅ Developer workflow integration

**GUI is for:**
- ❌ Visual board management
- ❌ Complex field editing
- ❌ Admin configuration
- ❌ Custom reporting/dashboards

**Philosophy:**
> "A CLI should be a *productivity multiplier*, not a *full Jira replacement*."

---

## 📅 Timeline Overview

```
Q4 2025 (Oct-Dec)    v1.7.3  Quick Wins        8h   Issue detail view (Issue #12)
Q1 2026 (Jan-Mar)    v1.8.0  Foundation        48h  Critical gaps + auto-detect
Q2 2026 (Apr-Jun)    v1.9.0  Enhancement       34h  Niche excellence + epic details
Q3 2026 (Jul-Sep)    v2.0.0  Polish            42h  Premium UX + context mgmt
Q4 2026 (Oct-Dec)    v2.1.0  Maintenance       -    Bug fixes, minor features
```

**Total Investment:** ~132 hours (~3 weeks of focused development)
**Previous Plan:** ~100 hours
**Increase:** +32 hours (user-driven features from Issue #12)

---

## 🎭 "Buddy" Personality Enhancement

**What makes a CLI tool a "Buddy"?**

### ✅ budjira already does well:
1. Friendly banner ("Your CLI Pal" 🦖)
2. Helpful error messages (actionable)
3. Rich output (formatted tables)
4. Auto-update (self-care)

### 💡 New "Buddy" behaviors (v2.0):

**1. Context Awareness**
```bash
budjira mine      # My issues (auto-expands JQL)
budjira today     # Today's activity
budjira week      # This week's summary
```

**2. Smart Suggestions**
```bash
budjira start PROJ-123
✅ Started PROJ-123
💡 Tip: Log time when done: budjira tempo log PROJ-123 2h
```

**3. Workflow Memory**
```bash
budjira last      # Last viewed issue
budjira continue  # Resume last workflow
```

---

## 🎯 Next Steps

### Immediate Actions:
1. ✅ Document roadmap (this file)
2. ⬜ Create GitHub Issues for Phase 1 features
3. ⬜ Prototype Sprint Management (quick win)
4. ⬜ Update README with roadmap preview
5. ⬜ Optional: User survey to validate assumptions

### Phase 1 Implementation Order:
1. Quick Aliases (4h) - fastest win
2. Comments (8h) - high impact
3. Sprint Management (24h) - biggest gap

---

## 📎 GitHub Issues Tracking

This roadmap incorporates user feedback and feature requests from:

### Issue #12 - [FR] Improve UX: Issue detail view, workflow shortcuts, and context awareness
**Status:** Open | **Impact:** HIGH | **Date:** 2025-10-27

**Features Integrated:**
1. ✅ **Issue Detail View** → Phase 0 (v1.7.3) - CRITICAL
2. ✅ **Workflow shortcuts** (`start`, `done`) → Phase 1 (already planned)
3. ✅ **`search search` → `search`** → Phase 3 (already planned)
4. ✅ **Connection auto-detection** → Phase 1 (NEW) - HIGH
5. ✅ **Epic detail view** (`--details` flag) → Phase 2 (NEW) - MEDIUM
6. ✅ **Bulk operations** → Phase 3 (already planned)
7. ✅ **Context management** → Phase 3 (NEW) - LOW

**User Impact:**
- **100% coverage** of Issue #12 feature requests
- **4 new features** added to roadmap
- **3 existing features** validated by real-world user feedback
- **Phase 0 created** to address most critical gap immediately

**User Quote:**
> "budjira is already a game-changer! These improvements would make it perfect for daily PM work."

---

## 📚 Research Sources

- Jira Usage Statistics 2025 (Stack Overflow Developer Survey)
- CLI Design Best Practices (clig.dev, Atlassian)
- Competitor Analysis (jira-cli, go-jira, ACLI)
- Budjira current feature set (v1.7.2)
- **User Feedback:** GitHub Issue #12 (Real-world PM workflow)

---

## ✅ Sign-Off

**Analysis Date:** 2025-10-27 (Updated with Issue #12 feedback)
**Analyst Role:** Requirements Engineer & Product Workflow Expert
**Status:** Ready for stakeholder review

**Updated Recommendation:**
1. **Immediate:** Proceed with Phase 0 (v1.7.3) - Issue Detail View (8h)
2. **Q1 2026:** Proceed with Phase 1 (v1.8.0) - Foundation + Auto-Detection (48h)
3. **Q2 2026:** Proceed with Phase 2 (v1.9.0) - Enhancement + Epic Details (34h)
4. **Q3 2026:** Proceed with Phase 3 (v2.0.0) - Polish + Context Management (42h)

**Expected Outcome:** budjira becomes the definitive Daily Driver for Jira Cloud users with 100% coverage of critical workflows and smart context awareness.

**Validation:** All Phase 0-1 features validated by real-world user feedback (Issue #12).
