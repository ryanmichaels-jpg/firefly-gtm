#!/usr/bin/env python3
"""standalone-score: rank facilities by independence from large health systems.

Per spec (Ryan, 2026-06-23). Adds a 0-100 StandaloneScore that prioritizes
small/independent hospitals and deprioritizes large IDNs. Federal facilities
(VA / IHS / Government - Federal) are gated to score=0 and Excluded=True.

Formula:
    StandaloneScore = max(0, 100 - SCORE_DECAY * log2(N))
where N is the system's hospital count from the AHRQ Compendium.

Bands:
    >= PRIMARY_CUTOFF      -> "Primary"
    < PRIMARY_CUTOFF       -> "Deprioritized"
    federal-gated rows     -> "Excluded"

Run:
    python3 skills/standalone-score/run.py --state WA           # one-state sample
    python3 skills/standalone-score/run.py --all                # all 50 states + DC
    python3 skills/standalone-score/run.py --test               # run assertion tests
"""
from __future__ import annotations
import argparse
import csv
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CMS_HGI = ROOT / 'data' / 'raw' / 'cms-hgi' / 'Hospital_General_Information_2026-05-13.csv'
AHRQ_LINKAGE = ROOT / 'data' / 'raw' / 'ahrq-compendium' / 'chsp-hospital-linkage-2023.csv'
AHRQ_COMPENDIUM = ROOT / 'data' / 'raw' / 'ahrq-compendium' / 'chsp-compendium-2023.csv'
STAGING = ROOT / 'data' / 'staging'

# Tunable formula constants
SCORE_DECAY = 18
PRIMARY_CUTOFF = 40

# 50 states + DC
US_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY','DC'
}

# Federal gate (per spec, extended) — VA / IHS / Government-Federal / DoD / Tribal
FEDERAL_OWNERSHIPS = {
    'Veterans Health Administration',
    'Government - Federal',
    'Department of Defense',
    'Tribal',
}
FEDERAL_SYSTEM_KEYWORDS = ('veterans health administration', 'indian health service')


def score_facility(n: int | float | None, is_federal: bool = False,
                   is_unmatched: bool = False) -> float:
    """Pure score function. Returns 0..100.

    n: system hospital count (defensive — coerced to 1 if missing / <=0)
    is_federal: if True, force 0 (caller also sets Excluded=True)
    is_unmatched: if True, treat as standalone N=1 (caller sets Affiliation_Unverified=True)
    """
    if is_federal:
        return 0.0
    if is_unmatched:
        n = 1
    if n is None or (isinstance(n, float) and math.isnan(n)) or (isinstance(n, (int, float)) and n <= 0):
        n = 1
    return max(0.0, 100.0 - SCORE_DECAY * math.log2(n))


def classify_band(score: float, excluded: bool) -> str:
    if excluded:
        return 'Excluded'
    return 'Primary' if score >= PRIMARY_CUTOFF else 'Deprioritized'


def load_ahrq() -> tuple[dict[str, dict], dict[str, int]]:
    """Return (ccn -> linkage row, health_sys_id -> hosp_cnt)."""
    ccn_to_link: dict[str, dict] = {}
    # AHRQ files use cp1252 (Windows-1252)
    with AHRQ_LINKAGE.open(newline='', encoding='cp1252') as fh:
        for r in csv.DictReader(fh):
            ccn = (r.get('ccn') or '').strip()
            if not ccn:
                continue
            ccn_to_link[ccn.zfill(6)] = r

    sys_to_cnt: dict[str, int] = {}
    with AHRQ_COMPENDIUM.open(newline='', encoding='cp1252') as fh:
        for r in csv.DictReader(fh):
            sid = (r.get('health_sys_id') or '').strip()
            cnt = (r.get('hosp_cnt') or '').strip()
            if not sid:
                continue
            try:
                sys_to_cnt[sid] = int(cnt) if cnt else 0
            except ValueError:
                sys_to_cnt[sid] = 0
    return ccn_to_link, sys_to_cnt


def score_cms_rows(state_filter: str | None = None) -> list[dict]:
    """Score every CMS HGI row, optionally filtered to one state."""
    ccn_to_link, sys_to_cnt = load_ahrq()
    out: list[dict] = []
    with CMS_HGI.open(newline='') as fh:
        for r in csv.DictReader(fh):
            state = (r.get('State') or '').strip().upper()
            if state not in US_STATES:
                continue
            if state_filter and state != state_filter.upper():
                continue

            ccn = (r.get('Facility ID') or '').strip().zfill(6)
            name = (r.get('Facility Name') or '').strip()
            city = (r.get('City/Town') or '').strip()
            htype = (r.get('Hospital Type') or '').strip()
            ownership = (r.get('Hospital Ownership') or '').strip()

            link = ccn_to_link.get(ccn)
            sys_id = (link or {}).get('health_sys_id', '').strip()
            sys_name = (link or {}).get('health_sys_name', '').strip()

            if link is None:
                # not in AHRQ linkage at all -> truly unknown
                is_unmatched = True
                n = 1
                system_display = ''
            elif not sys_id:
                # known standalone in AHRQ but no system_id
                is_unmatched = True
                n = 1
                system_display = ''
            else:
                is_unmatched = False
                n = sys_to_cnt.get(sys_id, 0)
                if n <= 0:
                    # system exists in linkage but missing/zero count in compendium
                    is_unmatched = True
                    n = 1
                system_display = sys_name

            # Federal gate
            is_federal = (
                ownership in FEDERAL_OWNERSHIPS
                or any(kw in sys_name.lower() for kw in FEDERAL_SYSTEM_KEYWORDS)
            )

            score = score_facility(n, is_federal=is_federal, is_unmatched=is_unmatched)
            excluded = is_federal
            band = classify_band(score, excluded)

            out.append({
                'CCN': ccn,
                'Name': name,
                'City': city,
                'State': state,
                'Type': htype,
                'Ownership': ownership,
                'System': system_display,
                'System_Hospital_Count': n,
                'StandaloneScore': round(score, 2),
                'Band': band,
                'Excluded': excluded,
                'Affiliation_Unverified': is_unmatched,
            })
    return out


