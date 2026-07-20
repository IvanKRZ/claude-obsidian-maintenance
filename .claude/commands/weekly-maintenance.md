---
description: Wöchentliche Vault-Pflege auf Basis von findings.json
allowed-tools: Read, Edit, Write, Glob, Bash
---

# Weekly Vault Maintenance

Du führst die wöchentliche Pflege dieses Obsidian-Vaults durch.

**Voraussetzung:** `_maintenance/scripts/Run-Weekly.ps1` wurde bereits ausgeführt.
Ist der State älter als ein paar Tage oder fehlt, weise darauf hin, statt auf veralteten Daten zu arbeiten.

**Empfohlene Kadenz:** 1× pro Woche, direkt nach `Run-Weekly.ps1`.
Optional per Windows Task Scheduler automatisierbar:
```
schtasks /Create /SC WEEKLY /D FRI /TN "Vault-Maintenance" /TR "powershell -File <VAULT>\_maintenance\scripts\Run-Weekly.ps1 -SkipGitCheck" /ST 09:00
```
Danach `claude` im Vault starten und `/weekly-maintenance` aufrufen.

> **HARD STOP: `_maintenance/state/index.json` NIEMALS lesen.**
> Die Datei ist mehrere hundert KB groß und sprengt das Kontextfenster.
> Alle benötigten Infos sind bereits in `findings.json` und `delta.json` aufbereitet.
> Wenn du den Drang verspürst, `index.json` zu öffnen: tu es nicht — lies stattdessen die spezifische Quell-Notiz direkt.

## Vorgehen

### Schritt 1: Kontext laden
Lies **ausschließlich** diese fünf Dateien (in dieser Reihenfolge):
1. `_maintenance/state/findings.json` — alle Issues, Vault-Statistiken
2. `_maintenance/state/delta.json` — Änderungen seit letztem Lauf
3. `_maintenance/state/history.json` — Trend-Snapshots der letzten Läufe (sehr klein)
4. `_maintenance/state/missing_sources.json` — Notizen ohne / mit leerem Quellen-Abschnitt
5. `_maintenance/config/maintenance.yaml` — Konfiguration und Schwellwerte

**Erlaubte State-Dateien:** `findings.json`, `delta.json`, `history.json`, `missing_sources.json`
**Verboten:** `index.json` (zu groß — Context-Limit-Fehler)

Vergleiche aktuelle `findings.vault_stats` mit dem vorletzten Eintrag in `history.entries` und nenne im Report relevante Trends (z.B. "broken_links: -12 seit letzter Woche").

### Schritt 2: Priorisieren
Arbeite Probleme in dieser Reihenfolge ab:

1. **Broken Links** (`findings.broken_links`)
   - Prüfe, ob das Ziel umbenannt wurde (ähnlicher Name in den Notiz-Stems)
   - Schlage den Fix vor, bevor du editierst
   - Öffne die Quell-Datei nur, wenn der Fix nicht eindeutig ist
   - Ziele aus `broken_link_ignored_targets` sind bewusste Platzhalter — nicht fixen

2. **Tag-Varianten** (`findings.tag_variants.configured` und `.autodetected`)
   - **Configured mit `auto_apply: true`** → direkt ohne Rückfrage normalisieren
   - **Configured mit `auto_apply: false`** → vorschlagen, Bestätigung abwarten
   - **Autodetected** → vorschlagen und bei Zustimmung in `tag_canonical` aufnehmen
   - Hex-Farbcodes (z.B. `#FF0000`) sind False Positives — ignorieren

3. **Frontmatter-Issues** (`findings.frontmatter_issues`)
   - Fehlende Pflichtfelder aus `required_frontmatter` mit sinnvollen Defaults nachtragen
   - YAML-Parse-Errors: Datei öffnen, Syntax fixen
   - Halte dich strikt an das bestehende Schema — führe keine neuen Felder ein

4. **Orphans** (`findings.orphans`)
   - Für Notizen mit klar zuordenbaren Tags: passende MOCs in `findings.moc_drift` prüfen
   - MOC-Zuordnung vorschlagen (Link im MOC oder Frontmatter-Tag)
   - Notizen ohne klare Zuordnung: nur im Report auflisten

5. **MOC-Drift** (`findings.moc_drift`)
   - Für jeden MOC mit `unlinked_candidates`: MOC-Datei öffnen
   - Kandidaten in die bestehende Struktur einsortieren (Überschriften, Kategorien)
   - Nicht einfach am Dateiende anhängen

6. **Stubs & Singletons** — nur im Report auflisten, keine Auto-Fixes

