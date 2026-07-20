#!/usr/bin/env python3
"""
Vault Trend Aggregator: Hängt aktuelle findings.json-Kennzahlen an history.json an.
Output: _maintenance/state/history.json (rolling window, max 12 Einträge)
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
FINDINGS_PATH = STATE_DIR / "findings.json"
HISTORY_PATH = STATE_DIR / "history.json"
MAX_ENTRIES = 12


def main() -> None:
    if not FINDINGS_PATH.exists():
        print(f"ERROR: {FINDINGS_PATH} nicht gefunden – vault_analyze.py zuerst laufen lassen.", file=sys.stderr)
        sys.exit(1)

    findings = json.loads(FINDINGS_PATH.read_text(encoding='utf-8'))
    stats = findings.get('vault_stats', {})

    snapshot = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "generated": findings.get('generated'),
        "total_notes": stats.get('total_notes', 0),
        "moc_count": stats.get('moc_count', 0),
        "orphan_count": stats.get('orphan_count', 0),
        "total_unique_tags": stats.get('total_unique_tags', 0),
        "broken_links": len(findings.get('broken_links', [])),
        "tag_variants_auto": len(findings.get('tag_variants', {}).get('autodetected', [])),
        "frontmatter_issues": len(findings.get('frontmatter_issues', [])),
        "stubs": len(findings.get('stubs', [])),
        "moc_drift": len(findings.get('moc_drift', [])),
    }

    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding='utf-8'))
    else:
        history = {"entries": []}

    entries = [e for e in history.get('entries', []) if e.get('date') != snapshot['date']]
    entries.append(snapshot)
    entries = entries[-MAX_ENTRIES:]

    write_atomic(
        HISTORY_PATH,
        json.dumps({"entries": entries}, indent=2, ensure_ascii=False),
    )

    if len(entries) >= 2:
        prev, curr = entries[-2], entries[-1]
        deltas = []
        for k in ("total_notes", "broken_links", "orphan_count", "frontmatter_issues", "moc_drift"):
            d = curr.get(k, 0) - prev.get(k, 0)
            sign = "+" if d > 0 else ""
            deltas.append(f"{k}: {sign}{d}")
        print(f"Trend ({prev['date']} -> {curr['date']}): " + " | ".join(deltas))
    else:
        print(f"History initialized ({len(entries)} entry).")

    print(f"History -> {HISTORY_PATH}")


if __name__ == "__main__":
    main()
