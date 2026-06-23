#!/usr/bin/env python3
"""qso-linkedin: Apify LinkedIn company-employees scrape for the 5 QSOs.

Per CLAUDE.md: paid tools run ONLY on the 5 QSOs (Tier C). Skill enforces.

Run:
    python3 skills/qso-linkedin/run.py --ccn 500064
    python3 skills/qso-linkedin/run.py --all-qsos
    python3 skills/qso-linkedin/run.py --ccn 500064 --url "https://www.linkedin.com/company/...
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / 'documents' / 'qso-briefs' / 'auto'

# 5 hand-picked QSOs (immutable — per CLAUDE.md Tier-C gate)
QSO_CCNS = {
    '500064': {'name': 'Harborview Medical Center', 'state': 'WA',
               'linkedin': 'https://www.linkedin.com/company/harborview-medical-center/'},
    '310009': {'name': 'Clara Maass Medical Center', 'state': 'NJ',
               'linkedin': 'https://www.linkedin.com/company/clara-maass-medical-center/'},
    '330101': {'name': 'NewYork-Presbyterian Hospital', 'state': 'NY',
               'linkedin': 'https://www.linkedin.com/company/new-york-presbyterian-hospital/'},
    '450046': {'name': 'CHRISTUS Spohn Hospital — Corpus Christi', 'state': 'TX',
               'linkedin': 'https://www.linkedin.com/company/christus-spohn-health-system/'},
    '190064': {'name': 'Our Lady of the Lake Regional Medical Center', 'state': 'LA',
               'linkedin': 'https://www.linkedin.com/company/olol/'},
}

APIFY_BASE = 'https://api.apify.com/v2'
# Default actor — well-maintained LinkedIn employees scraper.
# Override via APIFY_LINKEDIN_ACTOR env var if your account uses a different one.
DEFAULT_ACTOR = 'harvestapi~linkedin-company-employees'

PATTERNS_YAML = Path(__file__).parent / 'title-patterns.yaml'

def _load_title_patterns() -> dict:
    """Parse the simple YAML — same flat structure as compliance/product-coverage.yaml."""
    buckets: dict[str, dict] = {}
    cur_bucket = None
    cur_field = None
    multiline = []
    for line in PATTERNS_YAML.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and stripped.endswith(':'):
            if cur_bucket and cur_field == 'rationale' and multiline:
                buckets[cur_bucket]['rationale'] = '\n'.join(multiline).strip()
                multiline = []
            cur_bucket = stripped[:-1]
            buckets[cur_bucket] = {'patterns': []}
            cur_field = None
        elif indent == 2 and ':' in stripped:
            if cur_field == 'rationale' and multiline:
                buckets[cur_bucket]['rationale'] = '\n'.join(multiline).strip()
                multiline = []
            k, _, v = stripped.partition(':')
            v = v.strip()
            cur_field = k.strip()
            if v == '|':
                multiline = []
            elif v:
                buckets[cur_bucket][cur_field] = v
        elif indent == 4 and stripped.startswith('-') and cur_field == 'patterns':
            pat = stripped[1:].strip()
            buckets[cur_bucket]['patterns'].append(pat)
        elif indent >= 4 and cur_field == 'rationale':
            multiline.append(stripped)
    if cur_bucket and cur_field == 'rationale' and multiline:
        buckets[cur_bucket]['rationale'] = '\n'.join(multiline).strip()
    return buckets

# Loaded at import-time
_BUCKETS = _load_title_patterns()

def load_env():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                v = v.split('#', 1)[0].strip()
                if v:
                    os.environ.setdefault(k.strip(), v)

def run_apify_actor(actor: str, input_payload: dict, token: str) -> list[dict]:
    """Synchronously run an Apify actor and return its dataset items."""
    url = f'{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items?token={token}'
    resp = httpx.post(url, json=input_payload, timeout=600.0)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f'Apify {resp.status_code}: {resp.text[:600]}')
    try:
        return resp.json()
    except Exception:
        return [{'raw': resp.text[:2000]}]

def _employee_name(e: dict) -> str:
    """Combine first/last when present; fall back to other name fields."""
    fn = (e.get('firstName') or '').strip()
    ln = (e.get('lastName') or '').strip()
    if fn or ln:
        return f'{fn} {ln}'.strip()
    return (e.get('name') or e.get('fullName') or '').strip() or '?'

def _employee_title(e: dict) -> str:
    return (e.get('headline') or e.get('title') or e.get('position') or '').strip()

def _employee_url(e: dict) -> str:
    return e.get('linkedinUrl') or e.get('profile_url') or e.get('profileUrl') or e.get('url') or ''

# Pre-compile patterns with word-boundary matching so e.g. "coo" doesn't match
# "coordinator" and "president" doesn't match "presidential".
_COMPILED = {
    bucket: [re.compile(r'\b' + re.escape(pat.lower()) + r'\b')
             for pat in data.get('patterns', [])]
    for bucket, data in _BUCKETS.items()
}

def classify_employees(employees: list[dict]) -> dict:
    """Bucket employees by buying-committee role using title-patterns.yaml.
    Order: cosponsor → champion → edm → influencer → other.
    Uses WORD-BOUNDARY matching to avoid false positives like
    'coo' ⊂ 'coordinator' or 'president' ⊂ 'presidential'."""
    out = {k: [] for k in list(_BUCKETS.keys()) + ['other']}
    bucket_order = ['cosponsor', 'champion', 'edm', 'influencer']
    for e in employees:
        title = _employee_title(e).lower()
        matched = None
        for bucket in bucket_order:
            for rex in _COMPILED.get(bucket, []):
                if rex.search(title):
                    matched = bucket
                    break
            if matched:
                break
        out[matched or 'other'].append(e)
    return out

def write_brief(ccn: str, qso: dict, employees: list[dict], buckets: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', qso['name'].lower()).strip('-')[:40]
    # raw json dump
    json_out = OUT_DIR / f'linkedin-{ccn}.json'
    json_out.write_text(json.dumps({
        'ccn': ccn,
        'facility_name': qso['name'],
        'state': qso['state'],
        'linkedin_url': qso['linkedin'],
        'employee_count': len(employees),
        'employees': employees,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    # classified buying-committee markdown
    md_out = OUT_DIR / f'buying-committee-{ccn}-{slug}.md'
    lines = [
        f'<!-- AUTO-GENERATED by skills/qso-linkedin on {datetime.now().date().isoformat()} -->',
        f'<!-- source: Apify LinkedIn actor · {qso["linkedin"]} -->',
        '',
        f'# Buying Committee — {qso["name"]} ({qso["state"]})',
        '',
        f'**CCN**: {ccn} · **Employees scraped**: {len(employees)} · **LinkedIn**: {qso["linkedin"]}',
        '',
        'Per CLAUDE.md Tier-C: data scraped via Apify for the 5 hand-picked QSOs only.',
        'Internal research; **do not external-send named contacts at QSO 5 (OLOL) without Legal review**.',
        '',
    ]
    for bucket_name, label in [
        ('cosponsor', '### Cosponsor — CNO / clinical-side unlock'),
        ('champion', '### Champion — security, safety, emergency mgmt, WPV coordinator'),
        ('edm', '### EDM — C-suite + system VP Support Services'),
        ('influencer', '### Influencer — facilities, IT, risk, CMO'),
    ]:
        lines.append(label)
        if not buckets.get(bucket_name):
            lines.append('_None matched._')
        else:
            lines.append('| Name | Title | Profile |')
            lines.append('|---|---|---|')
            for e in buckets[bucket_name][:15]:
                name = _employee_name(e)
                title = _employee_title(e)[:90]
                url = _employee_url(e)
                lines.append(f'| {name} | {title} | {url} |')
        lines.append('')
    lines.append(f'### Other employees ({len(buckets["other"])} total — not surfaced by default)')
    lines.append('')
    lines.append('See `linkedin-' + ccn + '.json` for the full dataset.')
    lines.append('')
    lines.append('## How these patterns were chosen')
    lines.append('')
    lines.append('Patterns live in `skills/qso-linkedin/title-patterns.yaml`, derived from')
    lines.append('`context/personas/healthcare-edm.md` + `context/personas/healthcare-champion.md`.')
    lines.append('Not empirically validated against closed Firefly deals — to validate,')
    lines.append('pull IAHSS member roster + cross-ref. Edit the YAML to refine.')
    md_out.write_text('\n'.join(lines))
    return md_out

def reclassify_cached(ccn: str) -> Path | None:
    """Re-run classification on already-fetched data (no Apify cost)."""
    cache = OUT_DIR / f'linkedin-{ccn}.json'
    if not cache.exists():
        print(f'  ! no cache for {ccn} — fetch first')
        return None
    data = json.loads(cache.read_text())
    employees = data.get('employees', [])
    qso = dict(QSO_CCNS.get(ccn, {'name': data.get('facility_name','?'),
                                   'state': data.get('state','?'),
                                   'linkedin': data.get('linkedin_url','')}))
    buckets = classify_employees(employees)
    print(f'  reclassified {ccn} ({len(employees)} employees): '
          f'cosponsor={len(buckets.get("cosponsor",[]))} '
          f'champion={len(buckets.get("champion",[]))} '
          f'edm={len(buckets.get("edm",[]))} '
          f'influencer={len(buckets.get("influencer",[]))} '
          f'other={len(buckets.get("other",[]))}')
    return write_brief(ccn, qso, employees, buckets)

def fetch_one(ccn: str, url_override: str | None = None) -> Path | None:
    if ccn not in QSO_CCNS:
        print(f'  ! {ccn} is not one of the 5 QSOs — refusing (CLAUDE.md Tier-C gate)')
        return None
    # cache-skip: if we already have it, just reclassify
    cache = OUT_DIR / f'linkedin-{ccn}.json'
    if cache.exists():
        print(f'  → {ccn} already cached — reclassifying without re-Apify')
        return reclassify_cached(ccn)
    qso = dict(QSO_CCNS[ccn])
    if url_override:
        qso['linkedin'] = url_override
    token = os.environ.get('APIFY_API_TOKEN')
    if not token:
        raise SystemExit('APIFY_API_TOKEN not set in .env')
    actor = os.environ.get('APIFY_LINKEDIN_ACTOR', DEFAULT_ACTOR)
    print(f'  → scraping {qso["name"]} via {actor}')
    print(f'    URL: {qso["linkedin"]}')
    # harvestapi/linkedin-company-employees input shape:
    # - companies: list of LinkedIn company URLs
    # - maxItems: cap per company (keeps cost down)
    # - profileScraperMode: must be exact string with price embedded
    #   "Short ($4 per 1k)" / "Full ($8 per 1k)" / "Full + email search ($12 per 1k)"
    input_payload = {
        'companies': [qso['linkedin']],
        'maxItems': 100,
        'profileScraperMode': 'Full ($8 per 1k)',  # title + headline + URL; skip email
    }
    t0 = time.time()
    try:
        items = run_apify_actor(actor, input_payload, token)
    except Exception as e:
        print(f'    ! error: {e}')
        return None
    elapsed = time.time() - t0
    print(f'    ← returned {len(items)} items in {elapsed:.0f}s')
    if not items:
        return None
    buckets = classify_employees(items)
    print(f'      EDM: {len(buckets["edm"])} · Champion: {len(buckets["champion"])} · '
          f'Influencer: {len(buckets["influencer"])} · Other: {len(buckets["other"])}')
    out = write_brief(ccn, qso, items, buckets)
    print(f'    → {out.relative_to(ROOT)}')
    return out

def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument('--ccn')
    ap.add_argument('--all-qsos', action='store_true')
    ap.add_argument('--url', help='override the LinkedIn URL for this CCN')
    ap.add_argument('--reclassify', action='store_true',
                    help='reclassify cached data only — no Apify call')
    args = ap.parse_args()
    if args.reclassify:
        targets = [args.ccn] if args.ccn else list(QSO_CCNS.keys())
        for ccn in targets:
            reclassify_cached(ccn)
        return
    targets = []
    if args.all_qsos:
        targets = list(QSO_CCNS.keys())
    elif args.ccn:
        targets = [args.ccn]
    if not targets:
        ap.print_help(); return
    print(f'\nscraping {len(targets)} QSO(s) via Apify...')
    for ccn in targets:
        fetch_one(ccn, args.url if args.ccn else None)

if __name__ == '__main__':
    main()
