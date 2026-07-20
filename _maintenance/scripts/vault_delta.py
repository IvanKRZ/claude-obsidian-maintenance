#!/usr/bin/env python3
"""
Vault Delta: Vergleicht index.json mit last_run.json.
Output: _maintenance/state/delta.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime

from atomic_io import write_atomic

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = SCRIPT_DIR.parent / "state"
INDEX_PATH = STATE_DIR / "index.json"
LAST_RUN_PATH = STATE_DIR / "last_run.json"
DELTA_PATH = STATE_DIR / "delta.json"


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    current = load_json(INDEX_PATH)
    if not current:
        print(f"ERROR: {INDEX_PATH} not found. Run vault_index.py first.", file=sys.stderr)
        sys.exit(1)

    last = load_json(LAST_RUN_PATH)
    current_map = {n['path']: n for n in current['notes'] if 'error' not in n}

    if not last:
        delta = {
            "generated": datetime.now().isoformat(timespec='seconds'),
            "first_run": True,
            "added": list(current_map.keys()),
            "modified": [],
            "deleted": [],
            "unchanged_count": 0,
        }
    else:
        last_map = {n['path']: n for n in last['notes'] if 'error' not in n}
        added = [p for p in current_map if p not in last_map]
        deleted = [p for p in last_map if p not in current_map]
        modified = [
            p for p in current_map
            if p in last_map and current_map[p]['hash'] != last_map[p]['hash']
        ]
        unchanged = len(current_map) - len(added) - len(modified)

        delta = {
            "generated": datetime.now().isoformat(timespec='seconds'),
            "first_run": False,
            "previous_run": last.get('generated'),
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "unchanged_count": unchanged,
        }

    write_atomic(
        DELTA_PATH,
        json.dumps(delta, indent=2, ensure_ascii=False),
    )
    print(f"Delta: +{len(delta['added'])} ~{len(delta['modified'])} -{len(delta['deleted'])}")


if __name__ == "__main__":
    main()
