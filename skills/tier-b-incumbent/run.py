#!/usr/bin/env python3
"""tier-b-incumbent: detect incumbent security/safety vendors at hospitals.

Apify's framing of the problem (Gap 3): incumbent vendor + contract vintage
lives in tactical text — Indeed job postings explicitly name systems
("manages AtHoc deployment", "Familiarity with Genetec required"). USAspending
+ SAM.gov are blind to commercial security vendor relationships at private
hospitals; this fills that gap.

Strategy
  1. For each facility, spawn ~3 targeted Apify Indeed searches per the
     QUERY_TEMPLATES (systems / program / healthcare-tech axes)
  2. Regex-match each job description body against the VENDOR_DICTIONARY
  3. Persist matches per-CCN with evidence URLs + post dates

About `legacy_signal=True` — DIAGNOSTIC ONLY, NOT ACTIONABLE
  Apify's framing of "no signal = legacy stack = cold target" is correct
  in theory but premature in practice:
    - v1 (Indeed only) yields 100% legacy_signal=True on the 5 QSOs
    - We KNOW some of these have incumbents (Inner Parish at OLOL); the
      flag is a false-positive at v1
    - Local integrators don't appear in any national-vendor dictionary,
      AND they don't run national case studies
  This field is logged for tuning + future re-evaluation once v2 (vendor
  case studies + apify/website-content-crawler on hospital-district
  board minutes) materially lifts the discriminating power. It MUST NOT
  feed into ranking, sort, or QSO-candidate selection at v1.

CLAUDE.md gate: Apify costs real money. --qsos default scope (5 hand-picked
QSOs). --all asks stop-and-confirm.

Costs (misceres/indeed-scraper, $0.005/result)
  --qsos    5 facilities × ~20 jobs = ~$0.50
  --all     1,147 facilities × ~20 jobs = ~$115 (would require confirm)

Run:
    python3 skills/tier-b-incumbent/run.py --ccn 330101
    python3 skills/tier-b-incumbent/run.py --qsos
    python3 skills/tier-b-incumbent/run.py --merge
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

ROOT = Path(__file__).resolve().parents[2]
MART = ROOT / 'data' / 'mart'
SCORED_MART = MART / 'tam_scored.csv'
CACHE_DIR = ROOT / 'data' / 'raw' / 'incumbent' / 'by-ccn'

APIFY_BASE = 'https://api.apify.com/v2'
INDEED_ACTOR = 'misceres~indeed-scraper'
RAG_ACTOR = 'apify~rag-web-browser'      # v2: Google search + page fetch (free compute)
HTTP_TIMEOUT = 60
JOBS_PER_SEARCH = 15
RAG_MAX_RESULTS = 8                        # top N Google results per query
APIFY_POLL_SECONDS = 5
APIFY_MAX_WAIT_SECONDS = 360
RAG_INTER_QUERY_DELAY = 2.0
MIN_HOSPITAL_NAME_LEN = 18                 # avoid false positives like "Memorial Hospital"
CASE_STUDIES_DIR = ROOT / 'data' / 'raw' / 'incumbent' / 'case-studies'
CASE_STUDY_QUERY_TMPL = '"{vendor}" hospital ("case study" OR "deploys" OR "installs" OR "implements" OR "partnership")'

# Targeted queries per facility, each spanning a distinct slice of the
# vendor dictionary. Per Ryan's category mapping:
#   q1 systems/integration → catches Lenel/CCURE/Genetec/Milestone/Avigilon/Brivo
#   q2 program/platform    → catches Everbridge/Rave/AtHoc/Singlewire
#   q3 healthcare-specific → catches CENTEGIX/Strongline/Stanley/Vocera + RTLS
# Bare title-pattern alone won't surface vendors — we regex the description
# body, not the title. This stays a low-hit-rate enrichment by design.
QUERY_TEMPLATES = (
    ('systems',     '{name} "security systems"'),
    ('program',     '{name} "physical security"'),
    ('healthcare',  '{name} "workplace violence"'),
)

# 5 hand-picked QSOs (matches qso-linkedin + tier-b-contracts)
QSO_CCNS = {
    '330028': 'Richmond University Medical Center',
    '330399': 'St Barnabas Hospital',
    '140015': 'Blessing Hospital',
    '490022': 'Mary Washington Hospital',
    '500064': 'Harborview Medical Center',
}


# ============================================================================
# Vendor dictionary
# Per Ryan: skip guard services. Cover the systems Firefly displaces or
# integrates with. Flag Firefly's direct competitors separately.
# ============================================================================

# regex pattern => (vendor display name, category, is_firefly_competitor)
VENDOR_DICTIONARY: list[tuple[str, str, str, bool]] = [
    # ── DURESS / WEARABLE PANIC (Firefly Lattice displacement targets) ──
    (r'\bcentegix\b',                          'Centegix',          'duress',           True),
    (r'\broar(?:\s+for\s+good)?\b',            'ROAR for Good',     'duress',           True),
    (r'\breact\s+mobile\b',                    'React Mobile',      'duress',           True),
    (r'\bstrongline\b',                        'Strongline',        'duress',           False),
    (r'\bcognosos\b',                          'Cognosos',          'duress',           False),
    (r'\bstanley\s+healthcare\b',              'Stanley Healthcare','duress',           False),

    # ── MASS NOTIFICATION ──
    (r'\beverbridge\b',                        'Everbridge',        'mass_notification',True),
    (r'\brave(?:\s+mobile(?:\s+safety)?)?\b',  'Rave Mobile Safety','mass_notification',True),
    (r'\bomnilert\b',                          'Omnilert',          'mass_notification',True),
    (r'\bsinglewire\b',                        'Singlewire',        'mass_notification',False),
    (r'\bathoc\b',                             'AtHoc',             'mass_notification',False),
    (r'\bgenasys\b',                           'Genasys',           'mass_notification',False),
    (r'\bnavigate\s*360\b',                    'Navigate360',       'mass_notification',True),

    # ── GUNSHOT DETECTION (indoor / hospital-relevant — ShotSpotter
    # is outdoor/municipal, intentionally excluded; same for SoundThinking) ──
    (r'\bzero\s*eyes\b',                       'ZeroEyes',                'gunshot_detection',True),
    (r'\bshooter\s+detection\s+systems\b',     'Shooter Detection Systems','gunshot_detection',True),
    (r'\bsds\s+guardian\b',                    'Shooter Detection Systems','gunshot_detection',True),
    (r'\beagl(?:\s+technology)?\b',            'EAGL Technology',         'gunshot_detection',False),
    (r'\bamberbox\b',                          'AmberBox',                'gunshot_detection',False),
    (r'\blattice\b',                           'Lattice (Firefly)',       'gunshot_detection',False),

    # ── COMMS / CLINICAL ALERTING ──
    (r'\bvocera\b',                            'Vocera',            'comms',            True),

    # ── VMS / CAMERAS (integration layer; not direct displacement) ──
    (r'\bgenetec\b',                           'Genetec',           'vms',              False),
    (r'\bavigilon\b',                          'Avigilon',          'vms',              False),
    (r'\bmilestone\s+(?:xprotect|systems)\b',  'Milestone',         'vms',              False),
    (r'\bverkada\b',                           'Verkada',           'vms',              False),
    (r'\baxis\s+communications\b',             'Axis',              'vms',              False),
    (r'\bbosch(?:\s+security)?\b',             'Bosch',             'vms',              False),

    # ── ACCESS CONTROL ──
    (r'\bccure\s*9000\b',                      'Software House CCURE','access_control', False),
    (r'\bsoftware\s+house\b',                  'Software House CCURE','access_control', False),
    (r'\blenel\b',                             'Lenel',             'access_control',   False),
    (r'\bhoneywell\s+prowatch\b',              'Honeywell ProWatch','access_control',   False),
    (r'\bbrivo\b',                             'Brivo',             'access_control',   False),
]

# Compile once
_COMPILED = [(re.compile(p, re.IGNORECASE), name, cat, is_comp)
             for p, name, cat, is_comp in VENDOR_DICTIONARY]


def scan_text(text: str) -> list[dict]:
    """Return list of matched vendors. One entry per unique (name) per scan."""
    if not text:
        return []
    found: dict[str, dict] = {}
    for pat, name, cat, is_comp in _COMPILED:
        m = pat.search(text)
        if m:
            if name not in found:
                # capture a short snippet (40 chars around the match)
                start = max(0, m.start() - 20); end = min(len(text), m.end() + 20)
                snippet = text[start:end].replace('\n', ' ')
                found[name] = {
                    'vendor': name,
                    'category': cat,
                    'is_firefly_competitor': is_comp,
                    'snippet': snippet,
                }
    return list(found.values())


# ============================================================================
# Apify call (Indeed scraper)
# ============================================================================

def run_indeed(client, position: str, max_items: int = JOBS_PER_SEARCH) -> list[dict]:
    """Spawn one Indeed search via Apify. Returns list of job dicts."""
    token = os.environ.get('APIFY_API_TOKEN')
    if not token:
        raise RuntimeError('APIFY_API_TOKEN missing from environment / .env')
    payload = {
        'position': position,
        'maxItemsPerSearch': max_items,
        'country': 'US',
        'parseCompanyDetails': False,
        'followApplyRedirects': False,
        'saveOnlyUniqueItems': True,
    }
    r = client.post(f'{APIFY_BASE}/acts/{INDEED_ACTOR}/runs',
                    params={'token': token}, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    run = r.json()['data']
    run_id = run['id']
    waited = 0
    while waited < APIFY_MAX_WAIT_SECONDS:
        time.sleep(APIFY_POLL_SECONDS); waited += APIFY_POLL_SECONDS
        run = client.get(f'{APIFY_BASE}/actor-runs/{run_id}',
                         params={'token': token}, timeout=HTTP_TIMEOUT).json()['data']
        if run['status'] in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
            break
    if run['status'] != 'SUCCEEDED':
        raise RuntimeError(f'Indeed actor run {run_id} status={run["status"]}')
    items = client.get(f'{APIFY_BASE}/datasets/{run["defaultDatasetId"]}/items',
                      params={'token': token, 'format': 'json', 'clean': '1'},
                      timeout=HTTP_TIMEOUT).json()
    return items


# ============================================================================
# RAG Web Browser — vendor case-study path (v2)
# ============================================================================

def run_rag(client, query: str, max_results: int = RAG_MAX_RESULTS) -> list[dict]:
    """One Google search + page-scrape via apify/rag-web-browser. Returns
    list of {searchResult, metadata, markdown, text}."""
    token = os.environ.get('APIFY_API_TOKEN')
    if not token:
        raise RuntimeError('APIFY_API_TOKEN missing')
    payload = {
        'query': query,
        'maxResults': max_results,
        'outputFormats': ['markdown'],
    }
    r = client.post(f'{APIFY_BASE}/acts/{RAG_ACTOR}/runs',
                    params={'token': token}, json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    run = r.json()['data']; run_id = run['id']; waited = 0
    while waited < APIFY_MAX_WAIT_SECONDS:
        time.sleep(APIFY_POLL_SECONDS); waited += APIFY_POLL_SECONDS
        run = client.get(f'{APIFY_BASE}/actor-runs/{run_id}',
                         params={'token': token}, timeout=HTTP_TIMEOUT).json()['data']
        if run['status'] in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
            break
    if run['status'] != 'SUCCEEDED':
        raise RuntimeError(f'rag-web-browser {run_id} status={run["status"]}')
    return client.get(f'{APIFY_BASE}/datasets/{run["defaultDatasetId"]}/items',
                     params={'token': token, 'format': 'json', 'clean': '1'},
                     timeout=HTTP_TIMEOUT).json()


def _normalize(s: str) -> str:
    s = (s or '').lower()
    s = re.sub(r'[–—\-]+', ' ', s)
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# Generic hospital-name suffixes that aren't distinctive on their own.
# After stripping ALL of these (longest-first), the remainder must still
# carry at least MIN_DISTINCTIVE_LEN chars of unique content, else the
# name is rejected from the index. Replaces the cruder len(norm) >= 18
# heuristic that let "Regional Medical Center" through.
GENERIC_SUFFIXES = (
    'regional medical center', 'community medical center', 'memorial medical center',
    'university medical center', 'general medical center',
    'medical center',
    'regional hospital', 'community hospital', 'memorial hospital',
    'general hospital', 'university hospital', "childrens hospital",
    "children s hospital",
    'health center', 'health system', 'health network',
    'medical group', 'health services', 'healthcare',
    'hospital', 'center', 'campus', 'clinic', 'inc',
)
MIN_DISTINCTIVE_LEN = 3   # require ≥3 chars of distinctive content after stripping
                          # (e.g. "JPS Health Network" → "jps" is distinctive)


def _strip_generics(norm_name: str) -> str:
    """Return the distinctive remainder of a normalized hospital name after
    stripping generic-suffix phrases."""
    s = norm_name
    changed = True
    while changed:
        changed = False
        for suf in sorted(GENERIC_SUFFIXES, key=len, reverse=True):
            if s.endswith(' ' + suf):
                s = s[:-(len(suf) + 1)].strip(); changed = True
            elif s == suf:
                s = ''; changed = True
            elif s.startswith(suf + ' '):
                s = s[len(suf) + 1:].strip(); changed = True
    return s.strip()


# Vendor case studies often refer to hospitals by SHORT brand form
# ("Vail Health") not full CMS name ("Vail Health Hospital"). Index both
# the full normalized name AND the distinctive form, as long as the
# distinctive form is unique across the TAM and long enough to avoid
# false-positives. 7 chars is the empirically-tested floor: "vail health"
# (11 chars) catches CENTEGIX's Vail Health Behavioral Health case study,
# while "jps" (3 chars) stays full-name-only to avoid token collisions.
SHORT_FORM_MIN_LEN = 7


def load_hospital_index() -> list[tuple[str, str, str, str, bool]]:
    """Return list of (search_key, ccn, raw_name, state, is_short_form).
    Full normalized names are eligible for HIGH confidence; short-form
    entries (distinctive prefix only) max out at MEDIUM because the
    short form alone is too ambiguous — "Virginia Hospital" matches
    "Virginia school", "Yavapai Regional" matches "Yavapai college",
    state context can't reliably disambiguate without the suffix word."""
    if not SCORED_MART.exists():
        return []
    out: list[tuple[str, str, str, str, bool]] = []
    seen: set[str] = set()
    with SCORED_MART.open(newline='') as fh:
        for r in csv.DictReader(fh):
            nm = (r.get('facility_name') or '').strip()
            norm = _normalize(nm)
            if len(norm) < MIN_HOSPITAL_NAME_LEN:
                continue
            distinctive = _strip_generics(norm)
            if len(distinctive) < MIN_DISTINCTIVE_LEN:
                continue
            if norm not in seen:
                seen.add(norm)
                out.append((norm, r['ccn'], nm, r.get('state', ''), False))
            if (len(distinctive) >= SHORT_FORM_MIN_LEN
                    and distinctive != norm and distinctive not in seen):
                seen.add(distinctive)
                out.append((distinctive, r['ccn'], nm, r.get('state', ''), True))
    return out


