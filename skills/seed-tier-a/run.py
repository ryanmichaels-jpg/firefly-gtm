#!/usr/bin/env python3
"""seed-tier-a: build data/mart/tam.csv for the 15 priority mandate states.

One file, eight ordered idempotent steps. Each step reads the prior staging
file and writes its own — so re-running a single step is safe and cheap.

Run:
    python3 skills/seed-tier-a/run.py --all
    python3 skills/seed-tier-a/run.py --step 1
    python3 skills/seed-tier-a/run.py --skip nppes,geocode
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import httpx

# ----------------------------------------------------------------------------
# paths + constants
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
STAGE = ROOT / 'data' / 'staging'
MART = ROOT / 'data' / 'mart'
REF = ROOT / 'data' / 'reference'

STATES = {'WA', 'CA', 'NY', 'NJ', 'LA', 'FL', 'IL', 'TX', 'AZ',
          'MA', 'NC', 'OR', 'CO', 'CT', 'MD'}

EXEC_TITLES = (
    'ceo', 'cfo', 'coo', 'cio', 'cto', 'cmo', 'cno', 'cso',
    'president', 'administrator', 'executive director', 'chief',
    'vp ', 'vice president', 'director of', 'general counsel',
)
TODAY = date.today()

# ----------------------------------------------------------------------------
# small csv helpers
# ----------------------------------------------------------------------------
def read_csv(path: Path, encoding: str = 'utf-8') -> list[dict]:
    with open(path, encoding=encoding, newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fieldnames = list({k: None for r in rows for k in r}.keys())
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def banner(n: int, label: str):
    bar = '=' * 70
    print(f'\n{bar}\nSTEP {n} · {label}\n{bar}')

def assert_unique(rows, key, label):
    seen, dupes = set(), []
    for r in rows:
        v = r.get(key)
        if v in seen: dupes.append(v)
        else: seen.add(v)
    if dupes:
        print(f'  ! {len(dupes)} duplicate {key} values, first 5: {dupes[:5]}')
    else:
        print(f'  ✓ {label}: {key} is unique across {len(rows)} rows')

# ============================================================================
# STEP 1 — filter CMS HGI to 15 priority states
# ============================================================================
def step_1_cms_hgi() -> Path:
    banner(1, 'CMS Hospital General Information → 15 states')
    src = RAW / 'cms-hgi' / 'Hospital_General_Information_2026-05-13.csv'
    out_rows = []
    for row in read_csv(src):
        if row['State'] not in STATES:
            continue
        out_rows.append({
            'ccn': row['Facility ID'].strip(),
            'legal_name': row['Facility Name'].strip(),
            'facility_name': row['Facility Name'].strip(),  # DBA fallback in step 5
            'address': row['Address'].strip(),
            'city': row['City/Town'].strip().title(),
            'state': row['State'],
            'zip': (row['ZIP Code'] or '')[:5],
            'hospital_type': row['Hospital Type'],
            'ownership': row['Hospital Ownership'],
            'has_ED': (row.get('Emergency Services', '').strip().lower() == 'yes'),
            'phone': row.get('Telephone Number', '').strip(),
            'cms_hgi_source_url':
                'https://data.cms.gov/provider-data/dataset/xubh-q36u',
        })
    by_state: dict[str, int] = {}
    for r in out_rows:
        by_state[r['state']] = by_state.get(r['state'], 0) + 1
    out = STAGE / '01_cms_hgi.csv'
    write_csv(out, out_rows)
    print(f'  → {out.relative_to(ROOT)} · {len(out_rows)} rows')
    for s in sorted(by_state, key=lambda x: -by_state[x]):
        print(f'    {s}: {by_state[s]}')
    assert_unique(out_rows, 'ccn', 'CMS HGI')
    return out


# ============================================================================
# STEP 2 — dedup on CCN + (name, address)
# ============================================================================
def step_2_dedup() -> Path:
    banner(2, 'Dedup on CCN + name+address')
    rows = read_csv(STAGE / '01_cms_hgi.csv')
    seen_ccn: dict[str, dict] = {}
    seen_nameaddr: dict[tuple[str, str], dict] = {}
    out_rows, ccn_dupes, nameaddr_dupes = [], 0, 0
    for r in rows:
        ccn = r['ccn']
        key_na = (r['legal_name'].lower(), (r['address'] or '').lower())
        if ccn in seen_ccn:
            ccn_dupes += 1
            continue
        if key_na in seen_nameaddr and (r['address'] or '').strip():
            nameaddr_dupes += 1
            continue
        seen_ccn[ccn] = r
        seen_nameaddr[key_na] = r
        out_rows.append(r)
    out = STAGE / '02_dedup.csv'
    write_csv(out, out_rows)
    print(f'  → {out.relative_to(ROOT)} · {len(out_rows)} rows '
          f'(dropped {ccn_dupes} ccn dupes, {nameaddr_dupes} name+addr dupes)')
    return out


# ============================================================================
# STEP 3 — AHRQ Compendium left join (parent_system, facilities_in_system)
# ============================================================================
def step_3_ahrq() -> Path:
    banner(3, 'Join AHRQ Compendium (parent_system, facilities_in_system)')
    rows = read_csv(STAGE / '02_dedup.csv')
    linkage = read_csv(
        RAW / 'ahrq-compendium' / 'chsp-hospital-linkage-2023.csv',
        encoding='cp1252',
    )
    by_ccn = {l['ccn']: l for l in linkage if l.get('ccn')}
    # build facilities_in_system count
    sys_count: dict[str, int] = {}
    for l in linkage:
        sid = l.get('health_sys_id') or ''
        if sid:
            sys_count[sid] = sys_count.get(sid, 0) + 1
    matched = 0
    for r in rows:
        l = by_ccn.get(r['ccn'])
        if l:
            matched += 1
            r['parent_system'] = l.get('health_sys_name', '').strip() or None
            r['parent_system_id'] = l.get('health_sys_id', '').strip() or None
            r['facilities_in_system'] = sys_count.get(l.get('health_sys_id'))
            r['corp_parent'] = l.get('corp_parent_name', '').strip() or None
            r['ahrq_source_url'] = (
                'https://www.ahrq.gov/sites/default/files/wysiwyg/chsp/'
                'compendium/chsp-hospital-linkage-2023.csv')
        else:
            r['parent_system'] = None
            r['parent_system_id'] = None
            r['facilities_in_system'] = None
            r['corp_parent'] = None
            r['ahrq_source_url'] = None
    out = STAGE / '03_ahrq.csv'
    write_csv(out, rows)
    pct = 100.0 * matched / max(len(rows), 1)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows · '
          f'AHRQ match: {matched}/{len(rows)} ({pct:.1f}%)')
    return out


# ============================================================================
# STEP 4 — CMS POS left join (certified beds, has_behavioral_unit)
# ============================================================================
def step_4_pos() -> Path:
    banner(4, 'Join CMS POS (certified beds, has_behavioral_unit)')
    rows = read_csv(STAGE / '03_ahrq.csv')
    pos_path = RAW / 'cms-pos' / 'Hospital_and_other.DATA.Q1_2026.csv'
    # only hospital-category rows; lookup by PRVDR_NUM
    by_ccn: dict[str, dict] = {}
    with open(pos_path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            # PRVDR_CTGRY_CD=01 is hospitals; some records lack it, keep all and match by PRVDR_NUM
            num = (r.get('PRVDR_NUM') or '').strip()
            if num:
                by_ccn[num] = r
    matched = 0
    for r in rows:
        p = by_ccn.get(r['ccn'])
        if p:
            matched += 1
            crtfd = (p.get('CRTFD_BED_CNT') or '').strip()
            psych = (p.get('PSYCH_UNIT_BED_CNT') or '').strip()
            r['beds'] = int(crtfd) if crtfd.isdigit() else None
            psych_n = int(psych) if psych.isdigit() else 0
            r['has_behavioral_unit'] = psych_n > 0
            r['pos_source_url'] = (
                'https://data.cms.gov/provider-characteristics/'
                'hospitals-and-other-facilities/'
                'provider-of-services-file-hospital-non-hospital-facilities')
        else:
            r['beds'] = None
            r['has_behavioral_unit'] = None
            r['pos_source_url'] = None
    out = STAGE / '04_pos.csv'
    write_csv(out, rows)
    pct = 100.0 * matched / max(len(rows), 1)
    bedded = sum(1 for r in rows if r.get('beds'))
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows · '
          f'POS match: {matched}/{len(rows)} ({pct:.1f}%) · {bedded} with beds')
    return out


# ============================================================================
# STEP 5 — NPPES enrichment (DBA, physical addr, edm_seed)
# ============================================================================
NPPES_URL = 'https://npiregistry.cms.hhs.gov/api/'

def _exec_title_score(title: str) -> int:
    t = (title or '').lower()
    for kw in EXEC_TITLES:
        if kw in t:
            return 2
    return 1 if t else 0

def _addr_match_score(hgi_addr: str, hgi_zip: str, nppes_addrs: list[dict]) -> int:
    """0=no match, 1=zip-only match, 2=street+zip prefix match."""
    hgi_norm = re.sub(r'[^A-Z0-9 ]', '', (hgi_addr or '').upper())[:12]
    for a in nppes_addrs:
        if a.get('address_purpose') != 'LOCATION':
            continue
        nppes_norm = re.sub(r'[^A-Z0-9 ]', '', (a.get('address_1') or '').upper())[:12]
        nppes_zip = (a.get('postal_code') or '')[:5]
        if hgi_norm and nppes_norm and hgi_norm == nppes_norm:
            return 2
        if hgi_zip and nppes_zip and hgi_zip == nppes_zip:
            return 1
    return 0

def _pick_nppes(facility_name: str, hgi_addr: str, hgi_zip: str, results: list[dict]) -> tuple[dict | None, str, int]:
    """Pick best NPPES result. Returns (result, match_method, confidence 0-3)."""
    candidates = []
    for r in results:
        if r.get('enumeration_type') != 'NPI-2':
            continue
        basic = r.get('basic', {}) or {}
        if (basic.get('status') or '').upper() != 'A':
            continue
        candidates.append(r)
    if not candidates:
        return None, 'no-active-org', 0
    scored = []
    for r in candidates:
        basic = r.get('basic', {}) or {}
        addr_score = _addr_match_score(hgi_addr, hgi_zip, r.get('addresses', []))
        title = basic.get('authorized_official_title_or_position') or ''
        title_score = _exec_title_score(title)
        scored.append((addr_score, title_score, r))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    best = scored[0]
    confidence = best[0] + best[1]  # 0..4
    method = f'addr={best[0]} title={best[1]}'
    return best[2], method, confidence

def _nppes_fetch(client: httpx.Client, facility_name: str, state: str) -> list[dict]:
    """Query NPPES by org name + state. Returns results list."""
    params = {
        'version': '2.1',
        'organization_name': facility_name,
        'state': state,
        'enumeration_type': 'NPI-2',
        'limit': 50,
    }
    for attempt in range(4):
        try:
            r = client.get(NPPES_URL, params=params, timeout=20.0)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json().get('results', [])
        except (httpx.HTTPError, json.JSONDecodeError):
            time.sleep(1 + attempt)
    return []

def _strip_common_suffix(name: str) -> str:
    # NPPES indexes hospital names with various forms; try a less-specific
    # query if the first fails (e.g. "Harborview Medical Center" → "Harborview")
    n = re.sub(r'(?i)\b(medical center|hospital|health|inc|llc)\b.*', '', name).strip()
    return n or name

# Known hospital-system prefixes seen in CMS HGI that NPPES drops.
SYSTEM_PREFIXES = (
    'HONORHEALTH', 'HONOR HEALTH', 'BANNER -', 'BANNER-', 'BANNER',
    'DIGNITY HEALTH -', 'DIGNITY HEALTH', 'ABRAZO', 'CHI ', 'COMMONSPIRIT',
    'KAISER PERMANENTE', 'KAISER FOUNDATION', 'KAISER',
    'PROVIDENCE', 'ASCENSION', 'TENET', 'HCA', 'AHMC',
    'BAYLOR SCOTT & WHITE', 'BAYLOR', 'METHODIST',
    'NORTHWELL', 'MOUNT SINAI', 'NYU LANGONE', 'NYC HEALTH + HOSPITALS',
    'INTERMOUNTAIN', 'UCLA', 'UCSF', 'UCI', 'UCSD', 'UC DAVIS',
    'MULTICARE', 'OVERLAKE', 'UW MEDICINE', 'SWEDISH',
)

def _name_variants(name: str) -> list[str]:
    """Yield query variants for fuzzy retry. Order: most specific → least."""
    base = (name or '').upper()
    out, seen = [], set()
    def push(s):
        s = re.sub(r'\s+', ' ', s).strip()
        if s and s not in seen:
            seen.add(s); out.append(s)
    push(base)
    # strip apostrophes / punctuation
    norm = re.sub(r"[.'`’]", '', base)
    push(norm)
    # expand abbreviations
    expanded = (norm
        .replace(' MED CTR', ' MEDICAL CENTER')
        .replace(' MED CTR.', ' MEDICAL CENTER')
        .replace(' HOSP ', ' HOSPITAL ').rstrip()
    )
    if expanded.endswith(' HOSP'):
        expanded = expanded[:-5] + ' HOSPITAL'
    push(expanded)
    # strip leading system prefix
    for p in SYSTEM_PREFIXES:
        if base.startswith(p):
            stripped = base[len(p):].lstrip(' -').strip()
            push(stripped)
            push(re.sub(r"[.'`’]", '', stripped))
            break
    # last-ditch: first 3 tokens
    toks = norm.split()
    if len(toks) >= 3:
        push(' '.join(toks[:3]))
    return out

def step_5_nppes() -> Path:
    banner(5, 'NPPES enrichment (DBA, physical addr, edm_seed)')
    rows = read_csv(STAGE / '04_pos.csv')
    cache_dir = RAW / 'nppes' / 'by-ccn'
    cache_dir.mkdir(parents=True, exist_ok=True)
    matched = ambiguous = unmatched = 0
    t0 = time.time()
    with httpx.Client(headers={'User-Agent': 'firefly-gtm/seed-tier-a'}) as client:
        for i, r in enumerate(rows):
            cache_path = cache_dir / f'{r["ccn"]}.json'
            if cache_path.exists():
                payload = json.loads(cache_path.read_text())
            else:
                payload = None
            # retry pass: if cached but empty results, walk name variants
            if payload is None or not payload.get('results'):
                tried = []
                results: list[dict] = []
                for variant in _name_variants(r['facility_name']):
                    tried.append(variant)
                    results = _nppes_fetch(client, variant, r['state'])
                    if results:
                        break
                    time.sleep(0.15)
                payload = {
                    'query': {'name': r['facility_name'], 'state': r['state'],
                              'tried_variants': tried},
                    'fetched_at': datetime.utcnow().isoformat() + 'Z',
                    'results': results,
                }
                cache_path.write_text(json.dumps(payload))
                time.sleep(0.20)  # courtesy rate-limit
            chosen, method, confidence = _pick_nppes(
                r['facility_name'], r['address'], r['zip'],
                payload.get('results', []))
            if chosen is None:
                unmatched += 1
                r['nppes_match_confidence'] = 0
                r['needs_review'] = True
                continue
            basic = chosen.get('basic', {}) or {}
            other = chosen.get('other_names') or []
            # DBA preference: only swap when legal_name is generic AND DBA
            # adds hospital identity. NPPES DBAs include sibling operations
            # under the same NPI (PHARMACY, TRANSPORT, IMAGING) and trailing
            # modifiers — those would misname the facility.
            HOSP_KW = ('HOSPITAL', 'MEDICAL CENTER', 'HEALTH CENTER',
                       'MEDICAL CTR')
            NON_FACILITY_MODIFIERS = (
                'PHARMACY', 'LABORATORY', 'LAB ', 'TRANSPORT',
                'IMAGING', 'SURGERY CENTER', 'OUTPATIENT',
                'INFUSION', 'DIALYSIS', 'AMBULANCE',
            )
            legal_has_hosp = any(kw in r['legal_name'].upper() for kw in HOSP_KW)
            dba = None
            if not legal_has_hosp:
                for o in other:
                    if o.get('type') not in ('Doing Business As', 'Former Name'):
                        continue
                    cand = (o.get('organization_name') or '').strip()
                    if not cand: continue
                    cu = cand.upper()
                    if any(kw in cu for kw in HOSP_KW) and not any(
                        m in cu for m in NON_FACILITY_MODIFIERS):
                        dba = cand
                        break
            location = next((a for a in chosen.get('addresses', [])
                             if a.get('address_purpose') == 'LOCATION'), None)
            if dba:
                r['facility_name'] = dba
            r['npi'] = chosen.get('number')
            r['edm_seed_name'] = (
                f"{basic.get('authorized_official_first_name', '').strip()} "
                f"{basic.get('authorized_official_last_name', '').strip()}").strip() or None
            r['edm_seed_title'] = basic.get('authorized_official_title_or_position') or None
            r['edm_seed_phone'] = basic.get('authorized_official_telephone_number') or None
            if location:
                r['address'] = location.get('address_1') or r['address']
                r['city'] = (location.get('city') or r['city']).title()
                r['zip'] = (location.get('postal_code') or r['zip'])[:5]
            r['nppes_match_confidence'] = confidence  # 0..4
            r['nppes_match_method'] = method
            r['nppes_source_url'] = f'https://npiregistry.cms.hhs.gov/api/?number={chosen.get("number")}'
            if confidence < 2:
                r['needs_review'] = True
                ambiguous += 1
            else:
                matched += 1
            if (i + 1) % 200 == 0:
                elapsed = time.time() - t0
                print(f'    {i+1}/{len(rows)} · elapsed {elapsed:.0f}s · '
                      f'matched={matched} ambiguous={ambiguous} unmatched={unmatched}')
    out = STAGE / '05_nppes.csv'
    write_csv(out, rows)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows · '
          f'matched={matched}, ambiguous={ambiguous}, unmatched={unmatched}')
    return out


# ============================================================================
# STEP 6 — Census batch geocoder (lat, lng)
# ============================================================================
CENSUS_URL = 'https://geocoding.geo.census.gov/geocoder/locations/addressbatch'
BATCH_SIZE = 1000  # well under 10k cap

def _clean_addr(a: str) -> str:
    a = re.sub(r'(?i)\b(p\.?o\.?\s*box|po\s*box|box|mail(\s*code|\s*stop)?)\s*[a-z0-9-]+\b', '', a or '')
    a = re.sub(r'\s+', ' ', a).strip().strip(',')
    return a

def step_6_geocode() -> Path:
    banner(6, 'Census batch geocoder (lat, lng)')
    rows = read_csv(STAGE / '05_nppes.csv')
    matches: dict[str, tuple[float, float, str]] = {}
    cache_dir = RAW / 'census-geocode'
    cache_dir.mkdir(parents=True, exist_ok=True)
    pending = [(r['ccn'], _clean_addr(r['address']), r['city'], r['state'], r['zip'])
               for r in rows if r.get('address')]
    batches = [pending[i:i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    print(f'  geocoding {len(pending)} addresses in {len(batches)} batches '
          f'of {BATCH_SIZE}')
    with httpx.Client(timeout=120.0) as client:
        for bi, batch in enumerate(batches, 1):
            payload_lines = [f'{cid},"{a}","{c}","{s}","{z}"'
                             for cid, a, c, s, z in batch]
            payload = '\n'.join(payload_lines).encode('utf-8')
            files = {'addressFile': ('input.csv', payload, 'text/csv')}
            data = {'benchmark': 'Public_AR_Current'}
            for attempt in range(4):
                try:
                    r = client.post(CENSUS_URL, files=files, data=data)
                    r.raise_for_status()
                    break
                except httpx.HTTPError as e:
                    print(f'    batch {bi} attempt {attempt+1} failed: {e}')
                    time.sleep(2 ** attempt)
            else:
                print(f'    batch {bi} gave up after retries')
                continue
            for line in r.text.splitlines():
                parts = next(csv.reader([line]))
                if len(parts) < 6:
                    continue
                ccn, _input, match_status = parts[0], parts[1], parts[2]
                if match_status == 'Match' and len(parts) >= 6:
                    coords = parts[5].split(',')
                    if len(coords) == 2:
                        try:
                            lng, lat = float(coords[0]), float(coords[1])
                            matches[ccn] = (lat, lng, 'census')
                        except ValueError:
                            pass
            (cache_dir / f'batch_{bi:03d}_out.csv').write_text(r.text)
            print(f'    batch {bi}/{len(batches)} · {len(matches)} matches so far')
    for r in rows:
        if r['ccn'] in matches:
            lat, lng, src = matches[r['ccn']]
            r['lat'] = lat
            r['lng'] = lng
            r['geocode_source'] = src
        else:
            r['lat'] = None
            r['lng'] = None
            r['geocode_source'] = None
            r['needs_review'] = True
    out = STAGE / '06_geocode.csv'
    write_csv(out, rows)
    matched_pct = 100.0 * len(matches) / max(len(rows), 1)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows · '
          f'geocoded {len(matches)}/{len(rows)} ({matched_pct:.1f}%)')
    return out


# ============================================================================
# STEP 7 — mandate-join + status logic
# ============================================================================
DATE_RE = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')
YEAR_RE = re.compile(r'\b(20\d{2})\b')
DEAD_STATUSES = {'Dead', 'Vetoed', 'Pending/Failed', 'None-found',
                 'Pending/Dead/Vetoed'}

def _parse_mandate_dates(text: str) -> list[date]:
    out: list[date] = []
    for m, d, y in DATE_RE.findall(text or ''):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    if not out:
        for y in YEAR_RE.findall(text or ''):
            try:
                out.append(date(int(y), 1, 1))
            except ValueError:
                pass
    return out

def _mandate_status(row: dict) -> tuple[str | None, date | None]:
    status = (row.get('Status') or '').strip()
    if any(d in status for d in DEAD_STATUSES):
        return None, None
    dates = _parse_mandate_dates(row.get('Effective / Deadline') or '')
    latest = max(dates) if dates else None
    text = (row.get('Effective / Deadline') or '').lower()
    if latest:
        return ('In force' if latest <= TODAY else 'Upcoming'), latest
    if 'in force' in text or 'fy26 active' in text:
        return 'In force', None
    if 'pending' in (status.lower() or ''):
        return 'Upcoming', None
    return None, None

def _state_codes(jurisdiction: str) -> tuple[list[str], str]:
    """Return (state_codes, scope) where scope ∈ {'state','federal','other'}."""
    j = (jurisdiction or '').upper()
    state_map = {
        'WASHINGTON': 'WA', 'CALIFORNIA': 'CA', 'NEW YORK': 'NY',
        'NEW JERSEY': 'NJ', 'LOUISIANA': 'LA', 'FLORIDA': 'FL',
        'ILLINOIS': 'IL', 'TEXAS': 'TX', 'ARIZONA': 'AZ',
        'MASSACHUSETTS': 'MA', 'NORTH CAROLINA': 'NC', 'OREGON': 'OR',
        'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'MARYLAND': 'MD',
    }
    if 'US — ' in j or j.startswith('US—') or 'FEDERAL' in j:
        return list(STATES), 'federal'
    for name, code in state_map.items():
        if name in j:
            return [code], 'state'
    return [], 'other'

def step_7_mandates() -> Path:
    banner(7, 'Mandate-join with status logic')
    rows = read_csv(STAGE / '06_geocode.csv')
    mandates = read_csv(REF / 'mandates.csv')
    dropped_path = STAGE / 'mandate_dropped.csv'
    dropped: list[dict] = []
    by_state: dict[str, list[dict]] = {s: [] for s in STATES}
    for m in mandates:
        # focus on healthcare-relevant mandates
        if (m.get('Vertical') or '').strip().lower() not in (
            'healthcare', 'cross-vertical', 'federal'):
            continue
        status, latest = _mandate_status(m)
        if status is None:
            dropped.append(m)
            continue
        codes, scope = _state_codes(m.get('Jurisdiction', ''))
        for code in codes:
            if code not in by_state:
                continue
            by_state[code].append({
                'mandate_name': m.get('Law / Bill', '').strip(),
                'mandate_type': m.get('Type', '').strip(),
                'mandate_status': status,
                'effective_date': latest.isoformat() if latest else None,
                '_date_obj': latest,
                'mandate_scope': scope,
                'mandate_source_url': m.get('Source', '').strip(),
                'mandate_requirement': m.get('Requirement (short)', '').strip(),
            })
    # rank per state: state-specific In-force (latest date) > state-specific Upcoming
    #  > federal In-force > federal Upcoming. Latest effective date wins within tier.
    def rank_key(m):
        status_p = 0 if m['mandate_status'] == 'In force' else 1
        scope_p = 0 if m.get('mandate_scope') == 'state' else 1
        date_key = -m['_date_obj'].toordinal() if m.get('_date_obj') else 0
        return (scope_p, status_p, date_key)
    for code, lst in by_state.items():
        lst.sort(key=rank_key)
        for m in lst:
            m.pop('_date_obj', None)  # don't leak to CSV
    for r in rows:
        cand = by_state.get(r['state'], [])
        if not cand:
            r['mandate_name'] = None
            r['mandate_type'] = None
            r['mandate_status'] = None
            r['mandate_scope'] = None
            r['effective_date'] = None
            r['mandate_source_url'] = None
            r['needs_review'] = True
        else:
            top = cand[0]
            r['mandate_name'] = top['mandate_name']
            r['mandate_type'] = top['mandate_type']
            r['mandate_status'] = top['mandate_status']
            r['mandate_scope'] = top['mandate_scope']
            r['effective_date'] = top['effective_date']
            r['mandate_source_url'] = top['mandate_source_url']
            # federal-only fallback is a weak signal — flag for review
            if top['mandate_scope'] != 'state':
                r['needs_review'] = True
    write_csv(dropped_path, dropped)
    out = STAGE / '07_mandate.csv'
    write_csv(out, rows)
    state_counts = {s: len(v) for s, v in by_state.items() if v}
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows · '
          f'dropped {len(dropped)} non-actionable mandates → {dropped_path.relative_to(ROOT)}')
    print('  primary mandate per state:')
    for s in sorted(STATES):
        top = by_state[s][0] if by_state[s] else None
        if top:
            print(f"    {s}: {top['mandate_name']} ({top['mandate_status']})")
        else:
            print(f"    {s}: ! no actionable mandate found")
    return out


# ============================================================================
# STEP 8 — tier classification + write data/mart/tam.csv
# ============================================================================
def _tier(row: dict) -> int:
    beds = row.get('beds')
    htype = (row.get('hospital_type') or '').lower()
    has_ed = row.get('has_ED') in (True, 'True', 'true', 1, '1')
    try:
        beds_n = int(beds) if beds not in (None, '', 'None') else None
    except (TypeError, ValueError):
        beds_n = None
    if 'critical access' in htype:
        return 3
    if beds_n is None:
        return 3
    if beds_n < 100:
        return 2
    return 1 if has_ed else 2

def step_8_tier_and_mart() -> Path:
    banner(8, 'Tier classification + final mart')
    rows = read_csv(STAGE / '07_mandate.csv')
    tier_counts = {1: 0, 2: 0, 3: 0}
    for r in rows:
        t = _tier(r)
        r['facility_tier'] = t
        tier_counts[t] += 1
        # confidence + needs_review consolidation
        c = []
        try:
            c.append(int(r.get('nppes_match_confidence') or 0))
        except (TypeError, ValueError):
            pass
        if r.get('lat') and r.get('lng'):
            c.append(2)
        else:
            c.append(0)
        r['confidence'] = round(sum(c) / max(len(c), 1), 2) if c else None
        r['enrichment_tier'] = 'A'
        r['last_enriched_at'] = datetime.utcnow().isoformat() + 'Z'
        if not r.get('needs_review'):
            r['needs_review'] = False
    out = MART / 'tam.csv'
    out.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out, rows)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows')
    print(f'    tier 1: {tier_counts[1]}')
    print(f'    tier 2: {tier_counts[2]}')
    print(f'    tier 3: {tier_counts[3]}')
    return out


# ============================================================================
# acceptance checks
# ============================================================================
def acceptance_check() -> int:
    banner(0, 'ACCEPTANCE CHECK · data/mart/tam.csv')
    out = MART / 'tam.csv'
    if not out.exists():
        print('  ! mart not written yet')
        return 1
    rows = read_csv(out)
    n = len(rows)
    print(f'  rows: {n}')
    ok = True
    if not (1500 <= n <= 4000):
        print(f'  ! row count {n} outside expected 1500..4000'); ok = False
    seen, dupes = set(), 0
    for r in rows:
        if r['ccn'] in seen: dupes += 1
        seen.add(r['ccn'])
    if dupes:
        print(f'  ! {dupes} duplicate CCNs'); ok = False
    else:
        print(f'  ✓ CCN unique')
    required = ['facility_name', 'state', 'mandate_status', 'lat', 'lng']
    for col in required:
        nulls = sum(1 for r in rows if not r.get(col))
        pct = 100 * nulls / n
        flag = '✓' if nulls == 0 else ('!' if pct > 5 else '~')
        print(f'  {flag} null in {col}: {nulls} ({pct:.1f}%)')
        if col in ('facility_name', 'state') and nulls > 0:
            ok = False
    nr = sum(1 for r in rows if r.get('needs_review') in (True, 'True', 'true'))
    print(f'  needs_review=True: {nr} ({100 * nr / n:.1f}%)')
    print('\n  by state:')
    by_state: dict[str, int] = {}
    for r in rows:
        by_state[r['state']] = by_state.get(r['state'], 0) + 1
    for s in sorted(by_state, key=lambda x: -by_state[x]):
        print(f'    {s}: {by_state[s]}')
    print(f'\n  acceptance: {"PASS" if ok else "FAIL"}')
    return 0 if ok else 1


# ============================================================================
# CLI
# ============================================================================
STEPS = {
    1: ('cms_hgi',  step_1_cms_hgi),
    2: ('dedup',    step_2_dedup),
    3: ('ahrq',     step_3_ahrq),
    4: ('pos',      step_4_pos),
    5: ('nppes',    step_5_nppes),
    6: ('geocode',  step_6_geocode),
    7: ('mandates', step_7_mandates),
    8: ('tier',     step_8_tier_and_mart),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true', help='run all steps')
    ap.add_argument('--step', type=int, help='run a single step (1..8)')
    ap.add_argument('--skip', type=str, default='',
                    help='comma-separated step names to skip (e.g. nppes,geocode)')
    ap.add_argument('--check', action='store_true',
                    help='run only acceptance check on existing mart')
    args = ap.parse_args()
    if args.check:
        sys.exit(acceptance_check())
    skip = set(args.skip.split(',')) if args.skip else set()
    if args.step:
        STEPS[args.step][1]()
        return
    if not args.all:
        ap.print_help(); return
    for i in sorted(STEPS):
        name, fn = STEPS[i]
        if name in skip:
            print(f'\n[skip] step {i} · {name}')
            continue
        fn()
    acceptance_check()

if __name__ == '__main__':
    main()
