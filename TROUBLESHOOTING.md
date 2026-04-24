# Troubleshooting

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
cd C:\Users\<User>\Documents\Obsidian\FIS   # zum Vault-Root
claude                                        # von dort starten
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

**Lösung:** In `.claude/commands/weekly-maintenance.md` im Abschnitt "Vault-spezifische Regeln" präzisieren:

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
python _maintenance\scripts\vault_index.py
python _maintenance\scripts\vault_analyze.py
```

Falls Config kaputt: Aus dem Archiv neu kopieren und anpassen.
