# Troubleshooting

Common problems and fixes.

*[Deutsche Version unten](#troubleshooting-deutsch)*

## Installation problems

### `python -m pip install pyyaml` fails

**Symptom:** `error: externally-managed-environment` or proxy errors.

**Fix:** use a Python user install:

```powershell
python -m pip install --user pyyaml
```

### `.ps1` won't start

**Symptom:**
```
.\Run-Weekly.ps1 cannot be loaded because running scripts is disabled on this system.
```

**Fix:**

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Does not require admin rights.

## Encoding problems

### `UnicodeDecodeError` during the index run

**Symptom:**
```
UnicodeDecodeError: 'charmap' codec can't decode byte ...
```

**Cause:** Windows uses `cp1252` as the default instead of UTF-8.

**Fix 1:** see `INSTALL.md` step 3 — configure the PowerShell profile for UTF-8.

**Fix 2:** if a single note causes it, the script automatically falls back to `cp1252` and flags the file in the index with `error`. Check:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); [print(n['path']) for n in d['notes'] if 'error' in n]"
```

Then re-save that file as UTF-8 in VS Code (status bar bottom right → "Save with Encoding").

### Umlauts show up as `Ã¤`, `Ã¶`

**Cause:** the PowerShell console isn't set to UTF-8.

**Fix:** follow `INSTALL.md` step 3, then open a new session.

## Python errors

### `TypeError: Object of type date is not JSON serializable`

**Cause:** a note has a date in its frontmatter (`erstellt: 2025-03-14`) that YAML parses into a `date` object, which isn't JSON-serializable.

**Fix:** already handled (see `VaultJSONEncoder` in `vault_index.py`). If it still occurs, check that you're on the current version of the script.

### `ModuleNotFoundError: No module named 'yaml'`

**Fix:**

```powershell
python -m pip install pyyaml
```

### `FileNotFoundError: maintenance.yaml`

**Symptom:** the script can't find the config.

**Cause:** the script isn't being invoked from the vault root, or the files were copied into a subfolder.

**Fix:** verify the structure:

```powershell
Test-Path "_maintenance\config\maintenance.yaml"
# should return "True"
```

If `False`: copy the files into the vault root again (see `INSTALL.md` step 1).

## Findings problems

### FM issues = nearly every note

**Symptom:** `Findings: ... FM issues: 137 | ...` (every note flagged)

**Cause:** `required_frontmatter` in `maintenance.yaml` doesn't match your schema.

**Fix:** check which fields actually exist in your vault:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); from collections import Counter; c=Counter(); [c.update(n['frontmatter'].keys()) for n in d['notes']]; [print(f'{k}: {v}') for k,v in c.most_common(20)]"
```

In `maintenance.yaml`, list **only** fields as `required_frontmatter` that exist in at least 80% of your notes. Then:

```powershell
python _maintenance\scripts\vault_analyze.py
```

### Tag variants show hex color codes

**Symptom:**
```
ff0000: [FF0000, ff0000]
ffffff: [FFFFFF, ffffff]
```

**Cause:** the tag regex interprets hex color codes as tags.

**Fix:**

- **Option A (recommended):** ignore them. The slash command already documents that Claude should skip these false positives.
- **Option B:** tighten the regex in `vault_index.py`:
  ```python
  INLINE_TAG_RE = re.compile(r'(?:^|\s)#(?![0-9a-fA-F]{3}\b)(?![0-9a-fA-F]{6}\b)([a-zA-Z0-9/_-]+)')
  ```
  Careful: this breaks any tag that happens to consist only of hex characters.

### Broken links point at existing files

**Symptom:** a note `Firewall.md` exists, but `[[firewall]]` is flagged as broken.

**Cause:** Windows is case-insensitive, Obsidian (mostly) too. The analyzer now checks case-insensitively as a fallback — this should be fixed.

**If it still happens:** make sure you're using the latest `vault_analyze.py`.

