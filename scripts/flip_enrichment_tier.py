"""flip_enrichment_tier.py — one-off A↔C swap on the enrichment_tier column.

Run once during the 2026-06-23 tier-letter refactor. After this lands, the
seed pipeline writes 'C' going forward (see commit aea33fc), so re-running
this script on a freshly seeded mart is a no-op for new rows but harmless.

Swaps only A↔C. B is untouched. Other columns are untouched. The script
is idempotent in the sense that running it twice restores the original
state; do not run twice unless that is what you want.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_TARGETS = [
    'data/mart/tam.csv',
    'data/mart/tam_scored.csv',
    'data/staging/forge_01_enrich.csv',
]
JSON_TARGETS = [
    'dashboard/data.json',
]
COL = 'enrichment_tier'

SWAP = {'A': 'C', 'C': 'A'}


def flip_csv(path: Path) -> dict:
    if not path.exists():
        return {'path': str(path), 'status': 'missing'}
    with path.open(newline='') as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if COL not in fieldnames:
            return {'path': str(path), 'status': 'no-column'}
        rows = list(reader)
    flips = 0
    for r in rows:
        v = r.get(COL, '')
        if v in SWAP:
            r[COL] = SWAP[v]
            flips += 1
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())
    return {'path': str(path), 'status': 'flipped', 'rows': len(rows), 'flips': flips}


def flip_json(path: Path) -> dict:
    if not path.exists():
        return {'path': str(path), 'status': 'missing'}
    with path.open() as fh:
        d = json.load(fh)
    rows = d.get('rows', [])
    flips = 0
    for r in rows:
        v = r.get(COL)
        if v in SWAP:
            r[COL] = SWAP[v]
            flips += 1
    with path.open('w') as fh:
        json.dump(d, fh, separators=(',', ':'))
    return {'path': str(path), 'status': 'flipped', 'rows': len(rows), 'flips': flips}


def main() -> int:
    results = []
    for rel in CSV_TARGETS:
        results.append(flip_csv(ROOT / rel))
    for rel in JSON_TARGETS:
        results.append(flip_json(ROOT / rel))
    for r in results:
        print(f"{r['status']:>9}  {r['path']}  rows={r.get('rows','-')}  flips={r.get('flips','-')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
