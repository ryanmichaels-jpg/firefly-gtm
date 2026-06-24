#!/usr/bin/env python3
"""tier-b-contracts: USAspending federal-recipient enrichment for hospitals.

Pulls each facility's last-5-year federal contract/grant footprint from the
public USAspending.gov API (no key, no Apify). For academic medical centers
(NYP, UW Medicine/Harborview, etc.) this yields a real signal — research
grants, DoD partnerships, HHS pilots. For private/Catholic systems with no
federal recipient activity, fields land as null with needs_review=False
(absence-of-signal is itself a signal).

Per CLAUDE.md guardrail: paid tools run only on the 5 QSOs (Tier A in the
flipped convention). This skill uses a free public API, so the gate is
softer — `--qsos` is the default scope; `--all` requires stop-and-confirm.

Cache: data/raw/contracts/by-ccn/{ccn}.json — fully re-runnable for $0.

v2 (deferred until SAM.gov API key arrives):
  - Active opportunities (SAM.gov)
  - Recompete radar (period-of-performance end-date detection)

Run:
    python3 skills/tier-b-contracts/run.py --ccn 330101         # one facility
    python3 skills/tier-b-contracts/run.py --qsos               # the 5 QSOs
    python3 skills/tier-b-contracts/run.py --merge              # write to mart
    python3 skills/tier-b-contracts/run.py --all                # asks confirm
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, date, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import httpx

ROOT = Path(__file__).resolve().parents[2]
MART = ROOT / 'data' / 'mart'
SCORED_MART = MART / 'tam_scored.csv'
CACHE_DIR = ROOT / 'data' / 'raw' / 'contracts' / 'by-ccn'

# Tunable knobs
LOOKBACK_YEARS = 5
PAGE_SIZE = 100
MAX_PAGES = 5                   # → 500 award rows per recipient cap (sane default)
HTTP_TIMEOUT = 30
INTER_REQUEST_DELAY = 0.10      # USAspending tolerates ~10 req/sec easily
MATCH_THRESHOLD_OK = 0.70       # similarity below this → flag for review

USA_API = 'https://api.usaspending.gov/api/v2'

# 5 hand-picked QSOs (immutable — matches qso-linkedin)
QSO_CCNS = {
    '500064': 'Harborview Medical Center',
    '310009': 'Clara Maass Medical Center',
    '330101': 'NewYork-Presbyterian Hospital',
    '450046': 'CHRISTUS Spohn Hospital — Corpus Christi',
    '190064': 'Our Lady of the Lake Regional Medical Center',
}

# Suffixes we strip to improve recipient-name search hit-rate.
NAME_SUFFIX_STRIP = (
    'medical center', 'regional medical center', 'community hospital',
    'memorial hospital', 'general hospital', 'hospital', 'health center',
    'health system', 'inc', 'inc.', 'llc', '#1', '#2', '#3',
)

# Contract + grant type codes per USAspending taxonomy.
AWARD_TYPE_CODES = ['A', 'B', 'C', 'D',          # Contracts: BPA Call, Purchase Order, Definitive, DOA
                    '02', '03', '04', '05']      # Direct grants / cooperative agreements


# ============================================================================
# Name normalization + matching
# ============================================================================

def _normalize(name: str) -> str:
    n = (name or '').lower().strip()
    n = re.sub(r'[—–\-]+', ' ', n)
    n = re.sub(r'[^a-z0-9 ]+', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _strip_suffix(name: str) -> str:
    n = _normalize(name)
    for suf in sorted(NAME_SUFFIX_STRIP, key=len, reverse=True):
        if n.endswith(' ' + suf):
            n = n[: -(len(suf) + 1)].strip()
    return n


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


# ============================================================================
# USAspending API thin client
# ============================================================================

def _post(client: httpx.Client, path: str, payload: dict) -> dict:
    time.sleep(INTER_REQUEST_DELAY)
    r = client.post(f'{USA_API}{path}', json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def autocomplete_recipient(client, query: str, limit: int = 10) -> list[dict]:
    """Returns list of {recipient_name, uei, duns, recipient_levels, ...}."""
    j = _post(client, '/autocomplete/recipient/', {'search_text': query, 'limit': limit})
    # API returns a flat list under 'results' for this endpoint.
    return j.get('results', [])


# USAspending splits contracts vs grants/assistance into separate result schemas.
# Each needs its own field list + post-filtering on exact recipient_name (the
# API's recipient_search_text is fuzzy and bleeds in false-positive recipients).
CONTRACT_TYPE_CODES = ['A', 'B', 'C', 'D']
ASSISTANCE_TYPE_CODES = ['02', '03', '04', '05']
CONTRACT_FIELDS = ['Award ID', 'Recipient Name', 'Award Amount',
                   'Awarding Agency', 'Awarding Sub Agency',
                   'NAICS', 'Description',
                   'generated_internal_id']
ASSISTANCE_FIELDS = ['Award ID', 'Recipient Name', 'Award Amount',
                     'Awarding Agency', 'Awarding Sub Agency',
                     'CFDA Number', 'Description',
                     'generated_internal_id']


def _search_one_class(client, exact_recipient: str, type_codes: list[str],
                      fields: list[str], start_date: str, end_date: str,
                      page_size: int, max_pages: int) -> list[dict]:
    """Run spending_by_award for one award class, post-filter on exact name."""
    results: list[dict] = []
    page = 1
    while page <= max_pages:
        body = {
            'filters': {
                'recipient_search_text': [exact_recipient],
                'time_period': [{'start_date': start_date, 'end_date': end_date}],
                'award_type_codes': type_codes,
            },
            'fields': fields,
            'page': page,
            'limit': page_size,
        }
        j = _post(client, '/search/spending_by_award/', body)
        batch = j.get('results', [])
        if not batch:
            break
        # Post-filter: keep only rows where Recipient Name matches the
        # autocomplete-confirmed exact name (case-insensitive).
        for r in batch:
            if (r.get('Recipient Name') or '').strip().lower() == exact_recipient.strip().lower():
                results.append(r)
        if len(batch) < page_size:
            break
        page += 1
    return results


def search_awards(client, recipient_name: str, start_date: str, end_date: str,
                  page_size: int = PAGE_SIZE, max_pages: int = MAX_PAGES) -> list[dict]:
    """Two API calls (contracts + grants), each post-filtered on exact name."""
    contracts = _search_one_class(client, recipient_name, CONTRACT_TYPE_CODES,
                                  CONTRACT_FIELDS, start_date, end_date,
                                  page_size, max_pages)
    grants = _search_one_class(client, recipient_name, ASSISTANCE_TYPE_CODES,
                               ASSISTANCE_FIELDS, start_date, end_date,
                               page_size, max_pages)
    # Tag each row with its class so aggregate() can branch.
    for r in contracts: r['_class'] = 'contract'
    for r in grants:    r['_class'] = 'assistance'
    return contracts + grants


# ============================================================================
# Per-facility resolve + enrich
# ============================================================================

def resolve_recipient(client, facility_name: str, state: str) -> dict:
    """Try several name variants, pick best similarity match.
    Returns dict with: query, candidates, selected, match_confidence, needs_review."""
    queries = [facility_name, _strip_suffix(facility_name)]
    # de-dupe while preserving order
    seen = set(); qs = []
    for q in queries:
        if q and q.lower() not in seen:
            qs.append(q); seen.add(q.lower())

    all_candidates: list[dict] = []
    for q in qs:
        try:
            hits = autocomplete_recipient(client, q)
        except httpx.HTTPError:
            hits = []
        for h in hits:
            name = h.get('recipient_name') or h.get('recipient_levels', {}).get('recipient_name')
            if not name: continue
            sim = _similarity(facility_name, name)
            all_candidates.append({
                'recipient_name': name,
                'uei': h.get('uei'),
                'duns': h.get('duns'),
                'similarity': round(sim, 3),
                'queried_via': q,
            })

    # Dedupe by recipient_name, keep highest similarity
    by_name: dict[str, dict] = {}
    for c in all_candidates:
        existing = by_name.get(c['recipient_name'])
        if not existing or c['similarity'] > existing['similarity']:
            by_name[c['recipient_name']] = c
    ranked = sorted(by_name.values(), key=lambda c: -c['similarity'])

    selected = ranked[0] if ranked else None
    confidence = (selected or {}).get('similarity', 0.0)
    needs_review = confidence < MATCH_THRESHOLD_OK

    return {
        'queries': qs,
        'candidates': ranked[:10],
        'selected': selected,
        'match_confidence': confidence,
        'needs_review': needs_review,
    }


def aggregate(awards: list[dict]) -> dict:
    """Compute per-recipient stats. Handles both contracts (NAICS) and
    grants/assistance (CFDA Number) classes."""
    if not awards:
        return {
            'count': 0, 'contract_count': 0, 'assistance_count': 0,
            'total_award_usd': 0.0,
            'top_naics': None, 'top_naics_desc': None,
            'top_cfda': None,
            'top_funding_agency': None,
            'latest_award_date': None, 'earliest_award_date': None,
            'largest_award_usd': None,
        }
    from collections import Counter
    naics = Counter(); naics_desc: dict[str, str] = {}
    cfda = Counter()
    agencies = Counter()
    total = 0.0
    largest = 0.0
    dates: list[str] = []
    contracts = 0; assistance = 0
    for a in awards:
        amt = a.get('Award Amount') or 0
        try:
            v = float(amt); total += v; largest = max(largest, v)
        except (TypeError, ValueError): pass
        # NAICS arrives as either a dict {code, description} or a string.
        n_raw = a.get('NAICS')
        if isinstance(n_raw, dict):
            code = (n_raw.get('code') or '').strip()
            desc = (n_raw.get('description') or '').strip()
        else:
            code = (n_raw or '').strip()
            desc = (a.get('NAICS Description') or '').strip()
        if code:
            naics[code] += 1
            if desc: naics_desc[code] = desc
        c_raw = (a.get('CFDA Number') or '').strip()
        if c_raw: cfda[c_raw] += 1
        agency = (a.get('Awarding Agency') or '').strip()
        if agency: agencies[agency] += 1
        # Spending_by_award doesn't return Action Date by default in our fields;
        # we don't have a usable date column here, so latest/earliest stay None
        # for now. (Adding Last Modified Date is straightforward later.)
        if a.get('_class') == 'contract':   contracts += 1
        elif a.get('_class') == 'assistance': assistance += 1
    top_n = naics.most_common(1)[0][0] if naics else None
    top_c = cfda.most_common(1)[0][0] if cfda else None
    top_a = agencies.most_common(1)[0][0] if agencies else None
    return {
        'count': len(awards),
        'contract_count': contracts,
        'assistance_count': assistance,
        'total_award_usd': round(total, 2),
        'largest_award_usd': round(largest, 2) if largest else None,
        'top_naics': top_n,
        'top_naics_desc': naics_desc.get(top_n) if top_n else None,
        'top_cfda': top_c,
        'top_funding_agency': top_a,
        'latest_award_date': None,
        'earliest_award_date': None,
    }


def enrich_one(client, ccn: str, facility_name: str, state: str,
               *, force: bool = False, verbose: bool = True) -> dict:
    cache_path = CACHE_DIR / f'{ccn}.json'
    if cache_path.exists() and not force:
        if verbose: print(f'  [{ccn}] using cached {cache_path.relative_to(ROOT)}')
        return json.loads(cache_path.read_text())

    if verbose: print(f'  [{ccn}] resolving recipient: {facility_name!r} ({state})')
    resolved = resolve_recipient(client, facility_name, state)
    selected = resolved.get('selected')

    awards = []
    aggs = aggregate([])
    evidence_url = None
    if selected:
        if verbose:
            print(f'    selected: {selected["recipient_name"]!r}  sim={selected["similarity"]:.2f}'
                  + ('  ⚠ low' if resolved['needs_review'] else ''))
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=365 * LOOKBACK_YEARS)).isoformat()
        try:
            awards = search_awards(client, selected['recipient_name'], start, end)
            aggs = aggregate(awards)
            # Build evidence URL — USAspending search for this recipient (last 5y)
            from urllib.parse import quote
            evidence_url = (
                'https://www.usaspending.gov/search?hash=null'
                f'&keyword={quote(selected["recipient_name"])}'
            )
            if verbose:
                print(f'    awards: {len(awards)}, total ${aggs["total_award_usd"]:,.0f},'
                      f' latest {aggs["latest_award_date"]}')
        except httpx.HTTPError as e:
            if verbose: print(f'    ! search_awards failed: {e}')
    else:
        if verbose: print(f'    no recipient match (will write nulls)')

    record = {
        'ccn': ccn,
        'facility_name': facility_name,
        'state': state,
        'queries': resolved['queries'],
        'candidates': resolved['candidates'],
        'selected_recipient': selected,
        'match_confidence': resolved['match_confidence'],
        'needs_review': resolved['needs_review'],
        'awards': awards,
        'aggregates': aggs,
        'evidence_url': evidence_url,
        'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2))
    if verbose: print(f'    → cached {cache_path.relative_to(ROOT)}')
    return record


# ============================================================================
# Mart merge
# ============================================================================

USA_COLS = [
    'usa_recipient_name', 'usa_recipient_uei', 'usa_match_confidence',
    'usa_needs_review',
    'usa_award_count_5yr', 'usa_contract_count_5yr', 'usa_assistance_count_5yr',
    'usa_total_award_5yr', 'usa_largest_award_5yr',
    'usa_top_naics', 'usa_top_naics_desc', 'usa_top_cfda',
    'usa_top_funding_agency', 'usa_evidence_url',
]


def merge_into_mart() -> int:
    """Read every cache file, write the USA_COLS into tam_scored.csv."""
    if not SCORED_MART.exists():
        print(f'  ! {SCORED_MART} not found — run forge-score first.')
        return 1
    if not CACHE_DIR.exists():
        print(f'  ! cache empty — run enrich first.')
        return 1
    cached = {}
    for f in CACHE_DIR.glob('*.json'):
        try:
            d = json.loads(f.read_text())
            cached[d['ccn']] = d
        except (KeyError, json.JSONDecodeError):
            continue
    with SCORED_MART.open(newline='') as fh:
        rows = list(csv.DictReader(fh))
    fields = list(rows[0].keys()) if rows else []
    for c in USA_COLS:
        if c not in fields:
            fields.append(c)
    populated = 0
    for r in rows:
        d = cached.get(r['ccn'])
        if not d:
            for c in USA_COLS:
                r.setdefault(c, '')
            continue
        populated += 1
        sel = d.get('selected_recipient') or {}
        aggs = d.get('aggregates') or {}
        r['usa_recipient_name'] = sel.get('recipient_name') or ''
        r['usa_recipient_uei'] = sel.get('uei') or ''
        r['usa_match_confidence'] = d.get('match_confidence') or ''
        r['usa_needs_review'] = 'True' if d.get('needs_review') else 'False'
        r['usa_award_count_5yr'] = aggs.get('count') or ''
        r['usa_contract_count_5yr'] = aggs.get('contract_count') or ''
        r['usa_assistance_count_5yr'] = aggs.get('assistance_count') or ''
        r['usa_total_award_5yr'] = aggs.get('total_award_usd') or ''
        r['usa_largest_award_5yr'] = aggs.get('largest_award_usd') or ''
        r['usa_top_naics'] = aggs.get('top_naics') or ''
        r['usa_top_naics_desc'] = aggs.get('top_naics_desc') or ''
        r['usa_top_cfda'] = aggs.get('top_cfda') or ''
        r['usa_top_funding_agency'] = aggs.get('top_funding_agency') or ''
        r['usa_evidence_url'] = d.get('evidence_url') or ''
    with SCORED_MART.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'  → merged {populated} cached records into {SCORED_MART.relative_to(ROOT)}')
    return 0


# ============================================================================
# CLI
# ============================================================================

def _load_facility(ccn: str) -> Optional[dict]:
    if not SCORED_MART.exists():
        return None
    with SCORED_MART.open(newline='') as fh:
        for r in csv.DictReader(fh):
            if r['ccn'] == ccn:
                return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--ccn', help='Enrich one facility')
    g.add_argument('--qsos', action='store_true', help='Enrich the 5 hand-picked QSOs')
    g.add_argument('--all', action='store_true', help='Enrich every forge_tier A facility (will ask confirm)')
    g.add_argument('--merge', action='store_true', help='Merge cached records into tam_scored.csv')
    ap.add_argument('--force', action='store_true', help='Ignore cache and re-fetch')
    args = ap.parse_args()

    if args.merge:
        return merge_into_mart()

    with httpx.Client(headers={'User-Agent': 'firefly-gtm/tier-b-contracts'}) as client:
        if args.ccn:
            row = _load_facility(args.ccn)
            if not row:
                print(f'  ! CCN {args.ccn} not found in mart'); return 1
            enrich_one(client, args.ccn, row.get('facility_name', ''), row.get('state', ''),
                       force=args.force)
            return 0

        if args.qsos:
            print(f'tier-b-contracts: enriching {len(QSO_CCNS)} hand-picked QSOs')
            for ccn, name in QSO_CCNS.items():
                row = _load_facility(ccn)
                state = row.get('state', '') if row else ''
                # Prefer the formal mart name over the QSO_CCNS label
                fn = (row.get('facility_name', '') if row else '') or name
                enrich_one(client, ccn, fn, state, force=args.force)
            return 0

        if args.all:
            # Stop-and-confirm gate per CLAUDE.md hard rule
            if not SCORED_MART.exists():
                print(f'  ! {SCORED_MART} not found'); return 1
            with SCORED_MART.open(newline='') as fh:
                tier_a = [r for r in csv.DictReader(fh) if r.get('forge_tier') == 'A']
            print(f'  Would enrich {len(tier_a)} forge_tier=A facilities.')
            print(f'  USAspending is free; no per-record cost.')
            confirm = input('  Type ENRICH to confirm: ').strip()
            if confirm != 'ENRICH':
                print('  aborted'); return 1
            for r in tier_a:
                enrich_one(client, r['ccn'], r.get('facility_name', ''), r.get('state', ''),
                           force=args.force)
            return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
