# budjira Header

## Design

Der budjira Header ist kompakt und auf 2 Zeilen begrenzt:

```
╭─ 🦖 budjira v0.1.0 ─ Your CLI Pal for Jira ─╮
╰──────────────────────────────────────────────────────────╯
```

Mit Farben im Terminal:
- Cyan: Rahmen (`╭─`, `─╮`, `╰`, `╯`)
- Bright Blue: Dino-Emoji (🦖)
- Bright Magenta Bold: "budjira"
- Dim: Versionsnummer
- Dim Italic: Tagline "Your CLI Pal for Jira"

## Verwendung

### Normaler Modus (Standard)
```bash
budjira <command>
# Zeigt Header, dann Kommando-Ausgabe
```

### Quiet-Modus (kein Header)
```bash
budjira -q <command>
budjira --quiet <command>
# Unterdrückt den Header, nur Kommando-Ausgabe
```

## Hinweise

- Der Header wird NICHT bei `--version` oder `--help` angezeigt (diese sind "eager" Callbacks)
- Der Header erscheint bei allen normalen Commands (search, create, log-time, etc.)
- Nutze `-q` für Scripting oder wenn der Header stört
- Der Header ist für Terminals mit Farbunterstützung optimiert

## Beispiele

**Interaktive Nutzung (mit Header):**
```bash
$ budjira search "project = MYPROJ"
╭─ 🦖 budjira v0.1.0 ─ Your CLI Pal for Jira ─╮
╰──────────────────────────────────────────────────────────╯

[Suchergebnisse...]
```

**Scripting/Automation (ohne Header):**
```bash
$ budjira -q search "project = MYPROJ" | jq '.issues[].key'
MYPROJ-123
MYPROJ-124
MYPROJ-125
```

**Pipelines:**
```bash
# Mit Header für lokale Entwicklung
budjira search "..." > issues.json

# Ohne Header für CI/CD
budjira -q search "..." > issues.json
```
