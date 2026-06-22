#!/usr/bin/env python3
"""forge-score: apply the F.O.R.G.E. framework to data/mart/tam.csv.

Two phases:
  1. enrich — re-join AHRQ Compendium to add safety-net proxy fields
            (hos_highdpp, hos_highuc, hos_majteach) used by Acute Need
  2. score  — apply FORGE rubrics, write data/mart/tam_scored.csv
            + a redacted committable sample

Run:
    python3 skills/forge-score/run.py --all
    python3 skills/forge-score/run.py --step enrich
    python3 skills/forge-score/run.py --step score
    python3 skills/forge-score/run.py --check
"""
from __future__ import annotations
import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
STAGE = ROOT / 'data' / 'staging'
MART = ROOT / 'data' / 'mart'

EXEC_TITLES = (
    'ceo', 'cfo', 'coo', 'cio', 'cto', 'cmo', 'cno', 'cso',
    'president', 'administrator', 'executive director', 'chief',
    'vp ', 'vice president', 'director of', 'general counsel',
)

# ----------------------------------------------------------------------------
def read_csv(path: Path, encoding: str = 'utf-8') -> list[dict]:
    with open(path, encoding=encoding, newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict]) -> None:
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
# PHASE 1 — enrich with AHRQ safety-net proxy fields
# ----------------------------------------------------------------------------
def phase_enrich() -> Path:
    banner('PHASE 1 · ENRICH · AHRQ safety-net proxy fields')
    mart = read_csv(MART / 'tam.csv')
    linkage = read_csv(
        RAW / 'ahrq-compendium' / 'chsp-hospital-linkage-2023.csv',
        encoding='cp1252')
    by_ccn = {l['ccn']: l for l in linkage if l.get('ccn')}
    populated = 0
    flagged_safety_net = 0
    flagged_teaching = 0
    for r in mart:
        l = by_ccn.get(r.get('ccn'))
        if l:
            populated += 1
            for col in ('hos_majteach', 'hos_vmajteach', 'hos_teachint',
                        'hos_highdpp', 'hos_ucburden', 'hos_highuc',
                        'hos_children'):
                r[col] = l.get(col, '').strip() or None
            if (r.get('hos_highdpp') == '1' or r.get('hos_highuc') == '1'):
                flagged_safety_net += 1
            if (r.get('hos_majteach') == '1' or r.get('hos_vmajteach') == '1'):
                flagged_teaching += 1
        else:
            for col in ('hos_majteach', 'hos_vmajteach', 'hos_teachint',
                        'hos_highdpp', 'hos_ucburden', 'hos_highuc',
                        'hos_children'):
                r[col] = None
    out = STAGE / 'forge_01_enrich.csv'
    write_csv(out, mart)
    pct = 100.0 * populated / max(len(mart), 1)
    print(f'  → {out.relative_to(ROOT)} · {len(mart)} rows · '
          f'AHRQ fields populated: {populated}/{len(mart)} ({pct:.1f}%)')
    print(f'    flagged safety-net (high DSH or high UC): {flagged_safety_net}')
    print(f'    flagged major-teaching:                   {flagged_teaching}')
    return out


# ----------------------------------------------------------------------------
# PHASE 2 — score
# ----------------------------------------------------------------------------
def _truthy(v) -> bool:
    return str(v).strip().lower() in ('true', '1', 'yes', 'y')

def _int(v) -> int | None:
    try:
        s = str(v).strip()
        return int(s) if s and s.lower() not in ('none', 'null', 'nan') else None
    except (TypeError, ValueError):
        return None

def _is_exec_title(title: str) -> bool:
    t = (title or '').lower()
    return any(kw in t for kw in EXEC_TITLES)

def _fit(r: dict) -> tuple[bool, str]:
    htype = (r.get('hospital_type') or '').strip()
    htype_ok = htype in ('Acute Care Hospitals', 'Psychiatric',
                         'Childrens', "Children's")
    has_ed = _truthy(r.get('has_ED'))
    has_bh = _truthy(r.get('has_behavioral_unit'))
    beds = _int(r.get('beds'))
    capacity_ok = has_ed or has_bh or (beds is not None and beds >= 50)
    mandate_ok = bool((r.get('mandate_status') or '').strip())
    if htype_ok and capacity_ok and mandate_ok:
        return True, 'PASS'
    reasons = []
    if not htype_ok:    reasons.append(f'type={htype or "?"}')
    if not capacity_ok: reasons.append(f'no-ED/BH/beds<50 (beds={beds})')
    if not mandate_ok:  reasons.append('no mandate')
    return False, 'FAIL: ' + ', '.join(reasons)

