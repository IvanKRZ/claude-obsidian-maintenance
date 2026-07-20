#!/usr/bin/env python3
"""
Sources Scanner: Findet Notizen ohne oder mit leerem Quellen-Abschnitt.
Output: _maintenance/state/missing_sources.json

Gesteuert über den `sources_scan`-Block in maintenance.yaml. Ist er
deaktiviert, schreibt das Skript eine leere Payload (damit Folgeschritte
und der Skill immer eine valide Datei vorfinden) und beendet sich.
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

from atomic_io import write_atomic

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = VAULT_ROOT / "_maintenance" / "config" / "maintenance.yaml"
OUTPUT_PATH = VAULT_ROOT / "_maintenance" / "state" / "missing_sources.json"

# Ein Abschnitt gilt als gefüllt, wenn er eine Quellenangabe (Link, URL,
# ISBN, RFC) oder überhaupt substanziellen Text enthält.
CITATION_RE = re.compile(
    r'\[[^\]]+\]\([^)]+\)|https?://|\[\[[^\]]+\]\]|ISBN|RFC\s?\d',
    re.IGNORECASE,
)
TEXT_RE = re.compile(r'\w{3,}', re.UNICODE)
NEXT_HEADING_RE = re.compile(r'(?m)^#{1,2}\s+')


def load_config() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def should_skip(path: Path, vault_root: Path, exclude_dirs: list[str],
                exclude_patterns: list[str]) -> bool:
    try:
        rel_path = path.relative_to(vault_root)
    except ValueError:
        return True

    exclude_lower = {d.lower() for d in exclude_dirs}
    if any(part.lower() in exclude_lower for part in rel_path.parts):
        return True

    rel_str = rel_path.as_posix().lower()
    return any(p.lower() in rel_str for p in exclude_patterns)


def in_scope(path: Path, vault_root: Path, prefixes: list[str]) -> bool:
    """Ohne konfigurierte Präfixe ist alles im Scope."""
    if not prefixes:
        return True
    rel_parts = path.relative_to(vault_root).parts
    if len(rel_parts) < 2:      # Datei direkt im Vault-Root
        return False
    return any(rel_parts[0].startswith(p) for p in prefixes)


def write_payload(scope: list[str], no_heading: list[str], empty: list[str],
                  enabled: bool) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec='seconds'),
        "enabled": enabled,
        "scope": scope,
        "counts": {
            "no_heading": len(no_heading),
            "empty_section": len(empty),
            "total": len(no_heading) + len(empty),
        },
        "no_heading_files": no_heading,
        "empty_section_files": empty,
    }
    write_atomic(OUTPUT_PATH, json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    config = load_config()
    settings = config.get('sources_scan') or {}

    if not settings.get('enabled', False):
        write_payload([], [], [], enabled=False)
        print("Sources scan disabled (sources_scan.enabled = false) -> leere Payload geschrieben.")
        return

    vault_root = (VAULT_ROOT / config['vault_root']).resolve()
    heading = settings.get('heading', 'Quellen')
    prefixes = settings.get('include_dir_prefixes') or []
    exclude_dirs = config.get('exclude_dirs', [])
    exclude_patterns = config.get('exclude_path_patterns', [])

    heading_re = re.compile(r'(?m)^##\s+' + re.escape(heading) + r'\s*$')

    no_heading: list[str] = []
    empty: list[str] = []

    for md_path in sorted(vault_root.rglob('*.md')):
        if should_skip(md_path, vault_root, exclude_dirs, exclude_patterns):
            continue
        if not in_scope(md_path, vault_root, prefixes):
            continue

        try:
            text = md_path.read_text(encoding='utf-8-sig')
        except (UnicodeDecodeError, OSError):
            continue

        rel = md_path.relative_to(vault_root).as_posix()
        match = heading_re.search(text)
        if not match:
            no_heading.append(rel)
            continue

        # Abschnitt endet an der nächsten H1/H2 (oder am Dateiende)
        tail = text[match.end():]
        next_heading = NEXT_HEADING_RE.search(tail)
        body = tail[:next_heading.start()] if next_heading else tail

        if not (CITATION_RE.search(body) or TEXT_RE.search(body)):
            empty.append(rel)

    scope = sorted(prefixes) if prefixes else ["<alle nicht ausgeschlossenen Ordner>"]
    write_payload(scope, no_heading, empty, enabled=True)

    print(f"Missing-sources scan: {len(no_heading)} ohne '## {heading}', "
          f"{len(empty)} leer (gesamt {len(no_heading) + len(empty)})")
    print(f"Sources -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
