#!/usr/bin/env python3
"""tier-b-osha: OSHA Severe Injury Report enrichment for the scored mart.

Three phases:
  extract — filter SIR CSV to NAICS-622 hospitals in 10 priority federal-OSHA states, last 24mo
  match   — fuzzy-match Employer name → mart facility_name (state-scoped)
  merge   — write osha_* columns into mart; lift Acute Need 1/2 → 3 for matched rows

Run:
  python3 skills/tier-b-osha/run.py --all
  python3 skills/tier-b-osha/run.py --phase extract
  python3 skills/tier-b-osha/run.py --phase match
  python3 skills/tier-b-osha/run.py --phase merge
"""
from __future__ import annotations
import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw' / 'osha-sir'
STAGE = ROOT / 'data' / 'staging'
MART = ROOT / 'data' / 'mart'
SCORED_MART = MART / 'tam_scored.csv'

SIR_CSV = RAW / 'January2015toOctober2025.csv'
FILTERED_OUT = STAGE / 'osha_filtered.csv'
MATCHES_OUT = STAGE / 'osha_matches.csv'

# 10 priority federal-OSHA states (the other 5 are state-plan, NOT in this dataset)
STATE_NAME_TO_CODE = {
    'TEXAS': 'TX', 'NEW YORK': 'NY', 'NEW JERSEY': 'NJ', 'LOUISIANA': 'LA',
    'FLORIDA': 'FL', 'ILLINOIS': 'IL', 'ARIZONA': 'AZ', 'MASSACHUSETTS': 'MA',
    'CONNECTICUT': 'CT', 'COLORADO': 'CO',
}
# State-plan states (excluded from federal SIR):
STATE_PLAN_EXCLUDED = {'CA', 'WA', 'OR', 'MD', 'NC'}

# 24-month recency window (from today)
RECENCY_CUTOFF = date.today() - timedelta(days=365 * 2)