def _event(r: dict) -> tuple[int, str]:
    status = (r.get('mandate_status') or '').strip()
    scope = (r.get('mandate_scope') or '').strip()
    eff = (r.get('effective_date') or '').strip()
    if scope != 'state':
        return 0, f'no state-specific mandate (scope={scope or "—"})'
    if status == 'In force':
        return 3, f'{r.get("mandate_name", "")[:40]} In force'
    if status == 'Upcoming' and eff:
        try:
            d = date.fromisoformat(eff)
            months_out = (d - date.today()).days / 30.4
            if months_out <= 12:
                return 3, f'{r.get("mandate_name", "")[:40]} Upcoming ≤12mo ({eff})'
            return 2, f'{r.get("mandate_name", "")[:40]} Upcoming >12mo ({eff})'
        except ValueError:
            pass
    if status == 'Upcoming':
        return 2, f'{r.get("mandate_name", "")[:40]} Upcoming (no date)'
    return 0, f'unknown status: {status}'

def _acute_need(r: dict) -> tuple[int, str]:
    """AHRQ safety-net proxy. Documented Tier-A approximation; Tier-B
    will replace these with OSHA citations + 990 narrative + news incidents."""
    safety_net = (r.get('hos_highdpp') == '1' or r.get('hos_highuc') == '1')
    if safety_net:
        which = []
        if r.get('hos_highdpp') == '1': which.append('high DSH')
        if r.get('hos_highuc') == '1': which.append('high UC')
        return 3, f'safety-net hospital ({", ".join(which)}); proxy via AHRQ'
    major_teaching = r.get('hos_majteach') == '1' or r.get('hos_vmajteach') == '1'
    has_bh = _truthy(r.get('has_behavioral_unit'))
    reasons = []
    if major_teaching: reasons.append('major teaching')
    if has_bh:         reasons.append('behavioral health unit')
    if reasons:
        return 2, f'higher-acuity ({", ".join(reasons)}); proxy'
    return 1, 'no AHRQ proxy signal; Tier-B will refine'

def _gravity(r: dict) -> tuple[int, str]:
    edm_name = (r.get('edm_seed_name') or '').strip()
    edm_title = (r.get('edm_seed_title') or '').strip()
    if not edm_name:
        return 0, 'no edm_seed (NPPES unmatched)'
    is_exec = _is_exec_title(edm_title)
    beds = _int(r.get('beds')) or 0
    in_multi_system = False
    fis = _int(r.get('facilities_in_system'))
    if fis is not None and fis >= 2:
        in_multi_system = True
    if is_exec and beds >= 250 and in_multi_system:
        return 3, f'{edm_title} at {beds}-bed system facility ({fis}-facility)'
    if is_exec:
        return 2, f'{edm_title} (beds={beds}, sys_facilities={fis or "—"})'
    return 1, f'non-exec title: {edm_title or "—"}'

def _tier(total: int, fit_pass: bool) -> str:
    if not fit_pass or total == 0:
        return 'X'
    if total >= 12: return 'A'
    if total >= 6:  return 'B'
    return 'C'

def phase_score() -> Path:
    banner('PHASE 2 · SCORE · apply FORGE rubrics')
    rows = read_csv(STAGE / 'forge_01_enrich.csv')
    tier_counts = {'A': 0, 'B': 0, 'C': 0, 'X': 0}
    for r in rows:
        fit_pass, fit_reason = _fit(r)
        event, event_reason = _event(r)
        acute, acute_reason = _acute_need(r)
        gravity, gravity_reason = _gravity(r)
        total = (acute * event * gravity) if fit_pass else 0
        tier = _tier(total, fit_pass)
        r['fit_pass'] = fit_pass
        r['fit_reason'] = fit_reason
        r['acute_need'] = acute
        r['acute_need_evidence'] = acute_reason
        r['event'] = event
        r['event_evidence'] = event_reason
        r['gravity'] = gravity
        r['gravity_evidence'] = gravity_reason
        r['forge_total'] = total
        r['forge_tier'] = tier
        r['forge_rationale'] = (
            f'Acute={acute} ({acute_reason}) · '
            f'Event={event} ({event_reason}) · '
            f'Gravity={gravity} ({gravity_reason})'
        )
        r['resolve_status'] = 'confirm on call'
        r['clarity_status'] = 'confirm on call'
        r['is_qso_candidate'] = r['ccn'] in QSO_CCNS
        r['scored_at'] = datetime.utcnow().isoformat() + 'Z'
        tier_counts[tier] += 1
    out = MART / 'tam_scored.csv'
    write_csv(out, rows)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows')
    for t in ('A', 'B', 'C', 'X'):
        pct = 100 * tier_counts[t] / max(len(rows), 1)
        print(f'    tier {t}: {tier_counts[t]:>4} ({pct:.1f}%)')
    # write a redacted committable sample
    sample = _build_sample(rows)
    sample_path = MART / 'tam_scored_sample.csv'
    write_csv(sample_path, sample)
    print(f'  → {sample_path.relative_to(ROOT)} · {len(sample)} rows (PII redacted)')
    return out

# Hand-picked Tier-C QSOs from Step 4 of the runbook. Selection rationale +
# per-account briefs live in documents/qso-briefs/. These CCNs are flagged
# in the sample mart so reviewers can find them quickly.
QSO_CCNS = {
    '500064',  # Harborview Medical Center (WA)
    '310009',  # Clara Maass Medical Center (NJ)
    '330101',  # NewYork-Presbyterian Hospital (NY)
    '450046',  # CHRISTUS Spohn Hospital Corpus Christi (TX)
    '190064',  # Our Lady of the Lake Regional Medical Center (LA)
}

