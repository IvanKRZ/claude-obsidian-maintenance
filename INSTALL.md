# Installation

One-time setup of the vault maintenance workflow.

*[Deutsche Version unten](#installation-deutsch)*

## Step 1: Copy files into the vault

Copy `_maintenance/` and `.claude/` **directly into your Obsidian vault root** (not into a subfolder) — at the same level as your `.obsidian/` configuration.

**Example:**
```
C:\Users\<User>\Obsidian\MyVault\
├── .obsidian\                (already there)
├── .claude\                  (copied)
├── _maintenance\             (copied)
└── ... your notes ...
```

The markdown docs (`README.md`, `INSTALL.md`, …) are best left in the workflow repo — otherwise they show up as notes in your vault graph.

If your vault already has a `.claude/` directory, copy only `commands/weekly-maintenance.md` into it.

## Step 2: Python dependency

```powershell
python -m pip install pyyaml
```

Verify:

```powershell
python -m pip show pyyaml
```

## Step 3: Enable UTF-8 for PowerShell

Windows defaults to `cp1252`. With non-ASCII characters in your notes that causes encoding errors.

### Open the PowerShell profile

```powershell
if (-not (Test-Path $PROFILE)) { New-Item -Path $PROFILE -ItemType File -Force }
notepad $PROFILE
```

### Add these lines and save

```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
```

### Reload the profile

```powershell
. $PROFILE
```

Or simply open a new PowerShell session.

## Step 4: Execution policy (if needed)

If `.ps1` scripts refuse to start with "running scripts is disabled on this system":

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Does not require administrator rights.

## Step 5: Extend .gitignore

Add these lines to your vault's `.gitignore` (if not already present):

```gitignore
# Vault Maintenance
_maintenance/state/
!_maintenance/state/.gitkeep
```

Without this, temporary state files end up in the Git repo.

PowerShell shortcut:

```powershell
Add-Content -Path .gitignore -Value "`n# Vault Maintenance"
Add-Content -Path .gitignore -Value "_maintenance/state/"
Add-Content -Path .gitignore -Value "!_maintenance/state/.gitkeep"
```

## Step 6: Adjust the configuration

Open `_maintenance\config\maintenance.yaml` and review especially:

### required_frontmatter
Must match your vault's actual schema. Do **not** just keep the defaults — if you use `erstellt` instead of `created`, that's what belongs here:

```yaml
required_frontmatter:
  - tags
  - erstellt
  - geändert
```

To check which fields your vault actually uses (after the first index run):

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); from collections import Counter; c=Counter(); [c.update(n['frontmatter'].keys()) for n in d['notes']]; [print(f'{k}: {v}') for k,v in c.most_common(20)]"
```

Only list fields as required that exist in **at least 80%** of your notes.

### moc_patterns
Filename patterns for MOCs/HUBs. Default:

```yaml
moc_patterns:
  - "MOC"
  - "HUB"
  - "Index"
```

If you use different naming conventions (e.g. `Übersicht`, `Hub`), add them here.

### exclude_dirs and exclude_path_patterns
`exclude_dirs` matches **exact folder names**, `exclude_path_patterns` matches as a
case-insensitive **substring** against the relative path. You need the latter for
folders with a numeric prefix:

```yaml
exclude_dirs:
  - ".obsidian"
  - ".trash"
  - ".git"
  - ".claude"
  - "_maintenance"

exclude_path_patterns:
  - "templates"        # matches "10. Templates/", "99 Templates/", ...
  - "archive"
```

Add further folders of your own (e.g. `attachments`, `Daily Notes`) here.

### tag_canonical
Leave empty on first setup. After the first run, `findings.tag_variants.autodetected`
shows which variants actually occur — adopt those deliberately. Set
`auto_apply: true` only for unambiguous mappings (pure casing or language normalization).

### sources_scan
Disabled by default (`enabled: false`). Enable only if your content notes have a
fixed sources heading:

```yaml
sources_scan:
  enabled: true
  heading: "Quellen"              # or "Sources"
  include_dir_prefixes: ["02.", "03."]   # empty = all folders
```

## Step 7: First baseline run

Test the pipeline without Claude:

```powershell
.\_maintenance\scripts\Run-Weekly.ps1 -SkipGitCheck
```

Expected output roughly:

```
[1/5] vault_index.py
Indexed 137 notes (16 MOCs) -> ...\index.json
  OK: index.json ist valide JSON

[2/5] vault_delta.py
Delta: +137 ~0 -0
  OK: delta.json ist valide JSON

[3/5] vault_analyze.py
Broken links: 20 | Orphans: 0 | Tag variants: 2 | FM issues: 11 | Stubs: 2 | MOC drift: 9
  OK: findings.json ist valide JSON

[4/5] vault_trend.py
History initialized (1 entry).
  OK: history.json ist valide JSON

[5/5] scan_sources.py
Sources scan disabled (sources_scan.enabled = false) -> leere Payload geschrieben.
  OK: missing_sources.json ist valide JSON
```

If a step aborts with "hat ungueltige JSON erzeugt", that's intentional — the
validation gate prevents later steps from building on corrupt data.

## Step 8: Inspect the findings

```powershell
python _maintenance\scripts\inspect_findings.py all
```

Go through the output and check whether the numbers are plausible. Particularly relevant:

- **FM issues** should be **< 20% of your notes**. Otherwise `required_frontmatter` is misconfigured.
- **Broken links** show real problems **and** deliberate placeholders (TODO, WIP). That's normal.
- **MOC drift** is the actual payoff of this workflow.

If FM issues come out too high, go back to **step 6**, adjust the config, re-run the analyzer.

## Step 9: Adjust the slash command

Open `.claude/commands/weekly-maintenance.md` and adapt the **"Vault-Konventionen"**
section to your vault — frontmatter schema, language, MOC structure, tag convention.
That is the only vault-specific place in the file; everything else applies unchanged
to any vault.

## Step 10: Git baseline

```powershell
git add _maintenance\ .claude\ .gitignore
git commit -m "Setup vault maintenance workflow"
git tag maintenance-v1-baseline
```

The tag gives you a rollback point in case later Claude runs cause trouble.

## Step 11: Optional — alias for quick invocation

Add to your PowerShell profile (`$PROFILE`):

```powershell
function Invoke-VaultMaintenance {
    Push-Location "C:\Users\<User>\Obsidian\MyVault"
    try {
        .\_maintenance\scripts\Run-Weekly.ps1 @args
    } finally {
        Pop-Location
    }
}
Set-Alias vault-maint Invoke-VaultMaintenance
```

Callable from anywhere afterwards with: `vault-maint`

## Done

You can now move on to the weekly routine — see `WORKFLOW.md`.

---

# Installation (Deutsch)

Einmalige Einrichtung des Vault-Maintenance-Workflows.

## Schritt 1: Dateien in den Vault kopieren

Kopiere `_maintenance/` und `.claude/` **direkt in deine Obsidian-Vault-Root** (nicht in einen Unterordner) — auf dieselbe Ebene wie deine `.obsidian/`-Konfiguration.

**Beispiel:**
```
C:\Users\<User>\Obsidian\MeinVault\
├── .obsidian\                (bereits vorhanden)
├── .claude\                  (kopiert)
├── _maintenance\             (kopiert)
└── ... deine Notizen ...
```

Die Markdown-Doku (`README.md`, `INSTALL.md`, …) bleibt am besten im Workflow-Repo — sonst taucht sie als Notiz in deinem Vault-Graph auf.

Hat dein Vault bereits ein `.claude/`-Verzeichnis, kopiere nur `commands/weekly-maintenance.md` hinein.

## Schritt 2: Python-Dependency

```powershell
python -m pip install pyyaml
```

Verifizieren:

```powershell
python -m pip show pyyaml
```

## Schritt 3: UTF-8 für PowerShell aktivieren

Windows nutzt standardmäßig `cp1252`. Bei deutschen Umlauten in Notizen führt das zu Encoding-Fehlern.

### PowerShell-Profil öffnen

```powershell
if (-not (Test-Path $PROFILE)) { New-Item -Path $PROFILE -ItemType File -Force }
notepad $PROFILE
```

### Folgende Zeilen einfügen und speichern

```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
```

### Profil neu laden

```powershell
. $PROFILE
```

Oder einfach neue PowerShell-Session öffnen.

## Schritt 4: Execution Policy (falls nötig)

Falls `.ps1`-Scripts nicht starten mit der Fehlermeldung "Die Ausführung von Skripts ist auf diesem System deaktiviert":

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Muss nicht als Administrator ausgeführt werden.

## Schritt 5: .gitignore ergänzen

In die `.gitignore` deines Vaults folgende Zeilen ergänzen (falls noch nicht vorhanden):

```gitignore
# Vault Maintenance
_maintenance/state/
!_maintenance/state/.gitkeep
```

Ohne diesen Eintrag landen temporäre State-Dateien im Git-Repo.

PowerShell-Shortcut:

```powershell
Add-Content -Path .gitignore -Value "`n# Vault Maintenance"
Add-Content -Path .gitignore -Value "_maintenance/state/"
Add-Content -Path .gitignore -Value "!_maintenance/state/.gitkeep"
```

## Schritt 6: Konfiguration anpassen

Öffne `_maintenance\config\maintenance.yaml` und prüfe vor allem:

### required_frontmatter
Muss dem tatsächlichen Schema deines Vaults entsprechen. **Nicht** einfach die Defaults übernehmen — wenn du `erstellt` statt `created` nutzt, muss das hier stehen:

```yaml
required_frontmatter:
  - tags
  - erstellt
  - geändert
```

Zum Prüfen, welche Felder in deinem Vault tatsächlich genutzt werden (nachdem der erste Index-Lauf durchgelaufen ist):

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); from collections import Counter; c=Counter(); [c.update(n['frontmatter'].keys()) for n in d['notes']]; [print(f'{k}: {v}') for k,v in c.most_common(20)]"
```

Als Pflichtfeld nur Felder eintragen, die in **mindestens 80%** der Notizen existieren.

### moc_patterns
Dateinamen-Muster für MOCs/HUBs. Default:

```yaml
moc_patterns:
  - "MOC"
  - "HUB"
  - "Index"
```

Falls du andere Namenskonventionen verwendest (z.B. `Übersicht`, `Hub`), hier ergänzen.

### exclude_dirs und exclude_path_patterns
`exclude_dirs` matcht **exakte Ordnernamen**, `exclude_path_patterns` als
case-insensitiver **Substring** auf dem relativen Pfad. Letzteres brauchst du bei
Ordnern mit Nummern-Präfix:

```yaml
exclude_dirs:
  - ".obsidian"
  - ".trash"
  - ".git"
  - ".claude"
  - "_maintenance"

exclude_path_patterns:
  - "templates"        # matcht "10. Templates/", "99 Templates/", ...
  - "archive"
```

Weitere eigene Ordner (z.B. `attachments`, `Daily Notes`) hier ergänzen.

### tag_canonical
Beim ersten Setup leer lassen. Nach dem ersten Lauf zeigt dir
`findings.tag_variants.autodetected`, welche Varianten tatsächlich vorkommen —
die übernimmst du dann gezielt. `auto_apply: true` nur bei eindeutigen Mappings
(reine Groß-/Kleinschreibung oder Sprach-Normalisierung).

### sources_scan
Standardmäßig `enabled: false`. Nur aktivieren, wenn deine inhaltlichen Notizen
eine feste Quellen-Überschrift haben:

```yaml
sources_scan:
  enabled: true
  heading: "Quellen"              # oder "Sources"
  include_dir_prefixes: ["02.", "03."]   # leer = alle Ordner
```

## Schritt 7: Erster Baseline-Lauf

Teste die Pipeline ohne Claude:

```powershell
.\_maintenance\scripts\Run-Weekly.ps1 -SkipGitCheck
```

Erwartete Ausgabe etwa:

```
[1/5] vault_index.py
Indexed 137 notes (16 MOCs) -> ...\index.json
  OK: index.json ist valide JSON

[2/5] vault_delta.py
Delta: +137 ~0 -0
  OK: delta.json ist valide JSON

[3/5] vault_analyze.py
Broken links: 20 | Orphans: 0 | Tag variants: 2 | FM issues: 11 | Stubs: 2 | MOC drift: 9
  OK: findings.json ist valide JSON

[4/5] vault_trend.py
History initialized (1 entry).
  OK: history.json ist valide JSON

[5/5] scan_sources.py
Sources scan disabled (sources_scan.enabled = false) -> leere Payload geschrieben.
  OK: missing_sources.json ist valide JSON
```

Bricht ein Schritt mit "hat ungueltige JSON erzeugt" ab, ist das Absicht — das
Validierungs-Gate verhindert, dass Folgeschritte auf korrupten Daten aufsetzen.

## Schritt 8: Findings inspizieren

```powershell
python _maintenance\scripts\inspect_findings.py all
```

Gehe die Ausgabe durch und prüfe, ob die Werte plausibel sind. Besonders relevant:

- **FM issues** sollten **< 20% der Notizen** sein. Sonst ist `required_frontmatter` falsch konfiguriert.
- **Broken links** zeigen echte Probleme **und** bewusste Platzhalter (TODO, WIP). Das ist normal.
- **MOC drift** ist der eigentliche Ertrag des Workflows.

Falls FM issues zu hoch ausfallen, zurück zu **Schritt 6**, Config anpassen, Analyzer neu laufen lassen.

## Schritt 9: Slash-Command anpassen

Öffne `.claude/commands/weekly-maintenance.md` und passe den Abschnitt
**"Vault-Konventionen"** an deinen Vault an — Frontmatter-Schema, Sprache,
MOC-Struktur, Tag-Konvention. Das ist die einzige vault-spezifische Stelle
in der Datei; alles andere gilt unverändert für jeden Vault.

## Schritt 10: Git-Baseline

```powershell
git add _maintenance\ .claude\ .gitignore
git commit -m "Setup vault maintenance workflow"
git tag maintenance-v1-baseline
```

Der Tag gibt dir einen Rollback-Punkt, falls spätere Claude-Läufe Probleme machen.

## Schritt 11: Optional — Alias für schnellen Aufruf

Ins PowerShell-Profil (`$PROFILE`) eintragen:

```powershell
function Invoke-VaultMaintenance {
    Push-Location "C:\Users\<User>\Obsidian\MeinVault"
    try {
        .\_maintenance\scripts\Run-Weekly.ps1 @args
    } finally {
        Pop-Location
    }
}
Set-Alias vault-maint Invoke-VaultMaintenance
```

Danach überall aufrufbar mit: `vault-maint`

## Erledigt

Du kannst jetzt zum wöchentlichen Ablauf übergehen — siehe `WORKFLOW.md`.