# Full US state names for context-validation in case-study text scans
STATE_NAMES = {
    'AL':'alabama','AK':'alaska','AZ':'arizona','AR':'arkansas','CA':'california',
    'CO':'colorado','CT':'connecticut','DE':'delaware','FL':'florida','GA':'georgia',
    'HI':'hawaii','ID':'idaho','IL':'illinois','IN':'indiana','IA':'iowa',
    'KS':'kansas','KY':'kentucky','LA':'louisiana','ME':'maine','MD':'maryland',
    'MA':'massachusetts','MI':'michigan','MN':'minnesota','MS':'mississippi','MO':'missouri',
    'MT':'montana','NE':'nebraska','NV':'nevada','NH':'new hampshire','NJ':'new jersey',
    'NM':'new mexico','NY':'new york','NC':'north carolina','ND':'north dakota','OH':'ohio',
    'OK':'oklahoma','OR':'oregon','PA':'pennsylvania','RI':'rhode island','SC':'south carolina',
    'SD':'south dakota','TN':'tennessee','TX':'texas','UT':'utah','VT':'vermont',
    'VA':'virginia','WA':'washington','WV':'west virginia','WI':'wisconsin','WY':'wyoming',
    'DC':'district of columbia',
}


# Vendor-deployment verbs that must appear near a hospital-name match to
# distinguish a real deployment claim from incidental name overlap (city
# named "Columbus", state list, etc.). Required for short-form matches.
VENDOR_VERBS = (
    'case study', 'case studies', 'deploys', 'deployed', 'deploying', 'deployment',
    'installs', 'installed', 'installing', 'installation',
    'implements', 'implemented', 'implementing', 'implementation',
    'selects', 'selected', 'selecting', 'selection',
    'partnership', 'partnered', 'partner with', 'partners with',
    'customer', 'client', 'announces', 'announced',
)
_VENDOR_VERB_RE = re.compile(
    r'\b(' + '|'.join(re.escape(v) for v in VENDOR_VERBS) + r')\b', re.IGNORECASE)