### MOC drift returns 0 results despite obvious drift

**Cause:** MOC detection isn't matching. Check:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); [print(n['path']) for n in d['notes'] if n.get('is_moc')]"
```

If your MOCs don't show up here, extend `moc_patterns` in `maintenance.yaml` with your naming conventions (e.g. `"Übersicht"`, `"Hub"`, `"_Index"`).

### Pipeline aborts with "hat ungueltige JSON erzeugt"

**Symptom:**
```
vault_analyze.py hat ungueltige JSON erzeugt (...\findings.json): ...
```

**Cause:** the validation gate in `Run-Weekly.ps1` detected corrupt or half-written
output and aborts before a later step builds on it. Usually a sync client
(Nextcloud, OneDrive) or obsidian-git interfered with the file.

**Fix:** pause syncing briefly and re-run. If it persists, run the affected script
on its own — the actual Python exception then appears directly in the output.

### Sources scan reports 0 files despite being enabled

**Cause:** `include_dir_prefixes` doesn't match any top-level folder, or the notes
sit directly in the vault root (those are skipped when prefixes are set).

**Fix:** check the prefixes against the real folder names — the match is
case-sensitive and works on the folder name including its number (`"02."`).
Alternatively empty the list, which scans all non-excluded folders.

## Git problems

### `git status` shows every file as modified

**Cause:** differing line endings (CRLF vs LF) between Windows and other systems.

**Fix:**

```powershell
git config --global core.autocrlf true
```

Then:

```powershell
git add --renormalize .
git commit -m "Normalize line endings"
```

### "Path too long" error

**Cause:** the Windows 260-character limit with deep folder structures.

**Fix:**

```powershell
git config --system core.longpaths true
```

Plus enable long-path support in Windows:

```
gpedit.msc → Computer Configuration → Administrative Templates
→ System → Filesystem → Enable Win32 long paths
```

## Claude Code problems

### Slash command `/weekly-maintenance` doesn't exist

**Cause:** Claude Code looks for commands in `.claude/commands/` relative to the current directory.

**Fix:**

```powershell
cd C:\Users\<User>\Obsidian\MyVault   # to the vault root
claude                                 # start from there
```

`/weekly-maintenance` is then available.

### Claude refuses to read certain files

**Cause:** path problems with special characters or very long paths.

**Fix:** keep the vault path reasonably short. Spaces are usually fine, but exotic characters (umlauts in path names, not in file names) can cause trouble.

### Claude wants to open all 137 notes

**Cause:** `max_files_to_open_per_run` too high, or Claude ignoring the config.

**Fix:** restrict it explicitly in the prompt:

```
/weekly-maintenance

