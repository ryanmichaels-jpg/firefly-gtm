#!/usr/bin/env python3
"""dashboard/build-data.py — convert data/mart/tam_scored.csv to a
PII-redacted JSON the static dashboard reads.

Run:
    python3 dashboard/build-data.py

Writes:
    dashboard/data.json   — embedded in dashboard/index.html at build time

Redactions:
  - edm_seed_name → dropped (PII per CLAUDE.md)
  - edm_seed_phone → dropped (PII)
  - edm_seed_title → kept (functional / public role info)
  - everything else from the scored mart is passed through
"""
from __future__ import annotations
import csv
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'mart' / 'tam_scored.csv'
REF_MANDATES = ROOT / 'data' / 'reference' / 'mandates.csv'
OUT = ROOT / 'dashboard' / 'data.json'

PII_FIELDS = {'edm_seed_name', 'edm_seed_phone'}

def _int(v):
    try:
        return int(v) if v not in (None, '', 'None') else None
    except (TypeError, ValueError):
        return None

def _float(v):
    try:
        return float(v) if v not in (None, '', 'None') else None
    except (TypeError, ValueError):
        return None

def _truthy(v) -> bool:
    return str(v).strip().lower() in ('true', '1', 'yes', 'y')

def sub_segment(htype: str, has_ed: bool, beds: int | None) -> str:
    """Derived from hospital_type + ED + bed count."""
    if 'critical access' in htype.lower():
        return 'Community / Critical Access'
    if 'psychiatric' in htype.lower():
        return 'Psychiatric'
    if "childrens" in htype.lower() or "children" in htype.lower():
        return "Pediatric Specialty"
    if beds and beds >= 500 and has_ed:
        return 'Academic / Trauma'
    if beds and beds >= 200 and has_ed:
        return 'Regional Acute'
    return 'Acute Care'

def days_to_deadline(effective_date: str | None) -> int | None:
    if not effective_date:
        return None
    try:
        d = date.fromisoformat(effective_date)
        delta = (d - date.today()).days
        return delta
    except ValueError:
        return None

