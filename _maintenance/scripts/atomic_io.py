#!/usr/bin/env python3
"""
Gemeinsame Hilfsfunktion für atomares Schreiben.

Alle Wartungs-Skripte schreiben ihre JSON-Artefakte in den State-Ordner, der
über Nextcloud synchronisiert und per obsidian-git auto-committet wird. Ein
direktes ``write_text()`` kann von diesen Prozessen mitten im Schreibvorgang
gelesen werden → halb geschriebene / korrupte JSON, auf der ein Folgeschritt
dann aufsetzt.

``write_atomic()`` schreibt zuerst in ein Tempfile im selben Ordner, flusht es
auf die Platte und ersetzt die Zieldatei dann per ``os.replace()`` (atomarer
Rename auf derselben Partition). Leser sehen dadurch immer entweder die alte
oder die neue vollständige Datei — nie einen Zwischenzustand.
"""
import os
import tempfile
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    """Schreibt ``text`` atomar nach ``path`` (UTF-8, ohne BOM)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
