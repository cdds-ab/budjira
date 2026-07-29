# Transition screen fields and validator attribution (#101, slice 2+3)

Status: approved 2026-07-29
Issue: [#101](https://github.com/cdds-ab/budjira/issues/101)

## Problem

A Jira transition may present a screen whose fields must be filled. budjira
cannot fill them, so such a transition is **un-completable from the CLI** — not
degraded, but impossible. The only fallbacks are the Jira UI or a hand-rolled
REST call built from credentials pulled out of budjira's own config, which a
hardened policy layer can deny outright.

A second failure mode compounds it: a field enforced by a *workflow validator*
rather than by field-level required-ness fails with

```json
{"errorMessages":["<validator message>"],"errors":{}}
```

The `errors` object is empty, so nothing names the offending field, and such a
field can even appear as `required: false` in the transition metadata.

## Scope

This spec covers **parts 2 and 3** of #101, plus `--dry-run`.

Explicitly out of scope:

- **Part 1, multi-hop path finding.** `GET /issue/{key}/transitions` is
  state-specific: it returns only the transitions valid from the issue's
  *current* status. Looking ahead to a second hop requires the workflow
  definition (`/rest/api/3/workflow`, project workflow scheme), which is
  normally admin-gated. Whether a standard token can read it is unverified.
  Path finding stays blocked on that spike.
- **Part 4, rich-text/ADF.** budjira constructs `JIRA(...)` without
  `rest_api_version` (`budjira/core/jira_client.py:72`), so jira-python's
  default of `"2"` applies and rich-text transition fields accept plain
  strings today. The ADF problem becomes real only when Epic #96 switches to
  v3; it belongs there, and #96 must cover transition fields when it lands.

## Verified premises

| Premise | Evidence |
|---------|----------|
| jira-python can request screen fields | `JIRA.transitions(issue, id=None, expand=None)` |
| jira-python can send transition fields | `JIRA.transition_issue(issue, transition, fields=None, comment=None, ...)` |
| budjira speaks REST v2 today | no `rest_api_version` passed at `jira_client.py:72` |
| none of this exists yet | `TransitionService.get_transitions` returns only `id`+`name`; `transition()` passes no fields |

## Design

### Models — `budjira/models/transition.py` (new)

```python
class TransitionField(BaseModel):
    field_id: str            # e.g. "customfield_10001"
    name: str                # display name from the screen
    required: bool
    field_type: str | None   # from schema.type
    allowed_values: list[str] | None

class Transition(BaseModel):
    id: str
    name: str
    to_status: str | None
    fields: list[TransitionField]
```

Screen metadata gets a typed shape instead of raw dicts. `allowed_values` is
carried so a wrong value can be rejected locally, before it reaches Jira.

### Service — `budjira/services/transitions.py`

- `get_transitions()` keeps its current signature and `id`/`name` return shape.
  The `issue transitions` command and the deprecated `JiraClient` wrapper
  depend on it; this slice does not break them.
- `get_transition_details(issue_key) -> list[Transition]` is new: calls
  `client.transitions(issue_key, expand="transitions.fields")` and maps the
  response into the models above.
- `transition(issue_key, transition_name, fields=None)` gains an optional
  `fields` dict, forwarded to `client.transition_issue(..., fields=fields)`.
  Omitting it preserves today's behaviour exactly.

### Field resolution

`--field key=value` is repeatable. `key` matches either the field ID exactly
(`customfield_10001`) or the display name case-insensitively (`"Solution
details"`), both taken from the live screen metadata — **no `connections.toml`
configuration required**, unlike `create --custom`. Requiring pre-configuration
would defeat the purpose: the field is usually discovered in the moment.

Every resolved field is sent, not only the required ones: an optional screen
field the user chose to fill must reach Jira.

`--field` without `--status` is a usage error. These fields belong to a
transition screen, and without a transition there is no screen to resolve them
against; silently applying them as a plain field edit would be a different
operation than the user asked for.

Failure modes:

- Unknown key → error listing the field IDs and names the screen actually has.
- Key matching several fields by name → error naming the candidates and asking
  for the field ID. Never guess.
- Value not in `allowed_values` → error listing the permitted values.

### Missing required fields

Determined from the screen metadata (`required: true`, no value supplied).

- **Interactive** (`--interactive`, the default, *and* `stdin` is a TTY):
  prompt for each missing required field. `allowed_values` are shown.
- **Non-interactive** (`--no-interactive`, or `stdin` is not a TTY): no prompt.
  Abort with the full list of what is needed — field ID, display name, type,
  and allowed values where present — in a form that can be pasted back as
  `--field` arguments.

The TTY check matters beyond the flag: budjira is driven by agents and CI where
`--no-interactive` is easy to forget, and a prompt there hangs. The flag name
and default follow `create` (`--interactive/--no-interactive`, `-i/-n`,
default `True`).

### Validator attribution

On `JIRAError` from the transition, inspect the response body. When `errors` is
empty and `errorMessages` is non-empty, match each message against the display
names of the transition's screen fields (case-insensitive substring, both
directions) and report the matched field by ID and name instead of forwarding
Jira's bare sentence.

