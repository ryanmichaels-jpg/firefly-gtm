#!/usr/bin/env python3
"""tier-b-incident: HARD GATE — verifiable on-site violent incident per facility.

Per Ryan's QSO criteria, this is criterion #1 — a HARD GATE. The other four
(proximity, footprint, incumbent vintage, mandate) only RANK; this one
qualifies/disqualifies.

ON-SITE DEFINITION (enforced consistently across QSOs + state-anchor backfill)
============================================================================

PASS (counts as on-site):
  * Violence INSIDE the hospital building (lobby, ED/trauma room, ICU,
    psych unit, etc.)
  * Violence ON the campus / property — including parking lot, parking
    garage, ambulance bay, walkways, grounds. The OLOL Patricia Jackson
    homicide in the parking lot is the canonical PASS example.
  * Violence directed AT staff (nurses, security, doctors, employees) or
    occupants (patients, visitors) while on hospital property
  * Active shooter / barricaded suspect inside hospital space

FAIL (counts as off-site, NOT eligible):
  * Victim was injured ELSEWHERE and transported to / taken to /
    rushed to / brought to / flown to / walked into the hospital for
    treatment. The hospital is the receiving ED, not the site of violence.
  * False alarm / hoax (e.g. CHRISTUS Spohn Nov 13 2024 dementia-patient
    hoax that mobilized 50 officers but had no actual violence)

Implementation
  * Violence verb + location preposition must appear in the same
    sentence (≤80 chars apart) to qualify as on-site.
  * Transported-to verbs ("transported to", "taken to", "rushed to",
    "brought to", "flown to", "walked into") near the hospital name
    trigger FAIL classification.
  * Hoax keywords ("false alarm", "hoax", "no injuries", "no gunman
    found") trigger FAIL even when violence verbs are present.

v1 sources
  - apify/rag-web-browser: targeted Google queries per facility name + violence
    keywords. RAG Web Browser is free platform-compute, 99% success.
  - OSHA SIR (already in tam_scored.csv): date corroboration for on-site
    serious-injury events (NAICS 622, last 24 months). Note: nature codes
    don't distinguish violence vs medical, so RAG is the primary signal.

Deferred sources (v2)
  - Gun Violence Archive (geolocated incidents)
  - GDELT 2.0 Doc API (news events with location coordinates)
  - OSHA Establishment Search (narrative text per inspection)

Run
    python3 skills/tier-b-incident/run.py --qsos          # back-test the 5
    python3 skills/tier-b-incident/run.py --state NY      # anchor-state backfill
    python3 skills/tier-b-incident/run.py --ccn 330101    # single facility
    python3 skills/tier-b-incident/run.py --merge         # write to mart
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

import httpx

ROOT = Path(__file__).resolve().parents[2]
MART = ROOT / 'data' / 'mart'
SCORED_MART = MART / 'tam_scored.csv'
CACHE_DIR = ROOT / 'data' / 'raw' / 'incident' / 'by-ccn'
RAG_DIR = ROOT / 'data' / 'raw' / 'incident' / 'rag'

APIFY_BASE = 'https://api.apify.com/v2'
RAG_ACTOR = 'apify~rag-web-browser'
HTTP_TIMEOUT = 60
APIFY_POLL_SECONDS = 5
APIFY_MAX_WAIT_SECONDS = 360

QSO_CCNS = {
    '500064': 'Harborview Medical Center',
    '310009': 'Clara Maass Medical Center',
    '330101': 'NewYork-Presbyterian Hospital',
    '450046': 'CHRISTUS Spohn Hospital — Corpus Christi',
    '190064': 'Our Lady of the Lake Regional Medical Center',
}

# Three targeted queries per facility — different angles on on-site violence.
QUERY_TEMPLATES = (
    '"{name}" hospital shooting OR stabbing OR attack OR assault',
    '"{name}" "workplace violence" OR rampage OR homicide',
    '"{name}" patient OR staff "attacked" OR "stabbed" OR "shot" OR "killed"',
)

# Violence vocabulary — at least one must appear near the hospital mention.
VIOLENCE_KEYWORDS = (
    'shooting', 'shot', 'stabbing', 'stabbed', 'killed', 'fatally',
    'homicide', 'murder', 'murdered', 'attack', 'attacked', 'assault',
    'assaulted', 'rampage', 'active shooter', 'workplace violence',
    'wounded', 'beat', 'beating', 'destroyed', 'trashed',
)
_VIOLENCE_RE = re.compile(r'\b(' + '|'.join(re.escape(v) for v in VIOLENCE_KEYWORDS) + r')\b', re.I)

# AT-facility markers — require violence verb + location preposition in
# close proximity (same sentence essentially). The earlier broad set
# ("inside" alone, "on hospital" alone) caused false positives on NJ DOH
# score pages ("click on hospital name") and nurse-picket articles
# ("outside Clara Maass" referring to picket location, not violence).
_VERB_GRP = r'(shooting|shot|shooter|active shooter|armed gunman|gunman|stabbed|stabbing|killed|killing|fatally|murder(?:ed)?|homicide|attack(?:ed)?|assault(?:ed)?|rampage|wounded|destroyed|trashed|barricaded)'
_LOC_GRP = r'(inside|at|outside|in (?:the )?(?:parking lot|parking garage|ambulance bay|er|ed|emergency room|emergency department|trauma|lobby|psych)|on (?:the )?(?:hospital|medical center|campus|premises|grounds|property))'
AT_PATTERNS = (
    # violence verb followed by location marker within the same sentence
    rf'\b{_VERB_GRP}\b[^.!?]{{0,80}}\b{_LOC_GRP}\b',
    # location marker followed by violence verb within the same sentence
    rf'\b{_LOC_GRP}\b[^.!?]{{0,80}}\b{_VERB_GRP}\b',
    # role + violence verb (already tight on its own — keep)
    r'\b(employees?|staff|nurses?|patient|doctors?|guards?|officers?)\b[^.!?]{0,30}\b(shot|stabbed|killed|attacked|assaulted|wounded)\b',
)
_AT_RE = re.compile('|'.join(AT_PATTERNS), re.I)

# Transported-to markers (negative — count toward FAIL).
# Expanded after BronxCare FP ("man dumped at Bronx hospital after being
# transported by private means") and other "pronounced dead at" cases where
# the hospital was just the receiving ED.
TRANSPORTED_PATTERNS = (
    r'\btransported (to|by)\b',
    r'\btaken to\b',
    r'\brushed to\b',
    r'\bbrought to\b',
    r'\bflown to\b',
    r'\bairlifted to\b',
    r'\bwalked into\b',
    r'\barriv(?:e|ed|es|ing) at\b',
    r'\badmitted to\b',
    r'\btransferred to\b',
    r'\bdumped at\b',
    r'\bshowed up at\b',
    r'\bcame into\b',
    r'\bself-?presented (to|at)\b',
    r'\bpronounced (dead|deceased) at\b',
    r'\bprivate means\b',
)
_TRANSPORTED_RE = re.compile('|'.join(TRANSPORTED_PATTERNS), re.I)

# False-alarm / hoax markers (further negative) + drill / exercise (UTMC FP)
HOAX_PATTERNS = (
    r'\bfalse alarm\b', r'\bhoax\b', r'\bno injuries\b', r'\bno (one|gunman) found\b',
    r'\bactive shooter training\b', r'\bshooter drill\b', r'\btraining drill\b',
    r'\b(tabletop|live|fire) exercise\b', r'\bsimulation\b', r'\bpreparedness drill\b',
)
_HOAX_RE = re.compile('|'.join(HOAX_PATTERNS), re.I)

# Cyber-incident markers — "attack" / "attacked" verbs are too generic and
# match cyber breaches ("Anatomy of a ransomware attack at Erie County
# Medical Center"). When these appear, the incident is NOT physical violence
# at the facility and must FAIL the gate.
CYBER_PATTERNS = (
    r'\bransomware\b', r'\bcyber\s*(attack|breach|incident)\b',
    r'\bdata\s*breach\b', r'\bphishing\b', r'\bmalware\b',
    r'\bdenial[- ]of[- ]service\b', r'\bIT\s*outage\b',
)
_CYBER_RE = re.compile('|'.join(CYBER_PATTERNS), re.I)


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')


def run_rag(client, query: str, max_results: int = 6) -> list[dict]:
    token = os.environ.get('APIFY_API_TOKEN')
    if not token:
        raise RuntimeError('APIFY_API_TOKEN missing')
    payload = {'query': query, 'maxResults': max_results, 'outputFormats': ['markdown']}
    r = client.post(f'{APIFY_BASE}/acts/{RAG_ACTOR}/runs',
                    params={'token': token}, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    run = r.json()['data']
    waited = 0
    while waited < APIFY_MAX_WAIT_SECONDS:
        time.sleep(APIFY_POLL_SECONDS); waited += APIFY_POLL_SECONDS
        run = client.get(f'{APIFY_BASE}/actor-runs/{run["id"]}',
                         params={'token': token}, timeout=HTTP_TIMEOUT).json()['data']
        if run['status'] in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
            break
    if run['status'] != 'SUCCEEDED':
        raise RuntimeError(f'rag-web-browser status={run["status"]}')
    return client.get(f'{APIFY_BASE}/datasets/{run["defaultDatasetId"]}/items',
                     params={'token': token, 'format': 'json', 'clean': '1'},
                     timeout=HTTP_TIMEOUT).json()


_MONTHS = {m: i for i, m in enumerate(
    ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], start=1)}
_MONTHS_FULL = {m: i for i, m in enumerate(
    ['january','february','march','april','may','june','july','august',
     'september','october','november','december'], start=1)}


def extract_date(result: dict) -> tuple[str | None, int | None]:
    """Returns (iso_date_or_partial, year_int)."""
    desc = ((result.get('searchResult') or {}).get('description') or '').strip()
    # Google snippet leading date ("Jan 9, 2026 — ...")
    m = re.match(r'^\s*(\w{3,9})\s+(\d{1,2}),?\s+(\d{4})\s*[—\-–]', desc, re.I)
    if m:
        mo = _MONTHS.get(m.group(1).lower()[:3]) or _MONTHS_FULL.get(m.group(1).lower())
        if mo:
            y = int(m.group(3)); d = int(m.group(2))
            return (f'{y}-{mo:02d}-{d:02d}', y)
    # URL date path
    url = (result.get('searchResult') or {}).get('url') or ''
    m = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
    if m and 1990 < int(m.group(1)) <= 2030:
        return (f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}', int(m.group(1)))
    # Stand-alone year in title
    m = re.search(r'\b(20\d{2})\b', (result.get('searchResult') or {}).get('title') or '')
    if m and 1990 < int(m.group(1)) <= 2030:
        return (m.group(1), int(m.group(1)))
    return (None, None)


def classify_result(result: dict, hospital_name: str, hospital_state: str) -> dict:
    """For one search result, decide: PASS (on-site verified), FAIL (transported or false alarm),
    or LOW (no clear violence signal). Returns classification + confidence + reason."""
    sr = result.get('searchResult', {}) or {}
    title = sr.get('title') or ''
    desc = sr.get('description') or ''
    body = (result.get('markdown') or result.get('text') or '')[:6000]
    haystack = (title + '\n' + desc + '\n' + body)

    # 1. Hospital must be mentioned somewhere
    name_lo = hospital_name.lower()
    if name_lo not in haystack.lower():
        return {'verdict': 'low', 'confidence': 'low', 'reason': 'no_hospital_mention'}

    # 2. Violence vocabulary check
    if not _VIOLENCE_RE.search(haystack):
        return {'verdict': 'low', 'confidence': 'low', 'reason': 'no_violence_keyword'}

    # 3a. Hoax / false-alarm immediate disqualifier
    if _HOAX_RE.search(haystack):
        return {'verdict': 'fail', 'confidence': 'high', 'reason': 'hoax_or_false_alarm'}
    # 3b. Cyber incident — not physical violence, must FAIL the gate
    if _CYBER_RE.search(haystack):
        return {'verdict': 'fail', 'confidence': 'high', 'reason': 'cyber_incident_not_physical_violence'}

    # 4. AT vs TRANSPORTED proximity check — tight window (±120 chars) around
    # the hospital name. Wider windows let generic union-publication prose
    # ("nurses attacked at hospitals... Bellevue is mentioned 300 chars later")
    # falsely attribute to a specific facility. Tight window forces the
    # violence verb + location preposition to share roughly the same sentence
    # as the hospital name mention.
    name_idx = haystack.lower().find(name_lo)
    window = haystack[max(0, name_idx - 120):name_idx + len(name_lo) + 120]
    at_hits = list(_AT_RE.finditer(window))
    transported_hits = list(_TRANSPORTED_RE.finditer(window))

    if at_hits and not transported_hits:
        # Strong "AT" signal, no "transported" — high-confidence PASS
        return {'verdict': 'pass', 'confidence': 'high',
                'reason': f'at_facility: {at_hits[0].group(0)}'}
    if transported_hits and not at_hits:
        return {'verdict': 'fail', 'confidence': 'high',
                'reason': f'transported_to: {transported_hits[0].group(0)}'}
    if at_hits and transported_hits:
        # Mixed — DEFAULT TO FAIL (transported-to should dominate). The original
        # default of PASS bled in FPs like "killed in shooting OUTSIDE [church],
        # taken to Jamaica Hospital" — the AT pattern was the generic "outside",
        # not "outside hospital". Real PASS cases don't have transported verbs
        # in the same window (Mount Sinai, Richmond U, Jacobi all had ZERO
        # transported hits). Only override to PASS if a hospital-specific AT
        # phrase exists ("inside the ED", "on hospital property", etc.).
        hospital_specific_at = re.compile(
            r'\b(inside|on)\b[^.!?]{0,40}\b(hospital|medical center|ed|emergency (room|department)|trauma|campus|premises|property|grounds)\b',
            re.I)
        if hospital_specific_at.search(window):
            return {'verdict': 'pass', 'confidence': 'medium',
                    'reason': f'at_facility w/ hospital-specific override: {at_hits[0].group(0)}'}
        return {'verdict': 'fail', 'confidence': 'high',
                'reason': f'transported_to dominates: {transported_hits[0].group(0)}'}
    # Violence keyword present but no clear AT/transport distinguishing phrase
    return {'verdict': 'medium', 'confidence': 'medium', 'reason': 'violence_no_locator'}


# ============================================================================
# Per-facility enrich
# ============================================================================

def enrich_one(client, ccn: str, facility_name: str, state: str,
               *, force: bool = False, verbose: bool = True) -> dict:
    cache_path = CACHE_DIR / f'{ccn}.json'
    if cache_path.exists() and not force:
        if verbose: print(f'  [{ccn}] using cached {cache_path.relative_to(ROOT)}')
        return json.loads(cache_path.read_text())

    if verbose: print(f'  [{ccn}] {facility_name!r} ({state}) — 3 RAG queries')
    incidents: list[dict] = []
    queries_log: list[dict] = []
    seen_urls: set[str] = set()
    for tmpl in QUERY_TEMPLATES:
        q = tmpl.format(name=facility_name)
        try:
            items = run_rag(client, q)
        except Exception as e:
            if verbose: print(f'    ! query {q!r} failed: {e}')
            items = []
        passes = 0; fails = 0
        for it in items:
            url = (it.get('searchResult') or {}).get('url') or ''
            if url and url in seen_urls: continue
            if url: seen_urls.add(url)
            cls = classify_result(it, facility_name, state)
            iso_date, year = extract_date(it)
            ev = {
                'title': ((it.get('searchResult') or {}).get('title') or '')[:200],
                'url': url, 'snippet': ((it.get('searchResult') or {}).get('description') or '')[:300],
                'date': iso_date, 'year': year,
                'verdict': cls['verdict'], 'confidence': cls['confidence'], 'reason': cls['reason'],
                'query': q,
            }
            incidents.append(ev)
            if ev['verdict'] == 'pass': passes += 1
            elif ev['verdict'] == 'fail': fails += 1
        queries_log.append({'query': q, 'returned': len(items), 'passes': passes, 'fails': fails})
        if verbose:
            print(f'    [{q[:60]:<60}] returned={len(items)} pass={passes} fail={fails}')

    # Pick primary incident: prefer dated PASS, then most recent date, then high confidence.
    # Undated PASS sort below any dated PASS (was bug — undated 2025 lost to dated 2016).
    passes = [i for i in incidents if i['verdict'] == 'pass']
    passes.sort(key=lambda i: (
        1 if i.get('date') else 0,                      # dated wins over undated
        i.get('date') or '',                            # then most recent
        1 if i.get('confidence') == 'high' else 0,     # tiebreak by confidence
    ), reverse=True)
    primary = passes[0] if passes else None

    # Date-recency count — incidents PASS within last 24 months
    today = date.today()
    pass_24mo = 0
    for i in passes:
        d_str = i.get('date') or ''
        try:
            d_obj = date.fromisoformat(d_str if len(d_str) == 10 else d_str + '-01-01')
            if (today - d_obj).days <= 730:
                pass_24mo += 1
        except ValueError:
            pass

    record = {
        'ccn': ccn, 'facility_name': facility_name, 'state': state,
        'queries': queries_log,
        'incidents': incidents,
        'primary_incident': primary,
        'passes_incident_gate': primary is not None,
        'passes_24mo_count': pass_24mo,
        'max_confidence': primary['confidence'] if primary else 'none',
        'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2))
    if verbose:
        if primary:
            print(f'    → PASS · {primary["date"] or "no-date"} · {primary["title"][:70]}')
        else:
            print(f'    → FAIL (no on-site violent incident verified)')
    return record


# ============================================================================
# Mart merge
# ============================================================================

INCIDENT_COLS = [
    'incident_detection_attempted',
    'incident_passes_gate',          # HARD GATE — bool
    'incident_max_confidence',       # high | medium | none
    'incident_primary_type',         # shooting | stabbing | rampage | homicide | attack | assault | unknown
    'incident_primary_date',         # iso date
    'incident_primary_url',
    'incident_primary_title',
    'incident_pass_count_24mo',
]


_TYPE_MATCH = (
    ('shooting', re.compile(r'\bshooting|shot\b', re.I)),
    ('stabbing', re.compile(r'\bstabbing|stabbed\b', re.I)),
    ('homicide', re.compile(r'\bhomicide|murder(ed)?|killed\b', re.I)),
    ('rampage',  re.compile(r'\brampage|destroyed|trashed\b', re.I)),
    ('assault',  re.compile(r'\bassault(ed)?|attack(ed)?|beat(ing)?\b', re.I)),
)


def _classify_type(text: str) -> str:
    for label, pat in _TYPE_MATCH:
        if pat.search(text or ''):
            return label
    return 'unknown'


def merge_into_mart() -> int:
    if not SCORED_MART.exists():
        print(f'  ! {SCORED_MART} not found'); return 1
    if not CACHE_DIR.exists():
        print(f'  ! cache empty'); return 1
    cached = {}
    for f in CACHE_DIR.glob('*.json'):
        try: d = json.loads(f.read_text()); cached[d['ccn']] = d
        except (KeyError, json.JSONDecodeError): continue
    with SCORED_MART.open(newline='') as fh:
        rows = list(csv.DictReader(fh))
    fields = list(rows[0].keys()) if rows else []
    for c in INCIDENT_COLS:
        if c not in fields: fields.append(c)
    populated = 0
    for r in rows:
        d = cached.get(r['ccn'])
        if not d:
            for c in INCIDENT_COLS: r.setdefault(c, '')
            continue
        populated += 1
        primary = d.get('primary_incident') or {}
        r['incident_detection_attempted'] = 'True'
        r['incident_passes_gate'] = 'True' if d.get('passes_incident_gate') else 'False'
        r['incident_max_confidence'] = d.get('max_confidence', '')
        r['incident_primary_type'] = _classify_type((primary.get('title','') + ' ' + primary.get('snippet','')))
        r['incident_primary_date'] = primary.get('date', '') or ''
        r['incident_primary_url'] = primary.get('url', '') or ''
        r['incident_primary_title'] = (primary.get('title','') or '')[:200]
        r['incident_pass_count_24mo'] = d.get('passes_24mo_count', 0)
    with SCORED_MART.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f'  → merged {populated} cached records into {SCORED_MART.relative_to(ROOT)}')
    return 0


# ============================================================================
# Anchor-state backfill — search NY (or another state) for incidents,
# then match to TAM hospitals
# ============================================================================

def state_anchor_search(client, state: str, *, force: bool = False,
                       verbose: bool = True) -> list[dict]:
    """Run state-wide incident queries, scan results for hospital-name matches
    in our TAM. Returns list of {ccn, facility_name, incident, evidence_url}."""
    # Load hospital index for the state
    hospitals = []
    with SCORED_MART.open(newline='') as fh:
        for r in csv.DictReader(fh):
            if r.get('state', '').upper() != state.upper():
                continue
            nm = (r.get('facility_name') or '').strip()
            if not nm or len(nm) < 18:
                continue
            hospitals.append({
                'ccn': r['ccn'], 'name': nm,
                'forge_tier': r.get('forge_tier',''),
                'forge_total': r.get('forge_total',''),
                'beds': r.get('beds',''),
                'standalone_score': r.get('standalone_score',''),
                'parent_system': r.get('parent_system',''),
                'system_hospital_count': r.get('system_hospital_count',''),
                'osha_severe_injury_count_24mo': r.get('osha_severe_injury_count_24mo',''),
            })
    if verbose: print(f'  state-anchor: {len(hospitals)} hospitals in {state} index')

    # State-wide queries (broad — Google ranks the most-cited incidents first)
    state_queries = [
        f'"{state}" hospital shooting OR stabbing inside emergency room',
        f'"{state}" "workplace violence" hospital nurse OR staff attacked',
        f'"{state}" hospital active shooter incident',
    ]
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    findings: list[dict] = []
    for q in state_queries:
        slug = _slug(q)[:50]
        cache_path = RAG_DIR / f'{state}_{slug}.json'
        if cache_path.exists() and not force:
            items = json.loads(cache_path.read_text())
        else:
            try:
                items = run_rag(client, q, max_results=10)
            except Exception as e:
                if verbose: print(f'    ! query {q!r}: {e}')
                items = []
            cache_path.write_text(json.dumps(items, indent=2))
        if verbose: print(f'    [{q[:60]:<60}] returned={len(items)}')
        for it in items:
            text = (
                ((it.get('searchResult') or {}).get('title') or '') + '\n' +
                ((it.get('searchResult') or {}).get('description') or '') + '\n' +
                (it.get('markdown') or it.get('text') or '')[:5000]
            )
            text_lo = text.lower()
            for h in hospitals:
                if h['name'].lower() not in text_lo:
                    continue
                cls = classify_result(it, h['name'], state)
                if cls['verdict'] != 'pass':
                    continue
                iso_date, year = extract_date(it)
                findings.append({**h,
                    'evidence_url': (it.get('searchResult') or {}).get('url',''),
                    'evidence_title': ((it.get('searchResult') or {}).get('title') or '')[:200],
                    'snippet': ((it.get('searchResult') or {}).get('description') or '')[:300],
                    'incident_date': iso_date,
                    'incident_year': year,
                    'confidence': cls['confidence'],
                    'reason': cls['reason'],
                    'query': q,
                })
    return findings


# ============================================================================
# CLI
# ============================================================================

def _load_facility(ccn: str) -> Optional[dict]:
    if not SCORED_MART.exists(): return None
    with SCORED_MART.open(newline='') as fh:
        for r in csv.DictReader(fh):
            if r['ccn'] == ccn: return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--ccn', help='Enrich one facility')
    g.add_argument('--qsos', action='store_true', help='Back-test the 5 hand-picked QSOs')
    g.add_argument('--state', help='Anchor-state backfill — search incidents in state, match TAM')
    g.add_argument('--merge', action='store_true', help='Merge cached records into tam_scored.csv')
    ap.add_argument('--force', action='store_true', help='Ignore cache and re-fetch')
    args = ap.parse_args()

    if args.merge:
        return merge_into_mart()

    if not os.environ.get('APIFY_API_TOKEN'):
        print('  ! APIFY_API_TOKEN missing — source .env first'); return 1

    with httpx.Client(headers={'User-Agent': 'firefly-gtm/tier-b-incident'}) as client:
        if args.ccn:
            row = _load_facility(args.ccn)
            if not row: print(f'  ! CCN {args.ccn} not found'); return 1
            enrich_one(client, args.ccn, row.get('facility_name', ''), row.get('state', ''),
                       force=args.force)
            return 0

        if args.qsos:
            print(f'tier-b-incident: back-testing {len(QSO_CCNS)} hand-picked QSOs')
            for ccn, name in QSO_CCNS.items():
                row = _load_facility(ccn)
                state = row.get('state', '') if row else ''
                fn = (row.get('facility_name', '') if row else '') or name
                enrich_one(client, ccn, fn, state, force=args.force)
            return 0

        if args.state:
            print(f'tier-b-incident: anchor-state backfill — {args.state}')
            findings = state_anchor_search(client, args.state, force=args.force)
            # de-dup per CCN, keep most recent incident
            by_ccn: dict[str, dict] = {}
            for f in findings:
                ex = by_ccn.get(f['ccn'])
                if not ex or (f.get('incident_date') or '') > (ex.get('incident_date') or ''):
                    by_ccn[f['ccn']] = f
            print()
            print(f'  unique CCNs with PASS evidence: {len(by_ccn)}')
            for ccn, f in sorted(by_ccn.items(),
                                 key=lambda kv: (kv[1].get('incident_date') or ''), reverse=True):
                print(f'  {ccn} {f["name"][:46]:<46} tier {f["forge_tier"]} beds {f["beds"]} std {f["standalone_score"]} · {f.get("incident_date","")} {f["evidence_title"][:70]}')
            # Also write per-CCN cache so --merge picks them up
            for ccn, f in by_ccn.items():
                cache_path = CACHE_DIR / f'{ccn}.json'
                if cache_path.exists():
                    # Don't clobber a QSO --qsos cache if present
                    continue
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({
                    'ccn': ccn, 'facility_name': f['name'], 'state': args.state,
                    'queries': [], 'incidents': [{
                        'title': f['evidence_title'], 'url': f['evidence_url'],
                        'snippet': f['snippet'], 'date': f.get('incident_date'),
                        'year': f.get('incident_year'),
                        'verdict': 'pass', 'confidence': f['confidence'],
                        'reason': f['reason'], 'query': f.get('query',''),
                    }],
                    'primary_incident': {
                        'title': f['evidence_title'], 'url': f['evidence_url'],
                        'snippet': f['snippet'], 'date': f.get('incident_date'),
                        'confidence': f['confidence'],
                    },
                    'passes_incident_gate': True,
                    'passes_24mo_count': 1,
                    'max_confidence': f['confidence'],
                    'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                }, indent=2))
            return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
