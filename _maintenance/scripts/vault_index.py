#!/usr/bin/env python3
"""
Vault Indexer: Scannt alle .md Dateien und extrahiert Metadaten.
Output: _maintenance/state/index.json
"""
import json
import hashlib
import re
import sys
from pathlib import Path
from datetime import datetime, date

from atomic_io import write_atomic

# UTF-8 Console (Windows)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(1)


class VaultJSONEncoder(json.JSONEncoder):
    """Konvertiert date/datetime automatisch in ISO-Strings."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


# --- Regex Patterns ---
INLINE_TAG_RE = re.compile(r'(?:^|\s)#([a-zA-Z0-9/_-]+)')
# Nur [[...]] ohne vorangestelltem ! (kein Bild-Embed)
WIKILINK_RE = re.compile(r'(?<!!)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]+)?\]\]')
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')
FRONTMATTER_RE = re.compile(r'\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n', re.DOTALL)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
# Erkennt Code-Blöcke (``` ... ```) und Inline-Code (`...`) zum Herausfiltern
CODE_BLOCK_RE = re.compile(r'```.*?```', re.DOTALL)
INLINE_CODE_RE = re.compile(r'`[^`\n]+`')

# --- Pfade ---
SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = VAULT_ROOT / "_maintenance" / "config" / "maintenance.yaml"
OUTPUT_PATH = VAULT_ROOT / "_maintenance" / "state" / "index.json"


def load_config() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {"_parse_error": True}
    return fm, text[match.end():]


def get_fm_value(frontmatter: dict, key: str, default=None):
    """Case-insensitiver Frontmatter-Lookup."""
    key_lower = key.lower()
    for k, v in frontmatter.items():
        if k.lower() == key_lower:
            return v
    return default


def extract_tags(frontmatter: dict, body: str) -> tuple[list[str], list[str]]:
    fm_tags = []
    raw_tags = get_fm_value(frontmatter, 'tags', [])
    if isinstance(raw_tags, str):
        fm_tags = [t.strip() for t in re.split(r'[,\s]+', raw_tags) if t.strip()]
    elif isinstance(raw_tags, list):
        fm_tags = [str(t).strip().lstrip('#') for t in raw_tags if t]
    inline_tags = list(set(INLINE_TAG_RE.findall(body)))
    return fm_tags, inline_tags


def extract_links(body: str) -> list[str]:
    # Code-Blöcke und Inline-Code entfernen, damit darin enthaltene [[Links]] nicht gezählt werden
    clean = CODE_BLOCK_RE.sub('', body)
    clean = INLINE_CODE_RE.sub('', clean)
    wikilinks = [m.strip() for m in WIKILINK_RE.findall(clean)]
    md_links = [
        Path(link).stem
        for _, link in MD_LINK_RE.findall(clean)
        if not link.startswith(('http://', 'https://'))
    ]
    return list(set(wikilinks + md_links))


def extract_first_heading(body: str) -> str | None:
    match = HEADING_RE.search(body)
    return match.group(2).strip() if match else None


def is_moc(path: Path, frontmatter: dict, config: dict) -> bool:
    stem = path.stem
    # Wortgrenzen-Match: Pattern muss als eigenständiges Wort im Stem vorkommen
    for pattern in config['moc_patterns']:
        if re.search(r'(?<![a-zA-Z])' + re.escape(pattern) + r'(?![a-zA-Z])', stem, re.IGNORECASE):
            return True
    fm_type = str(frontmatter.get('type', '')).lower()
    moc_types = config.get('moc_frontmatter_types') or []
    if fm_type in [t.lower() for t in moc_types]:
        return True
    return False


def should_skip(
    path: Path, vault_root: Path, exclude_dirs: list[str], exclude_patterns: list[str]
) -> bool:
    try:
        rel_path = path.relative_to(vault_root)
    except ValueError:
        return True

    rel_parts = rel_path.parts
    rel_str = rel_path.as_posix().lower()

    exclude_lower = {d.lower() for d in exclude_dirs}
    if any(part.lower() in exclude_lower for part in rel_parts):
        return True

    patterns_lower = [p.lower() for p in exclude_patterns]
    if any(pattern in rel_str for pattern in patterns_lower):
        return True

    return False


def analyze_file(path: Path, vault_root: Path, config: dict) -> dict | None:
    try:
        text = path.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:
        # Fallback für Legacy-Dateien mit anderem Encoding
        try:
            text = path.read_text(encoding='cp1252')
        except (UnicodeDecodeError, OSError) as e:
            return {"path": path.relative_to(vault_root).as_posix(), "error": f"encoding: {e}"}
    except OSError as e:
        return {"path": path.relative_to(vault_root).as_posix(), "error": str(e)}

    frontmatter, body = parse_frontmatter(text)
    fm_tags, inline_tags = extract_tags(frontmatter, body)
    links = extract_links(body)
    stat = path.stat()

# Frontmatter mit normalisierten (lowercase) Keys für konsistente Prüfungen
    normalized_fm = {
        k.lower(): v for k, v in frontmatter.items() if not k.startswith('_')
    }
    return {
        "path": path.relative_to(vault_root).as_posix(),  # Forward-Slashes
        "stem": path.stem,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "hash": hashlib.sha256(text.encode('utf-8')).hexdigest()[:16],
        "frontmatter": normalized_fm,
        "frontmatter_original_keys": sorted(k for k in frontmatter.keys() if not k.startswith('_')),
        "frontmatter_parse_error": frontmatter.get('_parse_error', False),
        "fm_tags": fm_tags,
        "inline_tags": inline_tags,
        "all_tags": sorted(set(fm_tags + inline_tags)),
        "outgoing_links": links,
        "first_heading": extract_first_heading(body),
        "word_count": len(body.split()),
        "is_moc": is_moc(path, frontmatter, config),
    }


def build_backlinks(notes: list[dict]) -> None:
    stem_to_path = {n['stem']: n['path'] for n in notes if 'error' not in n}
    backlinks: dict[str, list[str]] = {}

    for note in notes:
        if 'error' in note:
            continue
        for link_target in note['outgoing_links']:
            target_path = stem_to_path.get(link_target)
            if target_path and target_path != note['path']:
                backlinks.setdefault(target_path, []).append(note['path'])

    for note in notes:
        if 'error' in note:
            continue
        note['backlinks'] = sorted(set(backlinks.get(note['path'], [])))
        note['backlink_count'] = len(note['backlinks'])


def main():
    config = load_config()
    vault_root = (VAULT_ROOT / config['vault_root']).resolve()
    exclude_dirs = config.get('exclude_dirs', [])
    exclude_patterns = config.get('exclude_path_patterns', [])

    print(f"Scanning vault: {vault_root}")
    notes = []
    for md_path in vault_root.rglob('*.md'):
        if should_skip(md_path, vault_root, exclude_dirs, exclude_patterns):
            continue
        result = analyze_file(md_path, vault_root, config)
        if result:
            notes.append(result)

    build_backlinks(notes)

    index = {
        "generated": datetime.now().isoformat(timespec='seconds'),
        "vault_root": str(vault_root),
        "note_count": len(notes),
        "error_count": sum(1 for n in notes if 'error' in n),
        "moc_count": sum(1 for n in notes if n.get('is_moc')),
        "notes": notes,
    }

    write_atomic(
        OUTPUT_PATH,
        json.dumps(index, indent=2, ensure_ascii=False, cls=VaultJSONEncoder),
    )
    print(f"Indexed {len(notes)} notes ({index['moc_count']} MOCs) -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