# Csv I/O
def read_csv(path: Path, encoding='utf-8') -> list[dict]:
    with open(path, encoding=encoding, errors='replace', newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(''); return
    fields = list({k: None for r in rows for k in r}.keys())
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def banner(label: str):
    bar = '=' * 70
    print(f'\n{bar}\n{label}\n{bar}')

# ----------------------------------------------------------------------------
# Phase 1: extract
# ----------------------------------------------------------------------------
def phase_extract() -> Path:
    banner('PHASE 1 · EXTRACT · filter SIR to NAICS-622 + priority states + last 24mo')
    if not SIR_CSV.exists():
        print(f'  ! {SIR_CSV.relative_to(ROOT)} not found — re-download per SKILL.md'); sys.exit(1)
    out_rows = []
    total = naics622 = priority = recent = 0
    with open(SIR_CSV, encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            total += 1
            naics = (row.get('Primary NAICS') or '').strip()
            if not naics.startswith('622'):
                continue
            naics622 += 1
            state_name = (row.get('State') or '').strip().upper()
            code = STATE_NAME_TO_CODE.get(state_name)
            if not code:
                continue
            priority += 1
            event_date_str = (row.get('EventDate') or '').strip()
            try:
                d = datetime.strptime(event_date_str, '%m/%d/%Y').date()
            except ValueError:
                continue
            if d < RECENCY_CUTOFF:
                continue
            recent += 1
            out_rows.append({
                'osha_id': row.get('ID', '').strip(),
                'event_date': d.isoformat(),
                'employer': (row.get('Employer') or '').strip(),
                'address': (row.get('Address1') or '').strip(),
                'city': (row.get('City') or '').strip(),
                'state': code,
                'zip': (row.get('Zip') or '').strip()[:5],
                'naics': naics,
                'hospitalized': row.get('Hospitalized', '').strip(),
                'event_title': (row.get('EventTitle') or '').strip(),
                'source_title': (row.get('SourceTitle') or '').strip(),
                'nature_title': (row.get('NatureTitle') or '').strip(),
                'narrative': (row.get('Final Narrative') or '').strip()[:500],
                'inspection': row.get('Inspection', '').strip(),
            })
    write_csv(FILTERED_OUT, out_rows)
    print(f'  total SIR records read    : {total:,}')
    print(f'  NAICS-622 (healthcare)    : {naics622:,}')
    print(f'  in priority federal-OSHA  : {priority:,}')
    print(f'  in last 24 months         : {recent:,}')
    print(f'  → {FILTERED_OUT.relative_to(ROOT)}  ({len(out_rows)} rows)')
    print(f'\n  state-plan states NOT covered (need separate scrapes): {", ".join(sorted(STATE_PLAN_EXCLUDED))}')
    return FILTERED_OUT

# ----------------------------------------------------------------------------
# Phase 2: match
# ----------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    for kw in ('hospital', 'medical center', 'health system', 'healthcare',
               'health', 'medical', 'center', 'regional', 'community',
               'memorial', 'general', 'university', 'the', 'and', 'of'):
        s = re.sub(r'\b' + kw + r'\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def _name_score(a: str, b: str) -> float:
    an, bn = _norm(a), _norm(b)
    if not an or not bn:
        return 0.0
    ta, tb = set(an.split()), set(bn.split())
    if not ta or not tb:
        return 0.0
    jac = len(ta & tb) / max(len(ta | tb), 1)
    seq = SequenceMatcher(None, an, bn).ratio()
    return 0.6 * jac + 0.4 * seq

def phase_match() -> Path:
    banner('PHASE 2 · MATCH · fuzzy Employer → mart facility_name')
    if not FILTERED_OUT.exists():
        print('  ! no filtered SIR — run --phase extract first'); sys.exit(1)
    sir_rows = read_csv(FILTERED_OUT)
    mart = read_csv(SCORED_MART)
    # index mart by state for fast lookup
    mart_by_state: dict[str, list[dict]] = defaultdict(list)
    for r in mart:
        mart_by_state[r['state']].append(r)
    matches = []
    matched_employers = 0
    unmatched_employers = 0
    for sir in sir_rows:
        state = sir['state']
        candidates = mart_by_state.get(state, [])
        if not candidates: continue
        best = (0.0, None)
        for c in candidates:
            score = _name_score(sir['employer'], c['facility_name'])
            # zip tiebreaker: small boost if zips match
            if sir.get('zip') and c.get('zip') and sir['zip'][:3] == c['zip'][:3]:
                score += 0.05
            if score > best[0]:
                best = (score, c)
        if best[0] >= 0.60 and best[1]:
            matched_employers += 1
            matches.append({
                'ccn': best[1]['ccn'],
                'facility_name': best[1]['facility_name'],
                'state': state,
                'osha_id': sir['osha_id'],
                'event_date': sir['event_date'],
                'employer': sir['employer'],
                'event_title': sir['event_title'],
                'source_title': sir['source_title'],
                'nature_title': sir['nature_title'],
                'inspection': sir['inspection'],
                # OSHA SIRs don't have per-record URLs on osha.gov — the SIR data
                # is a flat CSV + a Tableau dashboard. The dashboard URL is the
                # canonical "see the data" target; the OSHA ID is shown in the
                # UI so reviewers can search for the specific record inside.
                # NOTE: /severe-injury-reports works (200); /severe-injury-reports/data is 404.
                'evidence_url': 'https://www.osha.gov/severe-injury-reports',
                'confidence': round(best[0], 3),
            })
        else:
            unmatched_employers += 1
    write_csv(MATCHES_OUT, matches)
    # stats
    unique_ccns = len(set(m['ccn'] for m in matches))
    by_state: dict[str, int] = {}
    for m in matches:
        by_state[m['state']] = by_state.get(m['state'], 0) + 1
    print(f'  SIR rows                  : {len(sir_rows)}')
    print(f'  matched at conf ≥ 0.60    : {matched_employers}')
    print(f'  unmatched (likely no CMS row): {unmatched_employers}')
    print(f'  unique facilities tagged  : {unique_ccns}')
    print(f'  by state:')
    for s in sorted(by_state, key=lambda x: -by_state[x]):
        print(f'    {s}: {by_state[s]} incidents → {len(set(m["ccn"] for m in matches if m["state"]==s))} unique facilities')
    print(f'\n  → {MATCHES_OUT.relative_to(ROOT)}')
    return MATCHES_OUT

# ----------------------------------------------------------------------------
# Phase 3: merge into mart
# ----------------------------------------------------------------------------
def phase_merge() -> Path:
    banner('PHASE 3 · MERGE · write osha_* columns + lift Acute Need where citation-grade')
    if not MATCHES_OUT.exists():
        print('  ! no matches — run --phase match first'); sys.exit(1)
    matches = read_csv(MATCHES_OUT)
    # aggregate per ccn
    by_ccn: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_ccn[m['ccn']].append(m)

    rows = read_csv(SCORED_MART)
    lifted = enriched = 0
    for r in rows:
        ccn = r['ccn']
        hits = by_ccn.get(ccn)
        if hits:
            # sort by date desc — first is the most recent
            hits.sort(key=lambda h: h['event_date'], reverse=True)
            top = hits[0]
            natures = sorted(set(h.get('nature_title', '') for h in hits if h.get('nature_title')))
            ids = [h.get('osha_id', '') for h in hits if h.get('osha_id')]
            r['osha_severe_injury_count_24mo'] = len(hits)
            r['osha_first_evidence_url'] = top['evidence_url']
            r['osha_first_evidence_id'] = top.get('osha_id', '')
            r['osha_first_evidence_date'] = top['event_date']
            r['osha_first_evidence_nature'] = top.get('nature_title', '')
            r['osha_first_evidence_event'] = top.get('event_title', '')
            r['osha_evidence_natures'] = '; '.join(natures[:5])
            r['osha_evidence_ids'] = ', '.join(ids)
            r['osha_match_confidence'] = top.get('confidence', '')
            enriched += 1
            # lift Acute Need: 1 or 2 → 3 when count ≥ 1 (any SIR in 24mo is real signal)
            try:
                prev_acute = int(r.get('acute_need') or 0)
            except (TypeError, ValueError):
                prev_acute = 0
            if prev_acute < 3:
                r['acute_need'] = 3
                r['acute_need_evidence'] = (
                    f'OSHA SIR — {len(hits)} severe injury report(s) in last 24mo · '
                    f'most recent {top["event_date"]} · ' + (top.get('nature_title') or 'nature unknown')
                )
                # Recompute via forge-score's score_row so we share one source
                # of truth for the additive formula + StandaloneScore cap.
                # Imported lazily to keep tier-b-osha self-contained otherwise.
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        'forge_score_mod',
                        ROOT / 'skills' / 'forge-score' / 'run.py')
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    recomputed = mod.score_row(r)
                    r['forge_total'] = recomputed['forge_total']
                    r['forge_tier'] = recomputed['forge_tier']
                    r['forge_capped_to_b'] = recomputed.get('forge_capped_to_b', False)
                    r['forge_rationale'] = recomputed['forge_rationale']
                    lifted += 1
                except Exception as e:
                    # Don't let an import hiccup zero the row — leave forge_total
                    # as previously computed and flag for review.
                    r['needs_review'] = True
                    print(f'  ! score_row recompute failed for {r.get("ccn")}: {e}')
        else:
            for col in ('osha_severe_injury_count_24mo', 'osha_first_evidence_url',
                        'osha_first_evidence_date', 'osha_first_evidence_nature',
                        'osha_first_evidence_event', 'osha_evidence_natures',
                        'osha_match_confidence'):
                r.setdefault(col, '')
    fields = list({k: None for r in rows for k in r}.keys())
    with open(SCORED_MART, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    n = len(rows)
    print(f'  facilities tagged with OSHA SIR : {enriched} ({100*enriched/n:.1f}%)')
    print(f'  facilities lifted to Acute=3    : {lifted}')
    print(f'  → {SCORED_MART.relative_to(ROOT)}')
    return SCORED_MART

# ----------------------------------------------------------------------------
PHASES = {'extract': phase_extract, 'match': phase_match, 'merge': phase_merge}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--phase', choices=list(PHASES))
    args = ap.parse_args()
    if args.phase:
        PHASES[args.phase](); return
    if not args.all:
        ap.print_help(); return
    phase_extract()
    phase_match()
    phase_merge()

if __name__ == '__main__':
    main()
