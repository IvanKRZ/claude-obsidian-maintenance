# Installation

Einmalige Einrichtung des Vault-Maintenance-Workflows.

## Schritt 1: Archiv entpacken

Entpacke den Inhalt des ZIP-Archivs **direkt in deine Obsidian-Vault-Root** (nicht in einen Unterordner). Die Ordner `_maintenance/` und `.claude/` sowie die Markdown-Dateien sollten auf derselben Ebene wie deine `.obsidian/`-Konfiguration liegen.

**Beispiel:**
```
C:\Users\<User>\Documents\Obsidian\FIS\
├── .obsidian\                (bereits vorhanden)
├── .claude\                  (aus dem Archiv)
├── _maintenance\             (aus dem Archiv)
├── README.md                 (aus dem Archiv)
├── INSTALL.md                (aus dem Archiv)
├── WORKFLOW.md               (aus dem Archiv)
├── TROUBLESHOOTING.md        (aus dem Archiv)
└── ... deine Notizen ...
```

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

### exclude_dirs
Ordner, die nicht gescannt werden sollen. Default:

```yaml
exclude_dirs:
  - ".obsidian"
  - ".trash"
  - "_maintenance"
  - "templates"
  - ".git"
```

Wenn du weitere Ordner hast (z.B. `attachments`, `archive`), hier hinzufügen.

## Schritt 7: Erster Baseline-Lauf

Teste die Pipeline ohne Claude:

```powershell
python _maintenance\scripts\vault_index.py
python _maintenance\scripts\vault_delta.py
python _maintenance\scripts\vault_analyze.py
```

Erwartete Ausgabe etwa:

```
Scanning vault: C:\...\FIS
Indexed 137 notes (16 MOCs) -> ...\index.json
Delta: +137 ~0 -0
Findings -> ...\findings.json
Broken links: 20 | Orphans: 0 | Tag variants: 2 | FM issues: 11 | Stubs: 2 | MOC drift: 9
```

## Schritt 8: Findings inspizieren

```powershell
python _maintenance\scripts\inspect_findings.py all
```

Gehe die Ausgabe durch und prüfe, ob die Werte plausibel sind. Besonders relevant:

- **FM issues** sollten **< 20% der Notizen** sein. Sonst ist `required_frontmatter` falsch konfiguriert.
- **Broken links** zeigen echte Probleme **und** bewusste Platzhalter (TODO, WIP). Das ist normal.
- **MOC drift** ist der eigentliche Ertrag des Workflows.

Falls FM issues zu hoch ausfallen, zurück zu **Schritt 6**, Config anpassen, Analyzer neu laufen lassen.

## Schritt 9: Git-Baseline

```powershell
git add _maintenance\ .claude\ .gitignore README.md INSTALL.md WORKFLOW.md TROUBLESHOOTING.md
git commit -m "Setup vault maintenance workflow"
git tag maintenance-v1-baseline
```

Der Tag gibt dir einen Rollback-Punkt, falls spätere Claude-Läufe Probleme machen.

## Schritt 10: Optional — Alias für schnellen Aufruf

Ins PowerShell-Profil (`$PROFILE`) eintragen:

```powershell
function Invoke-VaultMaintenance {
    Push-Location "C:\Users\<User>\Documents\Obsidian\FIS"
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
