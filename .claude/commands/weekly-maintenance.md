---
description: Wöchentliche Vault-Pflege auf Basis von findings.json
allowed-tools: Read, Edit, Write, Glob, Bash
---

# Weekly Vault Maintenance

Du führst die wöchentliche Pflege von Ivans Obsidian-Vault durch.

## Vorgehen

### Schritt 1: Kontext laden
Lies **ausschließlich** diese Dateien:
- `_maintenance/state/findings.json`
- `_maintenance/state/delta.json`
- `_maintenance/config/maintenance.yaml`

**Lies NICHT das gesamte `index.json`** (kann mehrere MB sein).

### Schritt 2: Priorisieren
Arbeite Probleme in dieser Reihenfolge ab:

1. **Broken Links** (`findings.broken_links`)
   - Prüfe ob Ziel umbenannt wurde (ähnlicher Name in Notiz-Stems)
   - Schlage Fix vor, bevor du editierst
   - Öffne Quell-Datei nur wenn Fix nicht eindeutig ist
   - Links mit Ziel-Namen wie "TODO", "Noch zu schreiben", "WIP" sind bewusste Platzhalter — nicht fixen

2. **Tag-Varianten** (`findings.tag_variants.autodetected`)
   - Identifiziere Paare/Gruppen gleicher Bedeutung
   - Schlage kanonische Form vor
   - Bei Zustimmung: ersetze in allen betroffenen Dateien via `Edit`
   - Hex-Farbcodes (z.B. #FF0000, #FFFFFF) sind False Positives — ignorieren

3. **Frontmatter-Issues** (`findings.frontmatter_issues`)
   - Fehlende Pflichtfelder nachtragen mit sinnvollen Defaults
   - YAML-Parse-Errors: Datei öffnen, Syntax fixen
   - Vault-Schema: `tags`, `erstellt`, `geändert` (keine `type`-Felder einführen)

4. **Orphans** (`findings.orphans`)
   - Für Notizen mit klar zuordenbaren Tags: prüfe passende MOCs in `findings.moc_drift`
   - Schlage MOC-Zuordnung vor (Link in MOC oder Frontmatter-Tag)
   - Notizen ohne klare Zuordnung: nur im Report auflisten

5. **MOC-Drift** (`findings.moc_drift`)
   - Für jeden MOC mit unlinked_candidates: öffne MOC-Datei
   - Füge neue Kandidaten in sinnvoller Struktur hinzu
   - Berücksichtige bestehende Struktur (Überschriften, Kategorien) — nicht einfach am Ende anhängen

6. **Stubs & Singletons** — nur im Report auflisten, keine Auto-Fixes

### Schritt 3: Budget einhalten
- Öffne **maximal `max_files_to_open_per_run`** Dateien (siehe config)
- Bei Überschreitung: Rest in Report-Abschnitt "Deferred"

### Schritt 4: Bestätigung vor destruktiven Änderungen
Frage den User **einmal zusammengefasst** vor:
- Umbenennen von Dateien
- Löschen von Tags in mehr als 5 Dateien
- Änderung an mehr als 3 MOCs gleichzeitig

Kleinere Fixes direkt ausführen.

### Schritt 5: Report schreiben
Schreibe `_maintenance/reports/YYYY-MM-DD.md`:

```markdown
# Weekly Maintenance Report YYYY-MM-DD

## Summary
- Notes scanned: X
- Changes since last run: +A ~M -D
- Issues found / fixed / deferred

## Actions Performed
### Broken Links
- [x] `source.md` -> fixed link to `target.md`

### Tag Consolidation
- [x] Merged `#netzwerk`, `#network` -> `#networking` (12 files)

### MOC Updates
- [x] Added 5 notes to `Networking MOC.md`

### Frontmatter
- [x] Added missing `tags` field to 8 notes

## Deferred
Issues nicht bearbeitet (warum + Vorschlag).

## Observations
Auffälligkeiten für den User.
```

### Schritt 6: Abschluss
- Zeige Zusammenfassung
- Erinnere: `git add . ; git commit -m "Weekly maintenance YYYY-MM-DD"`

## Vault-spezifische Regeln (Ivans FIS-Vault)

- **Frontmatter-Schema**: `tags`, `erstellt`, `geändert` — keine `type`-Felder einführen
- **Sprache**: Deutsch — MOC-Namen und Notiz-Titel auf Deutsch beibehalten
- **MOC-Struktur**: Thematisch strukturiert mit Überschriften — neue Einträge in passende Abschnitte einsortieren
- **Broken-Link-Heuristik**: Bewusste Platzhalter (TODO, WIP, etc.) nicht als Fehler behandeln
- **Tag-Konvention**: Kleinbuchstaben, Bindestrich-getrennt (`#it-security` statt `#ITSecurity`)

## Harte Regeln
- **Keine Datei komplett neu schreiben** — nur gezielte `Edit`-Operationen
- **Keine Löschung von Inhalten** ohne Bestätigung
- **Frontmatter-Edits müssen YAML-valid bleiben** (strings mit Sonderzeichen quoten)
- Wenn unsicher: "needs review" im Report, nicht raten