def scan_for_hospitals(page_text: str, hospital_index: list[tuple[str, str, str, str, bool]],
                       *, state_proximity_chars: int = 400,
                       verb_proximity_chars: int = 200) -> list[dict]:
    """Substring scan + deployment-verb proximity filter. A hospital-name
    substring match is recorded only if a vendor-deployment verb appears
    within ±verb_proximity_chars (rejects alphabetical state-list and
    city-name collisions that dominate raw substring matches).
    Confidence:
      high   = verb context AND state context (within ±state_proximity_chars)
      medium = verb context only
      (no-verb matches are dropped — too noisy for short-form indexing)"""
    if not page_text:
        return []
    norm_text = _normalize(page_text)
    if not norm_text:
        return []
    matches: list[dict] = []
    for norm_name, ccn, raw_name, state, is_short_form in hospital_index:
        idx = norm_text.find(norm_name)
        if idx == -1:
            continue
        # 1. Required: deployment-verb proximity
        v_lo = max(0, idx - verb_proximity_chars)
        v_hi = min(len(norm_text), idx + len(norm_name) + verb_proximity_chars)
        if not _VENDOR_VERB_RE.search(norm_text[v_lo:v_hi]):
            continue
        # 2. Optional: state-context bumps to high (full-name matches only)
        confidence = 'medium'
        if state and not is_short_form:
            state_full = STATE_NAMES.get(state, '').lower()
            s_lo = max(0, idx - state_proximity_chars)
            s_hi = min(len(norm_text), idx + len(norm_name) + state_proximity_chars)
            window = norm_text[s_lo:s_hi]
            has_state = bool(
                re.search(rf'\b{re.escape(state.lower())}\b', window)
                or (state_full and state_full in window)
            )
            if has_state:
                confidence = 'high'
        snip_start = max(0, idx - 80); snip_end = min(len(norm_text), idx + len(norm_name) + 80)
        matches.append({
            'ccn': ccn, 'facility_name': raw_name, 'state': state,
            'snippet': norm_text[snip_start:snip_end],
            'confidence': confidence,
            'match_form': 'short' if is_short_form else 'full',
        })
    return matches


