#!/usr/bin/env python3
"""
Vault Analyzer: Findet potenzielle Wartungsprobleme.
Output: _maintenance/state/findings.json
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

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
STATE_DIR = VAULT_ROOT / "_maintenance" / "state"
INDEX_PATH = STATE_DIR / "index.json"
FINDINGS_PATH = STATE_DIR / "findings.json"


def load_config() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


HEX_COLOR_RE = re.compile(r'^[0-9a-fA-F]{3,8}$')


def normalize_tag(tag: str) -> str:
    return tag.lower().replace('_', '-').strip('#')


def is_technical_noise_tag(tag: str) -> bool:
    """Filtert Tags heraus, die technische Werte aus Notiz-Inhalten sind (Hex-Farben etc.)."""
    return bool(HEX_COLOR_RE.match(tag))


IMAGE_EXT_RE = re.compile(r'\.(png|jpg|jpeg|gif|svg|webp|bmp|ico|excalidraw)$', re.IGNORECASE)


def find_broken_links(notes: list[dict], config: dict) -> list[dict]:
    stems = {n['stem'] for n in notes}
    stems_lower = {n['stem'].lower() for n in notes}
    ignored = {t.lower() for t in config.get('broken_link_ignored_targets', [])}
    broken = []
    for note in notes:
        for link in note.get('outgoing_links', []):
            if link.lower() in ignored:
                continue
            # Bild-Embeds und Medien-Dateien ignorieren
            if IMAGE_EXT_RE.search(link):
                continue
            if link not in stems and link.lower() not in stems_lower:
                broken.append({
                    "source": note['path'],
                    "broken_target": link,
                })
    return broken


def find_orphans(notes: list[dict], config: dict) -> list[dict]:
    cutoff = datetime.now().timestamp() - (config['orphan_min_age_days'] * 86400)
    return [
        {
            "path": n['path'],
            "word_count": n['word_count'],
            "tags": n['all_tags'],
            "age_days": int((datetime.now().timestamp() - n['mtime']) / 86400),
        }
        for n in notes
        if n.get('backlink_count', 0) == 0
        and not n.get('is_moc')
        and n['mtime'] < cutoff
    ]


def find_tag_variants(notes: list[dict], config: dict) -> dict:
    variants: dict[str, set[str]] = defaultdict(set)
    for note in notes:
        for tag in note['all_tags']:
            if not is_technical_noise_tag(tag):
                variants[normalize_tag(tag)].add(tag)

    configured = config.get('tag_canonical', {}) or {}
    suggestions = []
    for canonical, value in configured.items():
        # Schema 1 (Liste) und Schema 2 (Objekt mit aliases + auto_apply)
        if isinstance(value, dict):
            aliases = value.get('aliases', []) or []
            auto_apply = bool(value.get('auto_apply', False))
        else:
            aliases = list(value or [])
            auto_apply = False

        all_forms = {canonical} | set(aliases)
        found = [t for t in variants if t in all_forms or any(a in t for a in all_forms)]
        if len(found) > 1:
            suggestions.append({
                "canonical": canonical,
                "found_variants": sorted(set().union(*(variants[f] for f in found))),
                "auto_apply": auto_apply,
            })

    auto = [
        {"normalized": norm, "variants": sorted(forms)}
        for norm, forms in variants.items()
        if len(forms) > 1
    ]
    return {"configured": suggestions, "autodetected": auto}


def find_tag_singletons(notes: list[dict]) -> list[dict]:
    tag_counts: Counter = Counter()
    tag_to_notes: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        for tag in note['all_tags']:
            if not is_technical_noise_tag(tag):
                tag_counts[tag] += 1
                tag_to_notes[tag].append(note['path'])
    return [
        {"tag": tag, "note": tag_to_notes[tag][0]}
        for tag, count in tag_counts.items() if count == 1
    ]


def find_frontmatter_issues(notes: list[dict], config: dict) -> list[dict]:
    required = [r.lower() for r in config.get('required_frontmatter', [])]
    issues = []
    for note in notes:
        if note.get('frontmatter_parse_error'):
            issues.append({"path": note['path'], "issue": "yaml_parse_error"})
            continue

        # Keys sind im Index bereits normalisiert (lowercase)
        fm = note.get('frontmatter', {})
        original_keys = note.get('frontmatter_original_keys', list(fm.keys()))

        missing = [f for f in required if f not in fm]
        if missing:
            issues.append({"path": note['path'], "missing_fields": missing})

        # Case-Inkonsistenzen separat melden
        case_issues = [
            k for k in original_keys
            if k.lower() in required and k != k.lower()
        ]
        if case_issues:
            issues.append({
                "path": note['path'],
                "issue": "case_mismatch",
                "keys": case_issues,
            })
    return issues


def find_stubs(notes: list[dict], config: dict) -> list[dict]:
    threshold = config.get('min_word_count_alert', 20)
    return [
        {"path": n['path'], "word_count": n['word_count']}
        for n in notes
        if n['word_count'] < threshold and not n.get('is_moc')
    ]


def find_moc_drift(notes: list[dict], config: dict) -> list[dict]:
    min_overlap = max(1, int(config.get('moc_drift_min_tag_overlap', 1)))
    max_candidates = int(config.get('moc_drift_max_candidates', 20))
    mocs = [n for n in notes if n.get('is_moc')]

    # Notizen die bereits in irgendeinem MOC verlinkt sind, sind kein Drift-Kandidat
    already_linked_in_any_moc: set[str] = set()
    for moc in mocs:
        for link in moc['outgoing_links']:
            already_linked_in_any_moc.add(link)

    drift = []
    for moc in mocs:
        moc_tags = set(moc['all_tags'])
        if not moc_tags:
            continue
        linked = set(moc['outgoing_links'])

        # Wenn der MOC nur 1 Tag hat, fällt min_overlap auf 1 zurück (sonst nie ein Match)
        effective_overlap = min(min_overlap, len(moc_tags))

        scored = []
        for n in notes:
            if n['path'] == moc['path'] or n.get('is_moc'):
                continue
            if n['stem'] in linked:
                continue
            # Bereits in einem anderen MOC verlinkt → kein Kandidat
            if n['stem'] in already_linked_in_any_moc:
                continue
            overlap = len(set(n['all_tags']) & moc_tags)
            if overlap >= effective_overlap:
                scored.append((overlap, n['path']))

        scored.sort(key=lambda x: (-x[0], x[1]))
        if scored:
            drift.append({
                "moc": moc['path'],
                "moc_tags": sorted(moc_tags),
                "min_overlap_used": effective_overlap,
                "unlinked_candidates": [p for _, p in scored[:max_candidates]],
                "unlinked_count": len(scored),
            })
    return drift


def main():
    config = load_config()
    if not INDEX_PATH.exists():
        print(f"ERROR: {INDEX_PATH} not found. Run vault_index.py first.", file=sys.stderr)
        sys.exit(1)

    index = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    notes = [n for n in index['notes'] if 'error' not in n]

    findings = {
        "generated": datetime.now().isoformat(timespec='seconds'),
        "vault_stats": {
            "total_notes": len(notes),
            "moc_count": sum(1 for n in notes if n.get('is_moc')),
            "orphan_count": sum(1 for n in notes if n.get('backlink_count', 0) == 0),
            "total_unique_tags": len({t for n in notes for t in n['all_tags']}),
        },
        "broken_links": find_broken_links(notes, config),
        "orphans": find_orphans(notes, config),
        "tag_variants": find_tag_variants(notes, config),
        "tag_singletons": find_tag_singletons(notes),
        "frontmatter_issues": find_frontmatter_issues(notes, config),
        "stubs": find_stubs(notes, config),
        "moc_drift": find_moc_drift(notes, config),
    }

    write_atomic(
        FINDINGS_PATH,
        json.dumps(findings, indent=2, ensure_ascii=False),
    )

    summary = (
        f"Broken links: {len(findings['broken_links'])} | "
        f"Orphans: {len(findings['orphans'])} | "
        f"Tag variants: {len(findings['tag_variants']['autodetected'])} | "
        f"FM issues: {len(findings['frontmatter_issues'])} | "
        f"Stubs: {len(findings['stubs'])} | "
        f"MOC drift: {len(findings['moc_drift'])}"
    )
    print(f"Findings -> {FINDINGS_PATH}")
    print(summary)


if __name__ == "__main__":
    main()