Open at most 10 files. If there are more issues, put the rest in the "Deferred" section of the report.
```

Then lower the value in `maintenance.yaml`:

```yaml
max_files_to_open_per_run: 10
```

### Claude adds fields that don't belong to my schema

**Symptom:** Claude adds e.g. `type: note` to all notes although `type` doesn't exist in your vault.

**Cause:** the slash command doesn't state your schema clearly enough.

**Fix:** be precise in the "Vault-Konventionen" section of `.claude/commands/weekly-maintenance.md`:

```markdown
- Frontmatter schema: EXACTLY these fields: tags, erstellt, geändert
- Do NOT introduce new fields (no type, no category, no status)
```

## Performance problems

### Index run takes > 30 seconds

**Cause:** vault too large or too many large files.

**Check:**

```powershell
Get-ChildItem -Recurse -Filter *.md | Measure-Object -Property Length -Sum
```

**Fixes:**

1. Don't store attachments as `.md` (they should be binary files)
2. Extend `exclude_dirs` with archives or old folders
3. For very large vaults (>5,000 notes): chunk the index by folder

### findings.json > 500 KB

**Cause:** many problems or a very large vault.

**Fixes:**

1. Clean up once manually: consolidating tags reduces `tag_variants` and `tag_singletons`
2. Reduce `max_files_to_open_per_run`
3. Create specialized slash commands (`/weekly-links`, `/weekly-mocs` separately)

## Last resort: full reset

If nothing works anymore:

```powershell
# throw away state, rebuild
Remove-Item _maintenance\state\*.json -Force -ErrorAction SilentlyContinue
.\_maintenance\scripts\Run-Weekly.ps1 -SkipGitCheck
```

Careful: this also discards `history.json` — the trend history starts over.
Copy it away beforehand if you want to keep it.

If the config is broken: copy it from the workflow repo again and re-adjust.

---

# Troubleshooting (Deutsch)

Häufige Probleme und Lösungen.

## Installations-Probleme

### `python -m pip install pyyaml` schlägt fehl

**Symptom:** `error: externally-managed-environment` oder Proxy-Fehler.

**Lösung:** Python-User-Install nutzen:

```powershell
python -m pip install --user pyyaml
```

### `.ps1` startet nicht

**Symptom:**
```
.\Run-Weekly.ps1 kann nicht geladen werden, da die Ausführung von Skripts auf diesem System deaktiviert ist.
```

**Lösung:**

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Muss nicht als Admin ausgeführt werden.

## Encoding-Probleme

### `UnicodeDecodeError` beim Index-Lauf

**Symptom:**
```
UnicodeDecodeError: 'charmap' codec can't decode byte ...
```

**Ursache:** Windows nutzt `cp1252` als Default statt UTF-8.

**Lösung 1:** Siehe `INSTALL.md` Schritt 3 — PowerShell-Profil für UTF-8 konfigurieren.

**Lösung 2:** Falls eine einzelne Notiz das Problem verursacht: Das Script fällt automatisch auf `cp1252` zurück und markiert die Datei im Index mit `error`. Prüfe:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); [print(n['path']) for n in d['notes'] if 'error' in n]"
```

Die Datei dann in VS Code mit UTF-8 neu speichern (Statusleiste unten rechts → "Save with Encoding").

### Umlaute erscheinen als `Ã¤`, `Ã¶`

**Ursache:** PowerShell-Console nicht auf UTF-8 konfiguriert.

**Lösung:** `INSTALL.md` Schritt 3 befolgen. Dann neue Session öffnen.

## Python-Fehler

### `TypeError: Object of type date is not JSON serializable`

**Ursache:** Eine Notiz hat ein Datum im Frontmatter (`erstellt: 2025-03-14`), das YAML als `date`-Objekt parst, aber nicht JSON-serialisierbar ist.

**Lösung:** Im Archiv bereits gefixt (siehe `VaultJSONEncoder` in `vault_index.py`). Falls Fehler trotzdem auftritt: Prüfe, ob du die aktuelle Version des Scripts hast.

### `ModuleNotFoundError: No module named 'yaml'`

**Lösung:**

```powershell
python -m pip install pyyaml
```

### `FileNotFoundError: maintenance.yaml`

**Symptom:** Script findet Config nicht.

**Ursache:** Script wird nicht aus dem Vault-Root aufgerufen, oder das Archiv wurde in einen Unterordner entpackt.

**Lösung:** Verifikation der Struktur:

```powershell
Test-Path "_maintenance\config\maintenance.yaml"
# Sollte "True" zurückgeben
```

Falls `False`: Archiv neu in den Vault-Root entpacken (siehe `INSTALL.md` Schritt 1).

## Findings-Probleme

### FM issues = fast alle Notizen

**Symptom:** `Findings: ... FM issues: 137 | ...` (jede Notiz markiert)

**Ursache:** `required_frontmatter` in `maintenance.yaml` passt nicht zu deinem Schema.

