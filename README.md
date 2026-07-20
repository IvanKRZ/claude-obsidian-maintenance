# Obsidian Vault Maintenance Workflow

Token-efficient weekly maintenance of an Obsidian vault with Claude Code.

*[Deutsche Version unten](#obsidian-vault-maintenance-workflow-deutsch)*

## Core Idea

The problem: handing your entire vault to Claude every week is expensive and stops working past a few hundred notes. This workflow splits the job into two layers:

1. **Python (local, free)**: scans the vault, extracts metadata, detects problems and compresses everything into a small `findings.json`
2. **Claude Code (tokens, targeted)**: reads only `findings.json` and selectively opens 5–25 problematic files to fix

Result: ~15–30k tokens per weekly run instead of hundreds of thousands.

## Contents

```
vault-maintenance/
├── README.md                           # This file
├── INSTALL.md                          # Setup guide
├── WORKFLOW.md                         # Weekly routine
├── TROUBLESHOOTING.md                  # Common problems
├── _maintenance/
│   ├── scripts/
│   │   ├── vault_index.py              # Metadata extraction
│   │   ├── vault_delta.py              # Change detection
│   │   ├── vault_analyze.py            # Problem detection
│   │   ├── vault_trend.py              # Metric history across runs
│   │   ├── scan_sources.py             # Sources-section check (optional)
│   │   ├── atomic_io.py                # Atomic JSON writes (shared)
│   │   ├── inspect_findings.py         # Findings inspector
│   │   ├── fix_tags_case.py            # One-off Tags/tags fix
│   │   └── Run-Weekly.ps1              # PowerShell orchestrator
│   ├── config/
│   │   └── maintenance.yaml            # Configuration (single point of adjustment)
│   ├── state/                          # Generated (gitignored)
│   ├── tasks/                          # On-demand work plans
│   └── reports/                        # Claude reports
└── .claude/
    └── commands/
        └── weekly-maintenance.md       # Slash command for Claude Code
```

All scripts are **vault-agnostic** — they derive the vault root from their own
location and read every setting from `maintenance.yaml`. For a new vault, copy
`_maintenance/` and `.claude/` into it and adjust only the config plus the
"Vault-Konventionen" section in the slash command.

## Requirements

| Component | Version | Check with |
|---|---|---|
| Windows | 10/11 | — |
| Python | 3.10+ | `python --version` |
| PyYAML | any | `python -m pip show pyyaml` |
| PowerShell | 5.1+ | `$PSVersionTable.PSVersion` |
| Git for Windows | 2.40+ | `git --version` |
| Claude Code CLI | current | `claude --version` |

## Quick Start

1. Copy `_maintenance/` and `.claude/` into your Obsidian vault root
2. Follow `INSTALL.md` (dependencies, UTF-8 config, execution policy, config adjustments)
3. Run the pipeline for the first time:
   ```powershell
   .\_maintenance\scripts\Run-Weekly.ps1
   ```
4. Inspect the findings:
   ```powershell
   python _maintenance\scripts\inspect_findings.py all
   ```
5. Start Claude Code and use `/weekly-maintenance`

## Architecture

```
[1] vault_index.py         -> index.json      (all metadata)
[2] vault_delta.py         -> delta.json      (changes since last run)
[3] vault_analyze.py       -> findings.json   (problems)
[4] vault_trend.py         -> history.json    (metrics across the last 12 runs)
[5] scan_sources.py        -> missing_sources.json (optional)
[6] Claude Code            -> fixes + report
[7] git commit
```

Claude reads only the small outputs from steps 3–5 and opens problem files selectively.
`index.json` is explicitly off-limits for Claude — the vault never enters the context in full.

`Run-Weekly.ps1` validates after every step that the expected JSON exists and parses,
and aborts hard otherwise. All writes are atomic (`atomic_io.py`), so a sync client or
obsidian-git never sees a half-written file.

## Detected Problems

The pipeline identifies:

- **Broken links**: `[[wikilinks]]` without a matching target note (code blocks and image embeds are ignored)
- **Orphans**: notes without backlinks and without MOC membership
- **Tag variants**: same meaning, different spelling (`#netzwerk` vs `#networking`)
- **Tag singletons**: tags used in only one note (typo candidates)
- **Frontmatter issues**: missing required fields, case inconsistencies, YAML parse errors
- **Stubs**: very short notes
- **MOC drift**: notes that thematically belong to a MOC but aren't linked from it
- **Missing sources** (optional): notes without or with an empty sources section
- **Trends**: development of all metrics across recent runs

## Auto-Apply Control

Tag normalizations can be marked as trusted per mapping:

```yaml
tag_canonical:
  python:
    aliases: ["py", "python3"]
    auto_apply: true      # Claude applies without asking
  security:
    aliases: ["sec", "infosec"]
    auto_apply: false     # Claude asks first
```

Everything else is collected into a consolidated dry-run plan for which Claude
requests **one** confirmation, instead of asking per file.

## Documentation

| File | Content |
|---|---|
| `INSTALL.md` | One-time setup |
| `WORKFLOW.md` | Weekly routine, Claude interaction |
| `TROUBLESHOOTING.md` | Common errors and fixes |

## License

Private project — no public license. Use at your own risk.

---

# Obsidian Vault Maintenance Workflow (Deutsch)

Token-effiziente wöchentliche Pflege eines Obsidian-Vaults mit Claude Code.

## Kernidee

Das Problem: Den kompletten Vault jede Woche an Claude zu geben ist teuer und funktioniert ab ein paar hundert Notizen nicht mehr. Die Lösung trennt die Arbeit in zwei Schichten:

1. **Python (lokal, kostenlos)**: Scannt den Vault, extrahiert Metadaten, erkennt Probleme und komprimiert alles in eine kleine `findings.json`
2. **Claude Code (Tokens, gezielt)**: Liest nur die `findings.json` und öffnet selektiv 5–25 problematische Dateien zur Bearbeitung

Resultat: ~15–30k Tokens pro Wochenlauf statt Hunderttausender.

## Inhalt

```
vault-maintenance/
├── README.md                           # Diese Datei
├── INSTALL.md                          # Setup-Anleitung
├── WORKFLOW.md                         # Wöchentlicher Ablauf
├── TROUBLESHOOTING.md                  # Häufige Probleme
├── _maintenance/
│   ├── scripts/
│   │   ├── vault_index.py              # Metadata-Extraktion
│   │   ├── vault_delta.py              # Änderungserkennung
│   │   ├── vault_analyze.py            # Problem-Detection
│   │   ├── vault_trend.py              # Kennzahl-Historie über Läufe hinweg
│   │   ├── scan_sources.py             # Quellen-Abschnitts-Check (optional)
│   │   ├── atomic_io.py                # Atomares JSON-Schreiben (shared)
│   │   ├── inspect_findings.py         # Findings-Inspektor
│   │   ├── fix_tags_case.py            # Einmaliger Tags/tags Fix
│   │   └── Run-Weekly.ps1              # PowerShell-Orchestrator
│   ├── config/
│   │   └── maintenance.yaml            # Konfiguration (einziger Anpassungspunkt)
│   ├── state/                          # Generiert (gitignored)
│   ├── tasks/                          # On-demand Arbeitspläne
│   └── reports/                        # Claude-Reports
└── .claude/
    └── commands/
        └── weekly-maintenance.md       # Slash-Command für Claude Code
```

Alle Skripte sind **vault-agnostisch** — sie leiten den Vault-Root aus ihrer
eigenen Position ab und lesen jede Einstellung aus `maintenance.yaml`. Für einen
neuen Vault kopierst du `_maintenance/` und `.claude/` hinein und passt nur die
Config sowie den Abschnitt "Vault-Konventionen" im Slash-Command an.

## Voraussetzungen

| Komponente | Version | Prüfen mit |
|---|---|---|
| Windows | 10/11 | — |
| Python | 3.10+ | `python --version` |
| PyYAML | beliebig | `python -m pip show pyyaml` |
| PowerShell | 5.1+ | `$PSVersionTable.PSVersion` |
| Git für Windows | 2.40+ | `git --version` |
| Claude Code CLI | aktuell | `claude --version` |

## Quick Start

1. `_maintenance/` und `.claude/` in den Obsidian-Vault-Root kopieren
2. `INSTALL.md` folgen (Dependencies, UTF-8-Config, Execution Policy, Config anpassen)
3. Erste Pipeline starten:
   ```powershell
   .\_maintenance\scripts\Run-Weekly.ps1
   ```
4. Findings inspizieren:
   ```powershell
   python _maintenance\scripts\inspect_findings.py all
   ```
5. Claude Code starten und `/weekly-maintenance` verwenden

## Architektur

```
[1] vault_index.py         -> index.json      (alle Metadaten)
[2] vault_delta.py         -> delta.json      (Änderungen seit letztem Lauf)
[3] vault_analyze.py       -> findings.json   (Probleme)
[4] vault_trend.py         -> history.json    (Kennzahlen über die letzten 12 Läufe)
[5] scan_sources.py        -> missing_sources.json (optional)
[6] Claude Code            -> Fixes + Report
[7] git commit
```

Claude liest nur die kleinen Ausgaben aus Schritt 3–5 und öffnet gezielt Problemdateien.
`index.json` ist für Claude explizit gesperrt — der Vault landet nie komplett im Context.

`Run-Weekly.ps1` validiert nach jedem Schritt, dass die erwartete JSON existiert und
parsebar ist, und bricht sonst hart ab. Alle Schreibvorgänge laufen atomar
(`atomic_io.py`), damit Nextcloud-Sync oder obsidian-git nie eine halb geschriebene
Datei sehen.

## Erkannte Probleme

Die Pipeline identifiziert:

- **Broken Links**: `[[Wikilinks]]` ohne passende Ziel-Notiz (Code-Blöcke und Bild-Embeds werden ignoriert)
- **Orphans**: Notizen ohne Backlinks und ohne MOC-Zugehörigkeit
- **Tag-Varianten**: Gleiche Bedeutung, unterschiedliche Schreibweise (`#netzwerk` vs `#networking`)
- **Tag-Singletons**: Tags in nur einer Notiz (Tippfehler-Kandidaten)
- **Frontmatter-Issues**: Fehlende Pflichtfelder, Case-Inkonsistenzen, YAML-Parse-Errors
- **Stubs**: Sehr kurze Notizen
- **MOC-Drift**: Notizen, die thematisch zu einem MOC gehören, aber nicht verlinkt sind
- **Fehlende Quellen** (optional): Notizen ohne oder mit leerem Quellen-Abschnitt
- **Trends**: Entwicklung aller Kennzahlen über die letzten Läufe

## Auto-Apply-Steuerung

Tag-Normalisierungen lassen sich pro Mapping als vertrauenswürdig markieren:

```yaml
tag_canonical:
  python:
    aliases: ["py", "python3"]
    auto_apply: true      # Claude wendet ohne Rückfrage an
  security:
    aliases: ["sec", "infosec"]
    auto_apply: false     # Claude fragt nach
```

Alles andere sammelt Claude in einem konsolidierten Dry-Run-Plan und holt dafür
**eine** Bestätigung, statt bei jeder Datei nachzufragen.

## Dokumentation

| Datei | Inhalt |
|---|---|
| `INSTALL.md` | Einmalige Einrichtung |
| `WORKFLOW.md` | Wöchentlicher Ablauf, Claude-Interaktion |
| `TROUBLESHOOTING.md` | Häufige Fehler und Lösungen |

## Lizenz

Privates Projekt — keine öffentliche Lizenz. Nutzung auf eigene Verantwortung.