def _slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')


# ============================================================================
# Publication date extraction (Extension A — vintage signal)
# ============================================================================

# Inferred contract term: assumed if a case study doesn't explicitly state a term.
# 5 years matches typical commercial security/safety vendor contract lengths.
DEFAULT_CONTRACT_TERM_YEARS = 5

# Firefly's own product categories — vendors here directly displace Firefly.
DIRECT_CATEGORIES = {'gunshot_detection', 'mass_notification', 'duress'}
# Adjacent categories — Firefly integrates with these but doesn't displace them.
# Listed competitors here (e.g. Vocera) shouldn't rank as urgent displacement
# targets even when their case studies confirm a hospital deployment.
ADJACENT_CATEGORIES = {'comms', 'vms', 'access_control'}


def _directness(category: str) -> str:
    if category in DIRECT_CATEGORIES: return 'direct'
    if category in ADJACENT_CATEGORIES: return 'adjacent'
    return 'unknown'

_MONTHS = {m: i for i, m in enumerate(
    ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], start=1)}
_MONTH_NAMES_FULL = {m: i for i, m in enumerate(
    ['january','february','march','april','may','june','july','august',
     'september','october','november','december'], start=1)}
_MONTH_LOOKUP = {**_MONTHS, **_MONTH_NAMES_FULL}


def _month_to_num(m: str) -> int | None:
    return _MONTH_LOOKUP.get((m or '').strip().lower()[:9])