**Lösung:** Prüfe, welche Felder in deinem Vault tatsächlich existieren:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); from collections import Counter; c=Counter(); [c.update(n['frontmatter'].keys()) for n in d['notes']]; [print(f'{k}: {v}') for k,v in c.most_common(20)]"
```

In `maintenance.yaml` **nur** Felder als `required_frontmatter` eintragen, die in mindestens 80% deiner Notizen existieren. Dann:

```powershell
python _maintenance\scripts\vault_analyze.py
```

### Tag-Variants zeigt Hex-Farbcodes

**Symptom:**
```
ff0000: [FF0000, ff0000]
ffffff: [FFFFFF, ffffff]
```

**Ursache:** Die Regex zur Tag-Erkennung interpretiert Hex-Farbcodes als Tags.

**Lösung:**

- **Option A (empfohlen):** Ignorieren. Im Slash-Command-File ist bereits dokumentiert, dass Claude diese False Positives überspringen soll.
- **Option B:** Regex in `vault_index.py` präzisieren:
  ```python
  INLINE_TAG_RE = re.compile(r'(?:^|\s)#(?![0-9a-fA-F]{3}\b)(?![0-9a-fA-F]{6}\b)([a-zA-Z0-9/_-]+)')
  ```
  Achtung: Das brickt alle Tags, die zufällig nur aus Hex-Zeichen bestehen.

### Broken Links zeigen existierende Dateien

**Symptom:** Eine Notiz `Firewall.md` existiert, aber `[[firewall]]` wird als broken markiert.

**Ursache:** Windows ist case-insensitive, Obsidian (meist) auch. Der Analyzer prüft inzwischen case-insensitive als Fallback — Fehler sollte behoben sein.

**Falls trotzdem auftretend:** Neueste Version von `vault_analyze.py` verwenden.

### MOC-Drift zeigt 0 Ergebnisse trotz offensichtlicher Drift

**Ursache:** MOC-Erkennung greift nicht. Prüfe:

```powershell
python -c "import json; d=json.load(open('_maintenance/state/index.json',encoding='utf-8')); [print(n['path']) for n in d['notes'] if n.get('is_moc')]"
```

Falls deine MOCs hier nicht auftauchen: `moc_patterns` in `maintenance.yaml` erweitern um deine Namenskonventionen (z.B. `"Übersicht"`, `"Hub"`, `"_Index"`).

### Pipeline bricht mit "hat ungueltige JSON erzeugt" ab

**Symptom:**
```
vault_analyze.py hat ungueltige JSON erzeugt (...\findings.json): ...
```

**Ursache:** Das Validierungs-Gate in `Run-Weekly.ps1` hat eine korrupte oder
halb geschriebene Ausgabe erkannt und bricht ab, bevor ein Folgeschritt darauf
aufsetzt. Meist hat ein Sync-Client (Nextcloud, OneDrive) oder obsidian-git in
die Datei gefunkt.

**Lösung:** Sync kurz pausieren und den Lauf wiederholen. Bleibt der Fehler,
das betroffene Skript einzeln starten — die eigentliche Python-Exception steht
dann direkt in der Ausgabe.

### Quellen-Scan meldet 0 Dateien trotz aktivierter Config

**Ursache:** `include_dir_prefixes` matcht keinen Top-Level-Ordner, oder die
Notizen liegen direkt im Vault-Root (die werden bei gesetzten Präfixen
übersprungen).

**Lösung:** Präfixe gegen die echten Ordnernamen prüfen — der Match ist
case-sensitiv und arbeitet auf dem Ordnernamen inklusive Nummer (`"02."`).
Alternativ die Liste leeren, dann werden alle nicht ausgeschlossenen Ordner gescannt.

## Git-Probleme

### `git status` zeigt alle Dateien als geändert

**Ursache:** Unterschiedliche Line-Endings (CRLF vs LF) zwischen Windows und anderen Systemen.

**Lösung:**

```powershell
git config --global core.autocrlf true
```

Anschließend:

```powershell
git add --renormalize .
git commit -m "Normalize line endings"
```

### `Pfad zu lang` Fehler

**Ursache:** Windows-260-Zeichen-Limit bei tiefer Ordnerstruktur.

**Lösung:**

```powershell
git config --system core.longpaths true
```

Zusätzlich Long-Path-Support in Windows aktivieren:

```
gpedit.msc → Computer Configuration → Administrative Templates 
→ System → Filesystem → Enable Win32 long paths
```

## Claude-Code-Probleme

### Slash-Command `/weekly-maintenance` existiert nicht

**Ursache:** Claude Code sucht Commands in `.claude/commands/` relativ zum aktuellen Verzeichnis.

**Lösung:**

```powershell
cd C:\Users\<User>\Obsidian\MeinVault   # zum Vault-Root
claude                                   # von dort starten
```

Dann `/weekly-maintenance` verfügbar.

### Claude weigert sich, bestimmte Dateien zu lesen

**Ursache:** Pfad-Probleme mit Sonderzeichen oder sehr langen Pfaden.

**Lösung:** Vault-Pfad möglichst kurz halten. Leerzeichen sind meist okay, aber exotische Zeichen (Umlaute in Pfadnamen, nicht in Dateinamen) können Probleme machen.

### Claude will alle 137 Notizen öffnen

**Ursache:** `max_files_to_open_per_run` zu hoch, oder Claude ignoriert die Config.

**Lösung:** In der Prompt explizit einschränken:

```
/weekly-maintenance

