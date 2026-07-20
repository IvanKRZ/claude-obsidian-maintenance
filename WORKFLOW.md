# Weekly Workflow

*[Deutsche Version unten](#wöchentlicher-workflow-deutsch)*

## The full routine in short

```powershell
cd C:\Users\<User>\Obsidian\MyVault
.\_maintenance\scripts\Run-Weekly.ps1                 # 1. pipeline, local
python _maintenance\scripts\inspect_findings.py all   # 2. quick check
claude                                                # 3. -> /weekly-maintenance
git add . ; git commit -m "Weekly maintenance $(Get-Date -Format 'yyyy-MM-dd')"
```

Duration: **5–10 minutes including the Claude interaction**.

## Step by step

### 1. Git safety

Make sure the vault is in a clean Git state:

```powershell
git status
```

If uncommitted changes exist, commit them first. Otherwise `Run-Weekly.ps1` warns you and asks.

### 2. Run the pipeline

```powershell
.\_maintenance\scripts\Run-Weekly.ps1
```

The script:
1. Clears a stale `.git/index.lock` (from an obsidian-git crash) and checks the Git status
2. Backs up the previous index as `last_run.json`
3. Generates a fresh index of all notes
4. Computes the delta (changed/new/deleted notes)
5. Analyzes problems
6. Appends the metric snapshot to the history
7. Optionally checks the sources sections

After each step the generated JSON is checked for existence and parsability.

**Expected output:**

```
=== Vault Maintenance: 2026-04-24 15:30 ===
Vault: C:\...\MyVault
Previous index backed up to last_run.json

[1/5] vault_index.py
Indexed 139 notes (16 MOCs) -> ...\index.json
  OK: index.json ist valide JSON

[2/5] vault_delta.py
Delta: +2 ~3 -0
  OK: delta.json ist valide JSON

[3/5] vault_analyze.py
Broken links: 18 | Orphans: 0 | Tag variants: 2 | FM issues: 9 | Stubs: 2 | MOC drift: 7
  OK: findings.json ist valide JSON

[4/5] vault_trend.py
Trend (2026-04-17 -> 2026-04-24): total_notes: +2 | broken_links: -3 | orphans: +1 | ...
  OK: history.json ist valide JSON

[5/5] scan_sources.py
Missing-sources scan: 76 ohne '## Quellen', 14 leer (gesamt 90)
  OK: missing_sources.json ist valide JSON

=== Ready for Claude Code ===
```

### 3. Inspect the findings (optional but recommended)

```powershell
python _maintenance\scripts\inspect_findings.py all
```

Or specific sections:

```powershell
python _maintenance\scripts\inspect_findings.py links
python _maintenance\scripts\inspect_findings.py mocs
python _maintenance\scripts\inspect_findings.py fm
python _maintenance\scripts\inspect_findings.py tags
python _maintenance\scripts\inspect_findings.py orphans
python _maintenance\scripts\inspect_findings.py stubs
```

This tells you in advance what Claude will work on, so you can prioritize in your prompt.

### 4. Start Claude Code

```powershell
claude
```

In the Claude prompt:

```
/weekly-maintenance
```

Claude reads `findings.json`, `delta.json`, `history.json`, `missing_sources.json` and the config, then works through the problems in a defined order.

Before the first `Edit`, Claude presents a **consolidated dry-run plan**: changes with `auto_apply: true` run without asking, everything else gets **one** collected confirmation. Then it executes the whole block.

### 5. Review the changes

After the Claude run finishes:

```powershell
git diff --stat            # overview: which files changed
git diff                   # details of the changes
```

Alternatively review visually in VS Code or Obsidian.

### 6. Commit

```powershell
git add .
git commit -m "Weekly maintenance $(Get-Date -Format 'yyyy-MM-dd')"
```

## Prompt variants

### Dry run (recommended for the first few times)

```
/weekly-maintenance

Important: dry run.
- Do not edit any notes
- Only write a report to _maintenance/reports/YYYY-MM-DD-dryrun.md
- Justify every suggestion
```

### Focus on broken links

```
/weekly-maintenance

Only handle broken_links and frontmatter_issues.
Skip MOC drift and tag variants this time, just mention them in the report.
```

### Focus on MOC upkeep

```
/weekly-maintenance

Only handle moc_drift. Open all affected MOCs and restructure them so the
unlinked_candidates are inserted into thematically fitting sections.
No broken_links, no frontmatter fixes.
```

### Excluding certain patterns

```
/weekly-maintenance

Ignore broken_links whose target contains "TODO", "WIP" or "Draft".
Those are deliberate placeholders.
```

## Reports

Every Claude run produces a markdown report in `_maintenance\reports\`. These are version-controlled and serve as history:

```
_maintenance\reports\
├── 2026-04-24-dryrun.md
├── 2026-04-24.md
├── 2026-05-01.md
└── 2026-05-08.md
```

You can open them directly in Obsidian and keep them as reference.

Each report contains a **trend block** from `history.json` (rolling window over the last 12 runs) — so you can see at a glance whether the vault is improving or drifting.

## The `_maintenance/tasks/` folder

Drop zone for one-off, on-demand work plans (source backlogs, bulk refactorings). It is **not** filled by the weekly run. Completed plans get deleted, not archived — the folder should be empty when nothing is pending.

## Rollback

If a Claude run goes wrong:

### Undo the last commit

```powershell
git reset --hard HEAD~1
```

### Back to a specific tag

```powershell
git reset --hard maintenance-v1-baseline
```

### Reset a single file

```powershell
git checkout HEAD~1 -- "path/to/file.md"
```

## Rhythm and discipline

**Recommended cadence:** once a week, e.g. Sunday evening or Monday morning.

**Why weekly?**
- The delta stays manageable (few changed notes)
- Problems don't accumulate (tag inconsistencies stay locally contained)
- Findings size stays below the token threshold

**Why not daily?**
- Overhead exceeds the benefit
- Some findings (MOC drift) only become meaningful after a few days

**Why not monthly?**
- The delta grows too large, Claude exceeds its budget
- Broken links stay undetected for weeks

## Optional: scheduled task for a nightly index

If you want the pipeline (without Claude) to run automatically — e.g. every Monday at 08:00:

```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\<User>\Obsidian\MyVault\_maintenance\scripts\Run-Weekly.ps1" -SkipGitCheck'

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '08:00'

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "VaultMaintenance" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Weekly Obsidian vault index regeneration"
```

Then start Claude Code manually whenever you have time — the findings are already waiting.

## Token budget

| Vault size | findings.json | Typical Claude run |
|---|---|---|
| 200 notes | ~20 KB | 8–15k tokens |
| 500 notes | ~50 KB | 15–25k tokens |
| 1,000 notes | ~100 KB | 25–40k tokens |
| 3,000 notes | ~300 KB | 50–80k tokens |

**If exceeded:** lower `max_files_to_open_per_run` in `maintenance.yaml`, or split the slash command into specialized versions (e.g. `/weekly-links`, `/weekly-mocs`).

---

# Wöchentlicher Workflow (Deutsch)

## Der komplette Ablauf in Kurzform

```powershell
cd C:\Users\<User>\Obsidian\MeinVault
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
1. Räumt ein verwaistes `.git/index.lock` auf (obsidian-git-Absturz) und prüft den Git-Status
2. Sichert den vorigen Index als `last_run.json`
3. Generiert einen neuen Index aller Notizen
4. Berechnet das Delta (geänderte/neue/gelöschte Notizen)
5. Analysiert Probleme
6. Schreibt den Kennzahl-Snapshot in die Historie
7. Prüft optional die Quellen-Abschnitte

Nach jedem Schritt wird die erzeugte JSON auf Existenz und Parsebarkeit geprüft.

**Erwartete Ausgabe:**

```
=== Vault Maintenance: 2026-04-24 15:30 ===
Vault: C:\...\MeinVault
Previous index backed up to last_run.json

[1/5] vault_index.py
Indexed 139 notes (16 MOCs) -> ...\index.json
  OK: index.json ist valide JSON

[2/5] vault_delta.py
Delta: +2 ~3 -0
  OK: delta.json ist valide JSON

[3/5] vault_analyze.py
Broken links: 18 | Orphans: 0 | Tag variants: 2 | FM issues: 9 | Stubs: 2 | MOC drift: 7
  OK: findings.json ist valide JSON

[4/5] vault_trend.py
Trend (2026-04-17 -> 2026-04-24): total_notes: +2 | broken_links: -3 | orphans: +1 | ...
  OK: history.json ist valide JSON

[5/5] scan_sources.py
Missing-sources scan: 76 ohne '## Quellen', 14 leer (gesamt 90)
  OK: missing_sources.json ist valide JSON

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

Claude liest `findings.json`, `delta.json`, `history.json`, `missing_sources.json` und die Config und arbeitet die Probleme in definierter Reihenfolge ab.

Vor dem ersten `Edit` legt Claude einen **konsolidierten Dry-Run-Plan** vor: Änderungen mit `auto_apply: true` laufen ohne Rückfrage, für alles andere holt er **eine** gesammelte Bestätigung. Danach führt er den ganzen Block aus.

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

Jeder Report enthält einen **Trend-Block** aus `history.json` (rollierendes Fenster über die letzten 12 Läufe) — damit siehst du auf einen Blick, ob der Vault sich verbessert oder driftet.

## Der `_maintenance/tasks/`-Ordner

Drop-Zone für einmalige, on-demand erstellte Arbeitspläne (Quellen-Backlogs, Bulk-Refactorings). Wird vom Weekly-Lauf **nicht** befüllt. Abgeschlossene Pläne werden gelöscht, nicht archiviert — der Ordner soll leer sein, wenn nichts ansteht.

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
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\<User>\Obsidian\MeinVault\_maintenance\scripts\Run-Weekly.ps1" -SkipGitCheck'

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
