#!/usr/bin/env python3
"""
Inspiziert findings.json interaktiv.
Aufruf: python inspect_findings.py <section>
Sections: links, orphans, tags, fm, stubs, mocs, all
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
FINDINGS = SCRIPT_DIR.parent / "state" / "findings.json"

if not FINDINGS.exists():
    print(f"ERROR: {FINDINGS} not found. Run vault_analyze.py first.")
    sys.exit(1)

d = json.loads(FINDINGS.read_text(encoding='utf-8'))


def show_links():
    print(f"\n=== Broken Links ({len(d['broken_links'])}) ===")
    for b in d['broken_links']:
        print(f"  {b['source']} -> [[{b['broken_target']}]]")


def show_orphans():
    print(f"\n=== Orphans ({len(d['orphans'])}) ===")
    for o in d['orphans']:
        tags = ', '.join(o['tags'][:5]) if o['tags'] else '(keine)'
        print(f"  {o['path']} | {o['word_count']}w | {o['age_days']}d | tags: {tags}")


def show_tags():
    print(f"\n=== Tag Variants ({len(d['tag_variants']['autodetected'])}) ===")
    for v in d['tag_variants']['autodetected']:
        print(f"  {v['normalized']}: {v['variants']}")
    if d['tag_variants']['configured']:
        print(f"\n=== Configured Tag Consolidations ===")
        for c in d['tag_variants']['configured']:
            print(f"  {c['canonical']}: {c['found_variants']}")


def show_fm():
    print(f"\n=== Frontmatter Issues ({len(d['frontmatter_issues'])}) ===")
    for i in d['frontmatter_issues']:
        detail = i.get('missing_fields') or i.get('issue')
        print(f"  {i['path']}: {detail}")


def show_stubs():
    print(f"\n=== Stubs ({len(d['stubs'])}) ===")
    for s in d['stubs']:
        print(f"  {s['path']}: {s['word_count']} words")


def show_mocs():
    print(f"\n=== MOC Drift ({len(d['moc_drift'])}) ===")
    for m in d['moc_drift']:
        print(f"\n  MOC: {m['moc']} ({m['unlinked_count']} unlinked)")
        print(f"  Tags: {', '.join(m['moc_tags'])}")
        for c in m['unlinked_candidates'][:10]:
            print(f"    - {c}")
        if m['unlinked_count'] > 10:
            print(f"    ... +{m['unlinked_count'] - 10} more")


SECTIONS = {
    'links': show_links,
    'orphans': show_orphans,
    'tags': show_tags,
    'fm': show_fm,
    'stubs': show_stubs,
    'mocs': show_mocs,
}

if len(sys.argv) < 2 or sys.argv[1] == 'all':
    for fn in SECTIONS.values():
        fn()
elif sys.argv[1] in SECTIONS:
    SECTIONS[sys.argv[1]]()
else:
    print(f"Unknown section: {sys.argv[1]}")
    print(f"Available: {', '.join(SECTIONS.keys())}, all")
    sys.exit(1)