Öffne maximal 10 Dateien. Bei mehr Issues: Rest in "Deferred"-Sektion des Reports.
```

Danach den Wert in `maintenance.yaml` senken:

```yaml
max_files_to_open_per_run: 10
```

### Claude fügt Felder ein, die nicht in mein Schema gehören

**Symptom:** Claude ergänzt z.B. `type: note` in allen Notizen, obwohl `type` nicht in deinem Vault existiert.

**Ursache:** Der Slash-Command sagt ihm nicht deutlich genug, welches Schema du verwendest.

**Lösung:** In `.claude/commands/weekly-maintenance.md` im Abschnitt "Vault-Konventionen" präzisieren:

```markdown
- Frontmatter-Schema: EXAKT diese Felder: tags, erstellt, geändert
- KEINE neuen Felder einführen (kein type, kein category, kein status)
```

## Performance-Probleme

### Index-Lauf dauert > 30 Sekunden

**Ursache:** Vault zu groß oder sehr viele große Dateien.

**Check:**

```powershell
Get-ChildItem -Recurse -Filter *.md | Measure-Object -Property Length -Sum
```

**Lösungen:**

1. Attachments nicht als `.md` speichern (sollten Binärdateien sein)
2. `exclude_dirs` erweitern um Archive oder alte Ordner
3. Für sehr große Vaults (>5.000 Notizen): Index nach Ordnern chunken

### findings.json > 500 KB

**Ursache:** Viele Probleme oder sehr großer Vault.

**Lösungen:**

1. Erst einmal aufräumen: Tag-Konsolidierung manuell durchführen, reduziert `tag_variants` und `tag_singletons`
2. `max_files_to_open_per_run` reduzieren
3. Spezialisierte Slash-Commands erstellen (`/weekly-links`, `/weekly-mocs` separat)

## Letzter Ausweg: Full Reset

Wenn gar nichts mehr läuft:

```powershell
# State wegwerfen, neu aufbauen
Remove-Item _maintenance\state\*.json -Force -ErrorAction SilentlyContinue
.\_maintenance\scripts\Run-Weekly.ps1 -SkipGitCheck
```

Achtung: Damit geht auch `history.json` verloren — die Trend-Historie startet neu.
Willst du sie behalten, vor dem Reset wegkopieren.

Falls die Config kaputt ist: aus dem Workflow-Repo neu kopieren und anpassen.
