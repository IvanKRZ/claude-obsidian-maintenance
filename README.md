# Obsidian Vault Maintenance Workflow

Token-effiziente wöchentliche Pflege eines Obsidian-Vaults mit Claude Code.

## Kernidee

Das Problem: Den kompletten Vault jede Woche an Claude zu geben ist teuer und funktioniert ab ein paar hundert Notizen nicht mehr. Die Lösung trennt die Arbeit in zwei Schichten:

1. **Python (lokal, kostenlos)**: Scannt den Vault, extrahiert Metadaten, erkennt Probleme und komprimiert alles in eine kleine `findings.json`
2. **Claude Code (Tokens, gezielt)**: Liest nur die `findings.json` und öffnet selektiv 5–25 problematische Dateien zur Bearbeitung

Resultat: ~15–30k Tokens pro Wochenlauf statt Hunderttausender.

## Inhalt des Archivs

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
│   │   ├── inspect_findings.py         # Findings-Inspektor
│   │   ├── fix_tags_case.py            # Einmaliger Tags/tags Fix
│   │   └── Run-Weekly.ps1              # PowerShell-Orchestrator
│   ├── config/
│   │   └── maintenance.yaml            # Konfiguration
│   ├── state/                          # Generiert (gitignored)
│   │   └── .gitkeep
│   └── reports/                        # Claude-Reports
│       └── .gitkeep
└── .claude/
    └── commands/
        └── weekly-maintenance.md       # Slash-Command für Claude Code
```

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

1. Archiv in den Obsidian-Vault-Root entpacken (Dateien/Ordner direkt dorthin kopieren)
2. `INSTALL.md` folgen (Dependencies, UTF-8-Config, Execution Policy)
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
[1] vault_index.py         -> index.json (alle Metadaten)
[2] vault_delta.py         -> delta.json (Änderungen seit letztem Lauf)
[3] vault_analyze.py       -> findings.json (Probleme)
[4] Claude Code            -> Fixes + Report
[5] git commit
```

Claude liest nur Schritt-3-Output und öffnet gezielt Problemdateien. Der Vault selbst landet nie komplett im Context.

## Erkannte Probleme

Die Pipeline identifiziert:

- **Broken Links**: `[[Wikilinks]]` ohne passende Ziel-Notiz
- **Orphans**: Notizen ohne Backlinks und ohne MOC-Zugehörigkeit
- **Tag-Varianten**: Gleiche Bedeutung, unterschiedliche Schreibweise (`#netzwerk` vs `#networking`)
- **Tag-Singletons**: Tags in nur einer Notiz (Tippfehler-Kandidaten)
- **Frontmatter-Issues**: Fehlende Pflichtfelder oder YAML-Parse-Errors
- **Stubs**: Sehr kurze Notizen
- **MOC-Drift**: Notizen, die thematisch zu einem MOC gehören, aber nicht verlinkt sind

## Dokumentation

| Datei | Inhalt |
|---|---|
| `INSTALL.md` | Einmalige Einrichtung |
| `WORKFLOW.md` | Wöchentlicher Ablauf, Claude-Interaktion |
| `TROUBLESHOOTING.md` | Häufige Fehler und Lösungen |

## Lizenz

Privates Projekt — keine öffentliche Lizenz. Nutzung auf eigene Verantwortung.
