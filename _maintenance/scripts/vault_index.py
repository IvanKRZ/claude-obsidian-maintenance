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
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]+)?\]\]')
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')
FRONTMATTER_RE = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.DOTALL)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

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


def extract_tags(frontmatter: dict, body: str) -> tuple[list[str], list[str]]:
    fm_tags = []
    raw_tags = frontmatter.get('tags', [])
    if isinstance(raw_tags, str):
        fm_tags = [t.strip() for t in re.split(r'[,\s]+', raw_tags) if t.strip()]
    elif isinstance(raw_tags, list):
        fm_tags = [str(t).strip().lstrip('#') for t in raw_tags if t]
    inline_tags = list(set(INLINE_TAG_RE.findall(body)))
    return fm_tags, inline_tags


def extract_links(body: str) -> list[str]:
    wikilinks = [m.strip() for m in WIKILINK_RE.findall(body)]
    md_links = [
        Path(link).stem
        for _, link in MD_LINK_RE.findall(body)
        if not link.startswith(('http://', 'https://'))
    ]
    return list(set(wikilinks + md_links))


def extract_first_heading(body: str) -> str | None:
    match = HEADING_RE.search(body)
    return match.group(2).strip() if match else None


def is_moc(path: Path, frontmatter: dict, config: dict) -> bool:
    stem = path.stem.lower()
    if any(pattern.lower() in stem for pattern in config['moc_patterns']):
        return True
    fm_type = str(frontmatter.get('type', '')).lower()
    moc_types = config.get('moc_frontmatter_types') or []
    if fm_type in [t.lower() for t in moc_types]:
        return True
    return False


def should_skip(path: Path, vault_root: Path, exclude_dirs: list[str]) -> bool:
    try:
        rel_parts = path.relative_to(vault_root).parts
    except ValueError:
        return True
    # Case-insensitiv (wichtig auf Windows)
    exclude_lower = {d.lower() for d in exclude_dirs}
    return any(part.lower() in exclude_lower for part in rel_parts)


def analyze_file(path: Path, vault_root: Path, config: dict) -> dict | None:
    try:
        text = path.read_text(encoding='utf-8')
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

    return {
        "path": path.relative_to(vault_root).as_posix(),  # Forward-Slashes
        "stem": path.stem,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "hash": hashlib.sha256(text.encode('utf-8')).hexdigest()[:16],
        "frontmatter": {k: v for k, v in frontmatter.items() if not k.startswith('_')},
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

    print(f"Scanning vault: {vault_root}")
    notes = []
    for md_path in vault_root.rglob('*.md'):
        if should_skip(md_path, vault_root, exclude_dirs):
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

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(index, indent=2, ensure_ascii=False, cls=VaultJSONEncoder),
        encoding='utf-8'
    )
    print(f"Indexed {len(notes)} notes ({index['moc_count']} MOCs) -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
