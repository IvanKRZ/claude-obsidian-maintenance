#!/usr/bin/env python3
"""
Einmaliger Fix: 'Tags:' -> 'tags:' im YAML-Frontmatter.
Dry-run by default. Mit --apply tatsächlich ändern.

Nur ausführen, wenn im Vault inkonsistente Großschreibung des tags-Feldes
vorkommt (Obsidian ist case-sensitive, 'Tags' wird vom Tag-System ignoriert).
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parent.parent

# Nur innerhalb des YAML-Frontmatter-Blocks am Dateianfang
FM_BLOCK_RE = re.compile(r'\A(---\s*\n)(.*?)(\n---\s*\n)', re.DOTALL)
TAGS_LINE_RE = re.compile(r'^Tags:', re.MULTILINE)

apply = '--apply' in sys.argv
fixed = []

for md in VAULT_ROOT.rglob('*.md'):
    if any(part in md.parts for part in ('_maintenance', '.obsidian', '.git', 'templates')):
        continue
    try:
        text = md.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue

    m = FM_BLOCK_RE.match(text)
    if not m:
        continue

    fm_content = m.group(2)
    if not TAGS_LINE_RE.search(fm_content):
        continue

    new_fm = TAGS_LINE_RE.sub('tags:', fm_content)
    if new_fm == fm_content:
        continue

    fixed.append(md.relative_to(VAULT_ROOT))
    if apply:
        new_text = text[:m.start(2)] + new_fm + text[m.end(2):]
        md.write_text(new_text, encoding='utf-8')

mode = "APPLIED" if apply else "DRY-RUN"
print(f"[{mode}] {len(fixed)} files with 'Tags:' -> 'tags:'")
for f in fixed:
    print(f"  {f}")
if not apply and fixed:
    print("\nRun with --apply to actually modify files.")