def _build_sample(rows: list[dict]) -> list[dict]:
    """Pick top-3 per (state, tier), guarantee the 5 hand-picked QSOs are
    included, redact PII columns. Output is committable."""
    keep_cols = [
        'ccn', 'facility_name', 'parent_system', 'facilities_in_system',
        'state', 'city', 'beds', 'has_ED', 'has_behavioral_unit',
        'hos_majteach', 'hos_highdpp', 'hos_highuc',
        'mandate_name', 'mandate_status', 'mandate_scope', 'effective_date',
        'edm_seed_title',  # title is public-functional info; name+phone redacted
        'fit_pass', 'acute_need', 'event', 'gravity', 'forge_total',
        'forge_tier', 'forge_rationale',
        'is_qso_candidate',
    ]
    # pick top-N per (state, tier)
    by_state_tier: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r['state'], r['forge_tier'])
        by_state_tier.setdefault(key, []).append(r)
    picks: dict[str, dict] = {}  # ccn → row
    for key, lst in by_state_tier.items():
        lst.sort(key=lambda x: int(x.get('forge_total') or 0), reverse=True)
        for r in lst[:3]:
            picks[r['ccn']] = r
    # guarantee the 5 hand-picked QSOs are in the sample
    for r in rows:
        if r['ccn'] in QSO_CCNS:
            picks[r['ccn']] = r
    # mark + redact
    sample = []
    for r in picks.values():
        r['is_qso_candidate'] = r['ccn'] in QSO_CCNS
        out_row = {k: r.get(k) for k in keep_cols}
        out_row['edm_seed_redacted'] = bool(r.get('edm_seed_name'))
        sample.append(out_row)
    # also write is_qso_candidate back to the full mart rows (mutated above)
    sample.sort(key=lambda x: (
        not x['is_qso_candidate'],  # QSOs first
        x['forge_tier'],
        -int(x.get('forge_total') or 0),
        x['state']
    ))
    return sample


# ----------------------------------------------------------------------------
# acceptance check
# ----------------------------------------------------------------------------
def acceptance() -> int:
    banner('ACCEPTANCE · data/mart/tam_scored.csv')
    path = MART / 'tam_scored.csv'
    if not path.exists():
        print('  ! scored mart not written yet'); return 1
    rows = read_csv(path)
    n = len(rows)
    print(f'  rows: {n}')
    required = ['fit_pass', 'acute_need', 'event', 'gravity',
                'forge_total', 'forge_tier', 'forge_rationale',
                'resolve_status', 'clarity_status']
    ok = True
    for col in required:
        missing = sum(1 for r in rows if r.get(col) in (None, '', 'None'))
        flag = '✓' if missing == 0 else '!'
        print(f'  {flag} {col}: {missing} missing')
        if missing > 0: ok = False
    # tier distribution
    tier_dist: dict[str, int] = {}
    for r in rows:
        tier_dist[r['forge_tier']] = tier_dist.get(r['forge_tier'], 0) + 1
    print('\n  tier distribution:')
    for t in ('A', 'B', 'C', 'X'):
        pct = 100 * tier_dist.get(t, 0) / max(n, 1)
        print(f'    {t}: {tier_dist.get(t, 0):>4} ({pct:.1f}%)')
    # top-10 candidates
    rows.sort(key=lambda x: int(x.get('forge_total') or 0), reverse=True)
    print('\n  top 10 FORGE candidates:')
    print('  ' + '─' * 100)
    print(f'  {"total":<6} {"tier":<4} {"state":<6} {"beds":<6} '
          f'{"facility_name":<45} mandate_status')
    print('  ' + '─' * 100)
    for r in rows[:10]:
        nm = (r.get('facility_name') or '')[:43]
        ms = (r.get('mandate_status') or '')[:14]
        print(f'  {r.get("forge_total"):<6} {r.get("forge_tier"):<4} '
              f'{r.get("state"):<6} {r.get("beds") or "?":<6} {nm:<45} {ms}')
    # per-state Tier-A counts
    print('\n  Tier-A counts by state:')
    by_state_a = {}
    for r in rows:
        if r['forge_tier'] == 'A':
            by_state_a[r['state']] = by_state_a.get(r['state'], 0) + 1
    for s in sorted(by_state_a, key=lambda x: -by_state_a[x]):
        print(f'    {s}: {by_state_a[s]}')
    print(f'\n  acceptance: {"PASS" if ok else "FAIL"}')
    return 0 if ok else 1


# ----------------------------------------------------------------------------
STEPS = {'enrich': phase_enrich, 'score': phase_score}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--step', choices=list(STEPS))
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if args.check:
        sys.exit(acceptance())
    if args.step:
        STEPS[args.step](); return
    if not args.all:
        ap.print_help(); return
    for name, fn in STEPS.items():
        fn()
    acceptance()

if __name__ == '__main__':
    main()