7. **Fehlende Quellen** (`missing_sources.json`) — **nur Reporting, keine Auto-Fixes**
   - Ist `enabled: false`, überspringe diesen Punkt komplett
   - Zahlen aus `counts` (`no_heading`, `empty_section`, `total`) in den Trend-Block übernehmen
   - Bei signifikantem Anstieg (>5) seit letztem Lauf in "Observations" erwähnen
   - **Nicht** automatisch Quellen recherchieren oder eintragen — das ist ein eigener On-Demand-Task

### Der `_maintenance/tasks/`-Ordner
Drop-Zone für **einmalige, on-demand erstellte Arbeitspläne** (z.B. Quellen-Backlogs, Bulk-Refactorings).
- Wird **nicht** vom Weekly-Lauf befüllt — nur manuell oder von Spezial-Skills
- Frontmatter-Schema: `typ: agent-task`, `status: offen|in-arbeit|abgeschlossen`
- Abgeschlossene Pläne **löschen**, nicht archivieren — der Ordner soll leer sein, wenn nichts ansteht

### Schritt 3: Budget einhalten
- Öffne **maximal `max_files_to_open_per_run`** Dateien (siehe Config)
- Bei Überschreitung: Rest in den Report-Abschnitt "Deferred"

### Schritt 4: Dry-Run-Plan + einmalige Bestätigung
Bevor du `Edit` aufrufst, erstelle einen **konsolidierten Plan** aller geplanten Änderungen in einem Block:

```
## Geplante Änderungen
### Auto-Apply (ohne Rückfrage)
- Tag `Python` -> `python` in 15 Dateien (config: auto_apply)

### Bestätigung benötigt
- Tag `sicherheit` -> `security` in 4 Dateien (config: auto_apply=false)
- MOC `Networking MOC.md`: 5 Kandidaten hinzufügen
- Frontmatter `tags` ergänzen in 8 Dateien
```

Hole eine **einzige** Bestätigung für den Bestätigungs-Block, dann führe alles aus.

**Zwingend Rückfrage** bei:
- Umbenennen oder Löschen von Dateien
- Tag-Operationen mit `auto_apply: false`
- Bulk-Änderungen > 10 Dateien
- Änderungen an > 3 MOCs gleichzeitig

**Auto-Apply ohne Rückfrage** bei:
- Tag-Mappings mit `auto_apply: true` in `tag_canonical`
- Broken-Link-Fixes mit eindeutigem Renaming-Match (≥ 0.9 String-Ähnlichkeit)

### Schritt 5: Report schreiben
Schreibe `_maintenance/reports/YYYY-MM-DD.md`:

```markdown
# Weekly Maintenance Report YYYY-MM-DD

## Summary
- Notes scanned: X
- Changes since last run: +A ~M -D
- Issues found / fixed / deferred

## Trend (vs. vorheriger Lauf, aus history.json)
- broken_links: 14 (-3)
- orphans: 42 (+1)
- frontmatter_issues: 8 (-12)
- moc_drift: 5 (-2)
- missing_sources: 90 (no_heading 76 / empty 14)

## Actions Performed
### Broken Links
- [x] `source.md` -> fixed link to `target.md`

### Tag Consolidation
- [x] Merged `#netzwerk`, `#network` -> `#networking` (12 files)

### MOC Updates
- [x] Added 5 notes to `Networking MOC.md`

### Frontmatter
- [x] Added missing `tags` field to 8 notes

### Missing Sources (Reporting only)
- 76 Notizen ohne Quellen-Heading, 14 mit leerem Abschnitt

## Deferred
Issues nicht bearbeitet (warum + Vorschlag).

## Observations
Auffälligkeiten für den User.
```

### Schritt 6: Abschluss
- Zeige eine Zusammenfassung
- Erinnere: `git add . ; git commit -m "Weekly maintenance YYYY-MM-DD"`

## Vault-Konventionen

Diesen Abschnitt beim Einrichten an den eigenen Vault anpassen — er ist die
einzige vault-spezifische Stelle in dieser Datei. Beispiel:

- **Frontmatter-Schema**: `tags`, `erstellt`, `geändert` — keine neuen Felder einführen
- **Sprache**: Deutsch — MOC-Namen und Notiz-Titel in der Vault-Sprache belassen
- **MOC-Struktur**: Thematisch mit Überschriften gegliedert — neue Einträge einsortieren
- **Tag-Konvention**: Kleinbuchstaben, Bindestrich-getrennt (`#it-security` statt `#ITSecurity`)

## Harte Regeln
- **Keine Datei komplett neu schreiben** — nur gezielte `Edit`-Operationen
- **Keine Löschung von Inhalten** ohne Bestätigung
- **Frontmatter-Edits müssen YAML-valid bleiben** (Strings mit Sonderzeichen quoten)
- Wenn unsicher: "needs review" im Report, nicht raten