def extract_publication_date(result: dict) -> tuple[str | None, str | None, int | None]:
    """Try multiple signals to date a case-study page. Returns
    (iso_date_or_year_string, source_label, year_int). Preference order:
    Google snippet → URL path → markdown body → metadata. Year-only is fine."""

    # 1. Google snippet leading date ("Jan 31, 2024 — ...")
    desc = ((result.get('searchResult') or {}).get('description') or '').strip()
    m = re.match(r'^\s*(\w{3,9})\s+(\d{1,2}),?\s+(\d{4})\s*[—\-–]', desc, re.IGNORECASE)
    if m:
        mo = _month_to_num(m.group(1))
        if mo:
            y = int(m.group(3)); d = int(m.group(2))
            return (f'{y}-{mo:02d}-{d:02d}', 'google_snippet', y)

    # 2. URL path patterns: /YYYY/MM/DD/ or /YYYY/MM/ or year-only /YYYY/
    url = (result.get('searchResult') or {}).get('url') or ''
    m = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
    if m and 1990 < int(m.group(1)) <= 2030:
        return (f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}', 'url_path', int(m.group(1)))
    m = re.search(r'/(\d{4})/(\d{1,2})/', url)
    if m and 1990 < int(m.group(1)) <= 2030:
        return (f'{m.group(1)}-{int(m.group(2)):02d}', 'url_path', int(m.group(1)))
    m = re.search(r'/(\d{4})/', url)
    if m and 1990 < int(m.group(1)) <= 2030:
        return (m.group(1), 'url_year', int(m.group(1)))

    # 3. Markdown body: "Published <date>" or "Posted on <date>"
    md = (result.get('markdown') or result.get('text') or '')[:5000].lower()
    m = re.search(r'(?:published|posted)(?:\s+on)?\s*[:\-]?\s*(\w{3,9})\s+(\d{1,2}),?\s+(\d{4})', md)
    if m:
        mo = _month_to_num(m.group(1))
        if mo:
            y = int(m.group(3))
            return (f'{y}-{mo:02d}-{int(m.group(2)):02d}', 'body', y)

    # 4. Stand-alone year mention adjacent to "case study" / "deployment"
    m = re.search(r'(20\d{2})\s+(?:case\s+study|deployment)', md)
    if m:
        return (m.group(1), 'body_year', int(m.group(1)))

    return (None, None, None)