- Interactive: prompt for the attributed field and retry the transition **once**.
  One retry only — a second failure means the guess was wrong, and looping
  writes noise into the issue history.
- Non-interactive: abort, naming the field.
- No match: forward Jira's message unchanged, plus the list of screen fields as
  context. Never invent a field name.

### CLI — `budjira issue update`

New options: `--field key=value` (repeatable), `--dry-run`, and
`--interactive/--no-interactive` consistent with `create`.

Flow: fetch transition details → resolve `--field` entries → determine missing
required fields → prompt or abort → execute → attribute-and-maybe-retry on
validator error.

`--dry-run` prints the transition to be performed, the resolved fields with
their IDs and values, and any missing required fields — then exits **without
touching the issue**. This is what makes the feature safe to explore on real
tickets, which is the whole point of the issue.

`--dry-run` combined with `--interactive` does not prompt: a dry run must not
ask for values it will never send.

## Error handling

Reuses the existing hierarchy in `budjira/utils/errors.py`
(`BudjiraError`, `JiraAPIError`, `InvalidIssueError`). Every new error message
names the issue, the transition, and what to do next — no bare Jira strings
except in the explicit no-match fallback.

## Testing

TDD, mocked at the jira-python boundary with `autospec=True`, no live API.

Service tests:
1. `get_transition_details` passes `expand="transitions.fields"`
2. screen metadata maps into `Transition` / `TransitionField`, `required` included
3. `transition(fields=...)` forwards the dict to `transition_issue`
4. `transition()` without fields keeps today's call shape

Resolution tests:
5. field resolved by exact ID
6. field resolved by display name, case-insensitive
7. unknown key errors and lists the available fields
8. ambiguous name errors and names the candidates
9. value outside `allowed_values` is rejected before any API call
10. optional (non-required) supplied fields are forwarded too
11. `--field` without `--status` is a usage error

CLI tests:
12. missing required field, non-interactive → exit 1, message lists ID/name/type
13. missing required field, interactive → prompt, then transition with the value
14. `--dry-run` performs no transition (assert `transition_issue` not called)
15. `--dry-run` does not prompt even when interactive
16. validator error with empty `errors` → message names the matched field
17. validator error, interactive → prompt and exactly one retry
18. validator error with no matching field → Jira's message forwarded intact

Coverage target: ≥90% for the new service and resolution code, per the repo's
core-logic guideline.

## Out of scope, recorded

- Multi-hop path finding (#101 part 1) — needs the workflow-API spike first.
- ADF/rich text (#101 part 4) — belongs to Epic #96.

Both should stay open on #101 after this slice merges; this spec closes neither.