def main():
    rows = []
    with open(SRC, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            beds = _int(r.get('beds'))
            has_ed = _truthy(r.get('has_ED'))
            has_bh = _truthy(r.get('has_behavioral_unit'))
            tier_num = _int(r.get('facility_tier')) or 3
            forge_total = _int(r.get('forge_total')) or 0
            # collapse Tier-A/B/C/X into a sortable enrichment letter
            forge_tier = (r.get('forge_tier') or 'X').strip()
            acute = _int(r.get('acute_need')) or 0
            event = _int(r.get('event')) or 0
            gravity = _int(r.get('gravity')) or 0
            eff = (r.get('effective_date') or '').strip() or None
            days = days_to_deadline(eff)
            mandate_status = (r.get('mandate_status') or '').strip()
            # display status: Upcoming → Upcoming, In force → In force,
            # surface "Enforcement" if In force AND it's been ≥ 6 months
            display_status = mandate_status
            try:
                if mandate_status == 'In force' and eff:
                    months_since = (date.today() - date.fromisoformat(eff)).days / 30.4
                    if months_since >= 6:
                        display_status = 'Enforcement'
            except ValueError:
                pass
            row = {
                'id': r['ccn'],
                'ccn': r['ccn'],
                'name': r.get('facility_name', '').strip(),
                'system': r.get('parent_system') or 'Independent facility',
                'city': r.get('city', '').strip(),
                'state': r.get('state', '').strip(),
                'lat': float(r['lat']) if r.get('lat') else None,
                'lng': float(r['lng']) if r.get('lng') else None,
                'beds': beds,
                'has_ED': has_ed,
                'has_behavioral_unit': has_bh,
                'sub_segment': sub_segment(r.get('hospital_type', ''), has_ed, beds),
                'tier_num': tier_num,
                'forge_total': forge_total,
                'forge_acute_need': acute,
                'forge_event': event,
                'forge_gravity': gravity,
                'forge_tier': forge_tier,
                'enrichment_tier': r.get('enrichment_tier', 'C'),
                'mandate_name': (r.get('mandate_name') or '').strip(),
                'mandate_status': mandate_status,
                'mandate_status_display': display_status,
                'mandate_scope': (r.get('mandate_scope') or '').strip(),
                'effective_date': eff,
                'days_to_deadline': days,
                'edm_title': (r.get('edm_seed_title') or '').strip() or None,
                'standalone_score': _float(r.get('standalone_score')),
                'standalone_band': (r.get('standalone_band') or '').strip() or None,
                'system_hospital_count': _int(r.get('system_hospital_count')),
                'system_name': (r.get('system_name') or '').strip() or None,
                'affiliation_unverified': _truthy(r.get('affiliation_unverified')),
                'forge_capped_to_b': _truthy(r.get('forge_capped_to_b')),
                # tier-b-contracts (USAspending federal-recipient enrichment)
                'usa_recipient_name': (r.get('usa_recipient_name') or '').strip() or None,
                'usa_match_confidence': _float(r.get('usa_match_confidence')),
                'usa_award_count_5yr': _int(r.get('usa_award_count_5yr')),
                'usa_contract_count_5yr': _int(r.get('usa_contract_count_5yr')),
                'usa_assistance_count_5yr': _int(r.get('usa_assistance_count_5yr')),
                'usa_total_award_5yr': _float(r.get('usa_total_award_5yr')),
                'usa_largest_award_5yr': _float(r.get('usa_largest_award_5yr')),
                'usa_top_funding_agency': (r.get('usa_top_funding_agency') or '').strip() or None,
                'usa_top_naics': (r.get('usa_top_naics') or '').strip() or None,
                'usa_top_naics_desc': (r.get('usa_top_naics_desc') or '').strip() or None,
                'usa_top_cfda': (r.get('usa_top_cfda') or '').strip() or None,
                'usa_evidence_url': (r.get('usa_evidence_url') or '').strip() or None,
                'usa_needs_review': _truthy(r.get('usa_needs_review')),
                # tier-b-incumbent (Apify Indeed vendor-name detection)
                'incumbent_detection_attempted': _truthy(r.get('incumbent_detection_attempted')),
                'incumbent_jobs_scanned': _int(r.get('incumbent_jobs_scanned')),
                'incumbent_primary_vendor': (r.get('incumbent_primary_vendor') or '').strip() or None,
                'incumbent_primary_category': (r.get('incumbent_primary_category') or '').strip() or None,
                'incumbent_all_vendors': (r.get('incumbent_all_vendors') or '').strip() or None,
                'incumbent_candidate_vendors': (r.get('incumbent_candidate_vendors') or '').strip() or None,
                'incumbent_max_confidence': (r.get('incumbent_max_confidence') or '').strip() or None,
                'incumbent_categories': (r.get('incumbent_categories') or '').strip() or None,
                'incumbent_has_firefly_competitor': _truthy(r.get('incumbent_has_firefly_competitor')),
                'incumbent_legacy_signal': _truthy(r.get('incumbent_legacy_signal')),
                'incumbent_evidence_url': (r.get('incumbent_evidence_url') or '').strip() or None,
                'incumbent_evidence_source': (r.get('incumbent_evidence_source') or '').strip() or None,
                'incumbent_case_study_count': _int(r.get('incumbent_case_study_count')),
                'incumbent_inferred_vintage_year': (r.get('incumbent_inferred_vintage_year') or '').strip() or None,
                'is_qso_candidate': _truthy(r.get('is_qso_candidate')),
                'forge_rationale': (r.get('forge_rationale') or '').strip(),
                'acute_need_evidence': (r.get('acute_need_evidence') or '').strip(),
                'event_evidence': (r.get('event_evidence') or '').strip(),
                'gravity_evidence': (r.get('gravity_evidence') or '').strip(),
                'needs_review': _truthy(r.get('needs_review')),
                # Tier-B/C fields we don't have yet
                'incumbent_vendor': None,
                'contract_expiry': None,
                # OSHA SIR enrichment (Tier-B, populated by skills/tier-b-osha)
                'osha_severe_injury_count_24mo':
                    _int(r.get('osha_severe_injury_count_24mo')) or None,
                'osha_first_evidence_url': (r.get('osha_first_evidence_url') or '').strip() or None,
                'osha_first_evidence_id': (r.get('osha_first_evidence_id') or '').strip() or None,
                'osha_first_evidence_date': (r.get('osha_first_evidence_date') or '').strip() or None,
                'osha_first_evidence_nature': (r.get('osha_first_evidence_nature') or '').strip() or None,
                'osha_evidence_natures': (r.get('osha_evidence_natures') or '').strip() or None,
                'osha_evidence_ids': (r.get('osha_evidence_ids') or '').strip() or None,
                # one-off draft path for QSOs
                'one_off_brief': None,
            }
            rows.append(row)

    # link QSO briefs
    qso_brief_paths = {
        '500064': '../documents/qso-briefs/qso-1-harborview.md',
        '310009': '../documents/qso-briefs/qso-2-clara-maass.md',
        '330101': '../documents/qso-briefs/qso-3-nyp.md',
        '450046': '../documents/qso-briefs/qso-4-christus-spohn.md',
        '190064': '../documents/qso-briefs/qso-5-our-lady-of-the-lake.md',
    }
    for row in rows:
        if row['ccn'] in qso_brief_paths:
            row['one_off_brief'] = qso_brief_paths[row['ccn']]

    # quick metadata + per-state mandate (from primary mandate per state)
    state_mandate: dict[str, dict] = {}
    for r in rows:
        st = r['state']
        if not st: continue
        if st not in state_mandate and r['mandate_name']:
            state_mandate[st] = {
                'name': r['mandate_name'],
                'status': r['mandate_status_display'],
                'effective_date': r['effective_date'],
                'days_to_deadline': r['days_to_deadline'],
            }

    # funnel computed from actual data
    total = len(rows)
    scored = sum(1 for r in rows if r['forge_total'] > 0)
    qso = sum(1 for r in rows if r['is_qso_candidate'])
    # "engaged" proxy: Tier-A (forge_tier='A'); pipeline value heuristic
    engaged = sum(1 for r in rows if r['forge_tier'] == 'A')

    out = {
        'rows': rows,
        'metadata': {
            'total': total,
            'scored': scored,
            'engaged': engaged,
            'qualified': qso,
            'states': sorted(set(r['state'] for r in rows if r['state'])),
            'state_mandate': state_mandate,
            'generated_at': date.today().isoformat(),
            'source': 'data/mart/tam_scored.csv',
        }
    }
    OUT.write_text(json.dumps(out, separators=(',', ':')))
    print(f'wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes, {total} rows)')
    print(f'  tier A: {sum(1 for r in rows if r["forge_tier"]=="A")}')
    print(f'  tier B: {sum(1 for r in rows if r["forge_tier"]=="B")}')
    print(f'  tier C: {sum(1 for r in rows if r["forge_tier"]=="C")}')
    print(f'  tier X: {sum(1 for r in rows if r["forge_tier"]=="X")}')
    print(f'  QSOs: {qso}')
    print(f'  geocoded: {sum(1 for r in rows if r["lat"])}/{total}')

if __name__ == '__main__':
    main()
