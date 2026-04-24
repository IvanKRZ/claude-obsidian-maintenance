# Wöchentlicher Workflow

## Der komplette Ablauf in Kurzform

```powershell
cd C:\Users\<User>\Documents\Obsidian\FIS
.\_maintenance\scripts\Run-Weekly.ps1          # 1. Pipeline lokal
python _maintenance\scripts\inspect_findings.py all   # 2. Quick-Check
claude                                         # 3. → /weekly-maintenance
git add . ; git commit -m "Weekly maintenance $(Get-Date -Format 'yyyy-MM-dd')"
```

Dauer: **5–10 Minuten inkl. Claude-Interaktion**.

## Schritt für Schritt

### 1. Git-Safety

Stelle sicher, dass der Vault in einem sauberen Git-Zustand ist:

```powershell
git status
```

Falls uncommitted changes existieren: vorher committen. `Run-Weekly.ps1` warnt dich sonst und fragt nach.

### 2. Pipeline ausführen

```powershell
.\_maintenance\scripts\Run-Weekly.ps1
```

Das Script:
1. Sichert den vorigen Index als `last_run.json`
2. Generiert einen neuen Index aller Notizen
3. Berechnet das Delta (geänderte/neue/gelöschte Notizen)
4. Analysiert Probleme

**Erwartete Ausgabe:**

```
=== Vault Maintenance: 2026-04-24 15:30 ===
Vault: C:\...\FIS
Previous index backed up to last_run.json

[1/3] vault_index.py
Scanning vault: C:\...\FIS
Indexed 139 notes (16 MOCs) -> ...\index.json

[2/3] vault_delta.py
Delta: +2 ~3 -0

[3/3] vault_analyze.py
Findings -> ...\findings.json
Broken links: 18 | Orphans: 0 | Tag variants: 2 | FM issues: 9 | Stubs: 2 | MOC drift: 7

=== Ready for Claude Code ===
```

### 3. Findings inspizieren (optional, aber empfohlen)

```powershell
python _maintenance\scripts\inspect_findings.py all
```

Oder gezielt einzelne Sektionen:

```powershell
python _maintenance\scripts\inspect_findings.py links
python _maintenance\scripts\inspect_findings.py mocs
python _maintenance\scripts\inspect_findings.py fm
python _maintenance\scripts\inspect_findings.py tags
python _maintenance\scripts\inspect_findings.py orphans
python _maintenance\scripts\inspect_findings.py stubs
```

Damit weißt du im Voraus, was Claude bearbeiten wird, und kannst in der Prompt gezielt priorisieren.

### 4. Claude Code starten

```powershell
claude
```

Im Claude-Prompt:

```
/weekly-maintenance
```

Claude liest `findings.json`, `delta.json` und die Config und arbeitet die Probleme in definierter Reihenfolge ab.

### 5. Review der Änderungen

Nach Abschluss des Claude-Laufs:

```powershell
git diff --stat            # Überblick: welche Dateien geändert
git diff                   # Details der Änderungen
```

Alternativ in VS Code oder Obsidian visuell prüfen.

### 6. Commit

```powershell
git add .
git commit -m "Weekly maintenance $(Get-Date -Format 'yyyy-MM-dd')"
```

## Varianten der Claude-Prompt

### Trockenlauf (erste Male empfohlen)

```
/weekly-maintenance

Wichtig: Trockenlauf.
- Keine Edits an Notizen durchführen
- Nur Report nach _maintenance/reports/YYYY-MM-DD-dryrun.md schreiben
- Für jeden Vorschlag begründen, warum
```

### Fokus auf Broken Links

```
/weekly-maintenance

Bearbeite nur broken_links und frontmatter_issues.
MOC-Drift und Tag-Varianten diesmal überspringen, nur im Report erwähnen.
```

### Fokus auf MOC-Pflege

```
/weekly-maintenance

Bearbeite nur moc_drift. Öffne alle betroffenen MOCs und strukturiere 
sie neu, sodass die unlinked_candidates in thematisch passende Abschnitte 
eingefügt werden. Keine broken_links, keine frontmatter-Fixes.
```

### Ausschluss bestimmter Patterns

```
/weekly-maintenance

Ignoriere broken_links, deren Ziel "TODO", "WIP" oder "Draft" im Namen enthält.
Das sind bewusste Platzhalter.
```

## Reports

Alle Claude-Läufe erzeugen einen Markdown-Report in `_maintenance\reports\`. Diese sind versionskontrolliert und dienen als Historie:

```
_maintenance\reports\
├── 2026-04-24-dryrun.md
├── 2026-04-24.md
├── 2026-05-01.md
└── 2026-05-08.md
```

Du kannst diese auch direkt in Obsidian öffnen und als Reference behalten.

## Rollback

Falls ein Claude-Lauf schiefgeht:

### Letzten Commit rückgängig machen

```powershell
git reset --hard HEAD~1
```

### Zu einem spezifischen Tag

```powershell
git reset --hard maintenance-v1-baseline
```

### Einzelne Datei zurücksetzen

```powershell
git checkout HEAD~1 -- "pfad/zur/datei.md"
```

## Rhythmus und Disziplin

**Empfohlene Kadenz:** Einmal pro Woche, z.B. Sonntagabend oder Montagmorgen.

**Warum wöchentlich?**
- Das Delta bleibt handhabbar (wenige geänderte Notizen)
- Probleme akkumulieren nicht (Tag-Inkonsistenzen sind lokal begrenzt)
- Findings-Größe bleibt unter der Token-Schwelle

**Warum nicht täglich?**
- Overhead übersteigt Nutzen
- Manche Findings (MOC-Drift) werden erst nach einigen Tagen aussagekräftig

**Warum nicht monatlich?**
- Delta wird zu groß, Claude überschreitet Budget
- Broken Links bleiben wochenlang unentdeckt

## Optional: Scheduled Task für nächtlichen Index

Falls du möchtest, dass die Pipeline (ohne Claude) automatisch läuft — z.B. jeden Montag um 08:00:

```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\<User>\Documents\Obsidian\FIS\_maintenance\scripts\Run-Weekly.ps1" -SkipGitCheck'

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '08:00'

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "VaultMaintenance" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Weekly Obsidian vault index regeneration"
```

Claude Code dann manuell starten, wenn du Zeit hast — die Findings liegen bereits fertig vor.

## Token-Budget

| Vault-Größe | findings.json | Typischer Claude-Run |
|---|---|---|
| 200 Notizen | ~20 KB | 8–15k Tokens |
| 500 Notizen | ~50 KB | 15–25k Tokens |
| 1.000 Notizen | ~100 KB | 25–40k Tokens |
| 3.000 Notizen | ~300 KB | 50–80k Tokens |

**Bei Überschreitung:** `max_files_to_open_per_run` in `maintenance.yaml` senken, oder den Slash-Command in spezialisierte Versionen splitten (z.B. `/weekly-links`, `/weekly-mocs`).