def phase_case_studies(client, vendor_filter: Optional[list[str]] = None,
                       force: bool = False, verbose: bool = True) -> dict:
    """v2 path A. For each vendor, Google + scrape case-study pages and
    reverse-index hospital mentions. Returns aggregate stats."""
    CASE_STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    hospital_index = load_hospital_index()
    if verbose:
        print(f'  hospital index: {len(hospital_index)} unique normalized names ≥{MIN_HOSPITAL_NAME_LEN} chars')

    # Vendor list (priority order: Firefly competitors first)
    seen_vendors: set[str] = set()
    ordered: list[tuple[str, str, bool]] = []
    for _pat, name, cat, is_comp in VENDOR_DICTIONARY:
        if name in seen_vendors: continue
        seen_vendors.add(name); ordered.append((name, cat, is_comp))
    ordered.sort(key=lambda x: (0 if x[2] else 1, x[1], x[0]))
    if vendor_filter:
        wanted = {v.lower() for v in vendor_filter}
        ordered = [o for o in ordered if o[0].lower() in wanted]

    findings_by_ccn: dict[str, list[dict]] = {}
    queries_run = 0; results_total = 0
    for vendor, cat, is_comp in ordered:
        slug = _slug(vendor)
        cache_path = CASE_STUDIES_DIR / f'{slug}.json'
        if cache_path.exists() and not force:
            data = json.loads(cache_path.read_text())
            if verbose: print(f'  [{vendor:<26}] cached ({len(data.get("results", []))} pages)')
        else:
            q = CASE_STUDY_QUERY_TMPL.format(vendor=vendor)
            if verbose: print(f'  [{vendor:<26}] rag-web-browser: {q!r}')
            try:
                items = run_rag(client, q)
            except Exception as e:
                if verbose: print(f'    ! query failed: {e}')
                items = []
            queries_run += 1
            data = {
                'vendor': vendor, 'category': cat, 'is_firefly_competitor': is_comp,
                'query': q, 'results': items,
                'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            }
            cache_path.write_text(json.dumps(data, indent=2))
            time.sleep(RAG_INTER_QUERY_DELAY)
        # Scan each page
        results_total += len(data.get('results', []))
        page_matches = 0
        for it in data.get('results', []):
            url = (it.get('searchResult') or {}).get('url') or it.get('url', '')
            title = (it.get('metadata') or {}).get('title') or (it.get('searchResult') or {}).get('title') or ''
            md = it.get('markdown') or it.get('text') or ''
            pub_date, pub_source, pub_year = extract_publication_date(it)
            matches = scan_for_hospitals(md, hospital_index)
            for m in matches:
                page_matches += 1
                findings_by_ccn.setdefault(m['ccn'], []).append({
                    'vendor': vendor, 'category': cat,
                    'is_firefly_competitor': is_comp,
                    'page_url': url, 'page_title': title,
                    'facility_name': m['facility_name'], 'state': m['state'],
                    'snippet': m['snippet'],
                    'confidence': m.get('confidence', 'medium'),
                    'publication_date': pub_date,
                    'publication_date_source': pub_source,
                    'publication_year': pub_year,
                })
        if verbose and page_matches:
            print(f'    → {page_matches} hospital mentions across {len(data.get("results", []))} pages')

    return {
        'vendors_queried': len(ordered),
        'queries_run': queries_run,
        'results_total': results_total,
        'ccns_with_findings': len(findings_by_ccn),
        'findings_by_ccn': findings_by_ccn,
    }


def merge_case_studies_into_per_ccn_cache(case_findings: dict[str, list[dict]],
                                          verbose: bool = True) -> int:
    """Update per-CCN incumbent cache files with case_study_findings."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0
    for ccn, findings in case_findings.items():
        cache_path = CACHE_DIR / f'{ccn}.json'
        record = json.loads(cache_path.read_text()) if cache_path.exists() else {
            'ccn': ccn, 'facility_name': findings[0]['facility_name'],
            'state': findings[0]['state'],
            'queries': [], 'jobs_scanned': 0, 'vendors_found': [],
            'job_evidence': [], 'all_vendor_names': '',
            'categories_found': [], 'has_firefly_competitor': False,
            'legacy_signal': False, 'detection_attempted': True,
            'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        }
        # Merge in case-study findings — vendor-level dedup, keep all evidence URLs
        existing_vendor_map = {v['vendor']: v for v in record.get('vendors_found', [])}
        for f in findings:
            v = existing_vendor_map.get(f['vendor'])
            ev = {
                'source': 'case_study',
                'page_url': f['page_url'], 'page_title': f['page_title'],
                'snippet': f['snippet'],
                'confidence': f.get('confidence', 'medium'),
                'publication_date': f.get('publication_date'),
                'publication_date_source': f.get('publication_date_source'),
                'publication_year': f.get('publication_year'),
            }
            if not v:
                existing_vendor_map[f['vendor']] = {
                    'vendor': f['vendor'], 'category': f['category'],
                    'is_firefly_competitor': f['is_firefly_competitor'],
                    'snippet': f['snippet'],
                    'case_study_evidence': [ev],
                }
            else:
                v.setdefault('case_study_evidence', []).append(ev)
        vendors = list(existing_vendor_map.values())
        # Compute per-vendor max_confidence + earliest publication year across all evidence
        for v in vendors:
            confs = set()
            years: list[int] = []
            for ev in v.get('case_study_evidence', []):
                if ev.get('confidence'): confs.add(ev['confidence'])
                py = ev.get('publication_year')
                if isinstance(py, int) and 1990 < py <= 2030: years.append(py)
            # Indeed evidence is treated as 'medium' (no state-context check exists for Indeed
            # since the search itself is hospital-scoped — but still don't promote to 'high').
            if v.get('job_url') and not confs:
                confs.add('medium')
            v['max_confidence'] = 'high' if 'high' in confs else ('medium' if confs else 'unknown')
            v['earliest_publication_year'] = min(years) if years else None
            v['inferred_recompete_year'] = (
                v['earliest_publication_year'] + DEFAULT_CONTRACT_TERM_YEARS
                if v['earliest_publication_year'] else None
            )
            v['directness'] = _directness(v.get('category', ''))

        # Recompute aggregates
        record['vendors_found'] = vendors
        record['all_vendor_names'] = '; '.join(sorted({v['vendor'] for v in vendors}))
        record['categories_found'] = sorted({v['category'] for v in vendors})
        record['has_firefly_competitor'] = any(v.get('is_firefly_competitor') for v in vendors)
        record['legacy_signal'] = (record.get('jobs_scanned', 0) > 0
                                    and not vendors)
        # Primary selection per the confidence + directness invariants:
        # (1) only HIGH-confidence vendors are eligible
        # (2) among eligible, prefer direct (Firefly-category) competitor first,
        #     then adjacent competitor, then any high-conf
        high = [v for v in vendors if v.get('max_confidence') == 'high']
        direct_comps = [v for v in high if v.get('is_firefly_competitor')
                                       and v.get('directness') == 'direct']
        adjacent_comps = [v for v in high if v.get('is_firefly_competitor')
                                         and v.get('directness') == 'adjacent']
        record['primary_incumbent'] = (
            direct_comps[0] if direct_comps else
            adjacent_comps[0] if adjacent_comps else
            (high[0] if high else None)
        )
        # Per-facility max confidence (highest of any vendor's max)
        any_high = any(v.get('max_confidence') == 'high' for v in vendors)
        any_med = any(v.get('max_confidence') == 'medium' for v in vendors)
        record['max_confidence'] = 'high' if any_high else ('medium' if any_med else 'none')
        # Per-facility max directness (only counts HIGH-confidence vendors; medium-only
        # candidates don't earn a directness flag until they're verified)
        directnesses = {v.get('directness') for v in high}
        record['max_directness'] = (
            'direct' if 'direct' in directnesses else
            'adjacent' if 'adjacent' in directnesses else
            'none'
        )
        record['has_case_study_evidence'] = True
        cache_path.write_text(json.dumps(record, indent=2))
        updated += 1
        if verbose:
            print(f'  [{ccn}] +{len(findings)} case-study findings · vendors now: {record["all_vendor_names"]}')
    return updated


# ============================================================================
# Per-facility enrich
# ============================================================================

def enrich_one(client, ccn: str, facility_name: str, state: str,
               *, force: bool = False, verbose: bool = True) -> dict:
    cache_path = CACHE_DIR / f'{ccn}.json'
    if cache_path.exists() and not force:
        if verbose: print(f'  [{ccn}] using cached {cache_path.relative_to(ROOT)}')
        return json.loads(cache_path.read_text())

    if verbose: print(f'  [{ccn}] indeed: 3 targeted queries on {facility_name!r} ({state})')
    queries_log: list[dict] = []
    jobs: list[dict] = []
    seen_urls: set[str] = set()
    for label, tmpl in QUERY_TEMPLATES:
        q = tmpl.format(name=facility_name)
        new_jobs = 0; new_vendor_hits = 0
        try:
            batch = run_indeed(client, q)
            for j in batch:
                u = j.get('url')
                if u and u in seen_urls: continue
                if u: seen_urls.add(u)
                jobs.append(j); new_jobs += 1
                # marginal-yield diagnostic: vendors found in THIS query's batch
                if scan_text((j.get('description') or '') + '\n' + (j.get('positionName') or '')):
                    new_vendor_hits += 1
            if verbose:
                print(f'    [{label:<11}] {q!r}: +{new_jobs} jobs, {new_vendor_hits} w/ vendor')
        except Exception as e:
            if verbose: print(f'    ! query {q!r} failed: {e}')
        queries_log.append({'label': label, 'query': q,
                            'new_jobs': new_jobs, 'jobs_with_vendor_hit': new_vendor_hits})

    matches_by_vendor: dict[str, dict] = {}
    job_evidence: list[dict] = []
    earliest_post = None
    for j in jobs:
        desc = j.get('description') or ''
        title = j.get('positionName') or j.get('title') or ''
        # Scan title + description together
        found = scan_text(title + '\n' + desc)
        post_date = (j.get('postingDateParsed') or '').split('T')[0] or None
        if found:
            for f in found:
                key = f['vendor']
                if key not in matches_by_vendor or (
                    post_date and (matches_by_vendor[key].get('first_seen') or '') < post_date
                ):
                    matches_by_vendor[key] = {**f,
                        'first_seen': post_date,
                        'job_url': j.get('url'),
                        'job_title': title[:120],
                    }
            job_evidence.append({
                'title': title[:120], 'company': j.get('company'),
                'url': j.get('url'), 'posted': post_date,
                'vendors': [f['vendor'] for f in found],
            })
        if post_date:
            if earliest_post is None or post_date < earliest_post:
                earliest_post = post_date

    vendors = list(matches_by_vendor.values())
    legacy = (len(jobs) > 0 and len(vendors) == 0)

    # Pick a "primary" incumbent — Firefly competitor first, then earliest seen
    primary = None
    if vendors:
        comps = [v for v in vendors if v.get('is_firefly_competitor')]
        primary = (comps[0] if comps else vendors[0])

    record = {
        'ccn': ccn,
        'facility_name': facility_name,
        'state': state,
        'queries': queries_log,
        'jobs_scanned': len(jobs),
        'earliest_job_post': earliest_post,
        'vendors_found': vendors,
        'job_evidence': job_evidence,
        'primary_incumbent': primary,
        'all_vendor_names': '; '.join(v['vendor'] for v in vendors),
        'categories_found': sorted({v['category'] for v in vendors}),
        'has_firefly_competitor': any(v.get('is_firefly_competitor') for v in vendors),
        'legacy_signal': legacy,
        'detection_attempted': True,
        'scraped_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2))
    if verbose:
        if vendors:
            print(f'    {len(jobs)} jobs scanned · vendors: {record["all_vendor_names"]}')
        elif legacy:
            print(f'    {len(jobs)} jobs scanned · NO known vendor mentions → legacy_signal=True')
        else:
            print(f'    {len(jobs)} jobs scanned · 0 jobs returned')
    return record


# ============================================================================
# Mart merge
# ============================================================================

INCUMBENT_COLS = [
    'incumbent_detection_attempted',
    'incumbent_jobs_scanned',
    'incumbent_primary_vendor',         # ONLY populated when a HIGH-confidence match exists
    'incumbent_primary_category',
    'incumbent_all_vendors',            # full vendor list (high + medium) for verification UI
    'incumbent_candidate_vendors',      # medium-confidence vendors awaiting verification
    'incumbent_categories',
    'incumbent_has_firefly_competitor',
    'incumbent_max_confidence',         # high | medium | none — per facility
    'incumbent_legacy_signal',
    'incumbent_evidence_url',
    'incumbent_evidence_source',        # indeed | case_study | both
    'incumbent_case_study_count',       # # of case-study pages mentioning this hospital
    'incumbent_inferred_vintage_year',    # earliest publication year of any HIGH-conf vendor evidence
    'incumbent_inferred_recompete_year',  # earliest_year + DEFAULT_CONTRACT_TERM_YEARS
    'incumbent_recompete_status',         # past | current_window | future | unknown
    'incumbent_primary_directness',       # direct | adjacent | unknown (per primary vendor)
    'incumbent_max_directness',           # direct | adjacent | none (per facility, HIGH-conf only)
]


def merge_into_mart() -> int:
    if not SCORED_MART.exists():
        print(f'  ! {SCORED_MART} not found — run forge-score first.'); return 1
    if not CACHE_DIR.exists():
        print(f'  ! cache empty — run enrich first.'); return 1
    cached = {}
    for f in CACHE_DIR.glob('*.json'):
        try:
            d = json.loads(f.read_text()); cached[d['ccn']] = d
        except (KeyError, json.JSONDecodeError):
            continue
    with SCORED_MART.open(newline='') as fh:
        rows = list(csv.DictReader(fh))
    fields = list(rows[0].keys()) if rows else []
    for c in INCUMBENT_COLS:
        if c not in fields: fields.append(c)
    populated = 0
    for r in rows:
        d = cached.get(r['ccn'])
        if not d:
            for c in INCUMBENT_COLS: r.setdefault(c, '')
            continue
        populated += 1
        primary = d.get('primary_incumbent') or {}
        r['incumbent_detection_attempted'] = 'True'
        r['incumbent_jobs_scanned'] = d.get('jobs_scanned', 0)
        # primary_vendor only populated when HIGH confidence — per invariant
        r['incumbent_primary_vendor'] = primary.get('vendor') or ''
        r['incumbent_primary_category'] = primary.get('category') or ''
        r['incumbent_all_vendors'] = d.get('all_vendor_names') or ''
        # Surface medium-confidence vendors as "candidate" — UI rendering caller's responsibility
        candidates = sorted({v['vendor'] for v in (d.get('vendors_found') or [])
                             if v.get('max_confidence') == 'medium'})
        r['incumbent_candidate_vendors'] = '; '.join(candidates)
        r['incumbent_categories'] = '; '.join(d.get('categories_found') or [])
        r['incumbent_has_firefly_competitor'] = 'True' if d.get('has_firefly_competitor') else 'False'
        r['incumbent_max_confidence'] = d.get('max_confidence', '')
        r['incumbent_legacy_signal'] = 'True' if d.get('legacy_signal') else 'False'
        # Evidence URL: prefer case-study (more authoritative) over Indeed
        ev_url = ''
        if primary.get('case_study_evidence'):
            ev_url = primary['case_study_evidence'][0].get('page_url') or ''
        if not ev_url:
            ev_url = primary.get('job_url') or ''
        r['incumbent_evidence_url'] = ev_url
        # Source mix: track which detection paths fired
        sources: list[str] = []
        any_cs = any(v.get('case_study_evidence') for v in (d.get('vendors_found') or []))
        any_idd = any(v.get('job_url') for v in (d.get('vendors_found') or []))
        if any_idd: sources.append('indeed')
        if any_cs: sources.append('case_study')
        r['incumbent_evidence_source'] = '+'.join(sources)
        cs_count = sum(len(v.get('case_study_evidence') or []) for v in (d.get('vendors_found') or []))
        r['incumbent_case_study_count'] = cs_count or ''
        # Vintage: prefer case-study earliest publication year (HIGH conf vendor only —
        # this is the ONLY incumbent-derived signal allowed to influence prioritization
        # per Ryan's invariant, so it must rest on HIGH-confidence evidence).
        vintage_year = (primary or {}).get('earliest_publication_year')
        recompete = (primary or {}).get('inferred_recompete_year')
        if not vintage_year:
            # fall back to Indeed first_seen for backward compatibility (still HIGH-only-eligible)
            fs = (primary or {}).get('first_seen') or d.get('earliest_job_post') or ''
            try:
                vintage_year = int(fs[:4]) if fs else None
            except ValueError:
                vintage_year = None
        r['incumbent_inferred_vintage_year'] = vintage_year or ''
        r['incumbent_inferred_recompete_year'] = recompete or ''
        from datetime import date as _date
        this_year = _date.today().year
        if recompete:
            if recompete < this_year:        status = 'past'
            elif recompete <= this_year + 1: status = 'current_window'
            else:                            status = 'future'
        else:
            status = ''
        r['incumbent_recompete_status'] = status
        r['incumbent_primary_directness'] = (primary or {}).get('directness') or ''
        r['incumbent_max_directness'] = d.get('max_directness', '')
    with SCORED_MART.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f'  → merged {populated} cached records into {SCORED_MART.relative_to(ROOT)}')
    return 0


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
    g.add_argument('--ccn', help='Enrich one facility (Indeed path)')
    g.add_argument('--qsos', action='store_true', help='Enrich the 5 hand-picked QSOs (Indeed path)')
    g.add_argument('--all', action='store_true', help='Enrich every forge_tier A facility (asks confirm)')
    g.add_argument('--case-studies', action='store_true',
                   help='v2 path A: rag-web-browser case-study scan across vendors → reverse-index hospitals')
    g.add_argument('--merge', action='store_true', help='Merge cached records into tam_scored.csv')
    ap.add_argument('--vendor', action='append',
                    help='With --case-studies: restrict to one or more vendor names (repeatable)')
    ap.add_argument('--force', action='store_true', help='Ignore cache and re-scrape')
    args = ap.parse_args()

    if args.merge:
        return merge_into_mart()

    if not os.environ.get('APIFY_API_TOKEN'):
        print('  ! APIFY_API_TOKEN missing from env. Source .env first:')
        print('    set -a && . ./.env && set +a && python3 skills/tier-b-incumbent/run.py …')
        return 1

    with httpx.Client(headers={'User-Agent': 'firefly-gtm/tier-b-incumbent'}) as client:
        if args.case_studies:
            print(f'tier-b-incumbent: v2 case-study path (rag-web-browser)')
            stats = phase_case_studies(client, vendor_filter=args.vendor, force=args.force)
            print()
            print(f'  vendors queried   : {stats["vendors_queried"]}')
            print(f'  rag runs spent    : {stats["queries_run"]} (cached: {stats["vendors_queried"]-stats["queries_run"]})')
            print(f'  pages scraped     : {stats["results_total"]}')
            print(f'  CCNs with hits    : {stats["ccns_with_findings"]}')
            if stats['findings_by_ccn']:
                merged = merge_case_studies_into_per_ccn_cache(stats['findings_by_ccn'])
                print(f'  per-CCN records updated: {merged}')
            return 0

        if args.ccn:
            row = _load_facility(args.ccn)
            if not row:
                print(f'  ! CCN {args.ccn} not found in mart'); return 1
            enrich_one(client, args.ccn, row.get('facility_name', ''), row.get('state', ''),
                       force=args.force)
            return 0

        if args.qsos:
            print(f'tier-b-incumbent: enriching {len(QSO_CCNS)} hand-picked QSOs via Indeed')
            for ccn, name in QSO_CCNS.items():
                row = _load_facility(ccn)
                state = row.get('state', '') if row else ''
                fn = (row.get('facility_name', '') if row else '') or name
                enrich_one(client, ccn, fn, state, force=args.force)
            return 0

        if args.all:
            with SCORED_MART.open(newline='') as fh:
                tier_a = [r for r in csv.DictReader(fh) if r.get('forge_tier') == 'A']
            est_cost = len(tier_a) * JOBS_PER_SEARCH * 0.005
            print(f'  Would enrich {len(tier_a)} forge_tier=A facilities.')
            print(f'  Estimated cost: ~${est_cost:.0f} ({JOBS_PER_SEARCH} jobs/facility × $0.005/job).')
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