def write_output(rows: list[dict], out_path: Path) -> None:
    rows_sorted = sorted(
        rows,
        key=lambda r: (-r['StandaloneScore'], r['System_Hospital_Count'], r['Name']),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['CCN', 'Name', 'City', 'State', 'Type', 'Ownership', 'System',
                  'System_Hospital_Count', 'StandaloneScore', 'Band', 'Excluded',
                  'Affiliation_Unverified']
    with out_path.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_sorted)


def print_summary(rows: list[dict], out_path: Path) -> None:
    n_total = len(rows)
    bands: dict[str, int] = {}
    for r in rows:
        bands[r['Band']] = bands.get(r['Band'], 0) + 1
    scores = [r['StandaloneScore'] for r in rows]
    unverified = sum(1 for r in rows if r['Affiliation_Unverified'])

    print()
    print(f'  wrote {out_path.relative_to(ROOT)}  ({n_total} facilities)')
    print()
    print(f'  bands:')
    for band in ('Primary', 'Deprioritized', 'Excluded'):
        cnt = bands.get(band, 0)
        pct = (100 * cnt / n_total) if n_total else 0
        print(f'    {cnt:>5}  {band:<14} ({pct:.1f}%)')
    print()
    if scores:
        print(f'  StandaloneScore distribution:')
        print(f'    min     {min(scores):>6.1f}')
        print(f'    median  {statistics.median(scores):>6.1f}')
        print(f'    mean    {statistics.mean(scores):>6.1f}')
        print(f'    max     {max(scores):>6.1f}')
    print()
    print(f'  Affiliation_Unverified: {unverified} ({100*unverified/n_total:.1f}%)')


# ---------------- tests ----------------

def run_tests() -> int:
    """Per Ryan's spec — exact assertions."""
    failures = 0

    def check(name: str, cond: bool, detail: str = ''):
        nonlocal failures
        if cond:
            print(f'  PASS  {name}')
        else:
            failures += 1
            print(f'  FAIL  {name}{("  -- " + detail) if detail else ""}')

    # Formula tests
    check('score_facility(1) == 100', score_facility(1) == 100)
    check('score_facility(2) == 82', score_facility(2) == 82,
          detail=f'got {score_facility(2)}')
    check('round(score_facility(10)) == 40', round(score_facility(10)) == 40,
          detail=f'got {score_facility(10):.4f}')
    check('score_facility(50) == 0', score_facility(50) == 0,
          detail=f'got {score_facility(50)}')
    check('score_facility(187) == 0', score_facility(187) == 0)

    # Federal gate
    check('federal gate forces 0 regardless of N',
          score_facility(1, is_federal=True) == 0
          and score_facility(187, is_federal=True) == 0)

    # Unmatched
    check('unmatched scores 100', score_facility(None, is_unmatched=True) == 100)

    # Defensive on None / <=0
    check('score_facility(None) == 100', score_facility(None) == 100)
    check('score_facility(0) == 100', score_facility(0) == 100)
    check('score_facility(-3) == 100', score_facility(-3) == 100)

    # Output sorted desc + no nulls (run on a tiny sample)
    rows = score_cms_rows(state_filter='WA')
    if rows:
        out = STAGING / 'hgi_test_scored.csv'
        write_output(rows, out)
        with out.open() as fh:
            written = list(csv.DictReader(fh))
        scores = [float(r['StandaloneScore']) for r in written]
        check('output CSV sorted desc by StandaloneScore',
              all(scores[i] >= scores[i+1] for i in range(len(scores)-1)))
        check('no nulls in StandaloneScore',
              all(r['StandaloneScore'] not in (None, '', 'None') for r in written))
        out.unlink()
    else:
        check('output sort + nulls test (skipped, no WA rows)', True)

    print()
    if failures:
        print(f'{failures} FAILED')
        return 1
    print('all tests passed')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--state', help='Run on one state (e.g. WA)')
    g.add_argument('--all', action='store_true', help='Run on all 50 states + DC')
    g.add_argument('--test', action='store_true', help='Run assertion tests')
    args = ap.parse_args()

    if args.test:
        return run_tests()

    if args.state:
        rows = score_cms_rows(state_filter=args.state)
        out = STAGING / f'standalone_scored_{args.state.upper()}.csv'
    else:
        rows = score_cms_rows()
        out = STAGING / 'hgi_50states_scored.csv'

    write_output(rows, out)
    print_summary(rows, out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
