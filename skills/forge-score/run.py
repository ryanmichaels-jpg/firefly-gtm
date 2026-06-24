#!/usr/bin/env python3
"""forge-score: apply the F.O.R.G.E. framework to data/mart/tam.csv.

Phases:
  1. enrich        — re-join AHRQ + StandaloneScore by CCN
  2. score         — apply additive FORGE rubric, write tam_scored.csv
  3. diagnostics   — print coverage, per-dim variance share, tier counts, caps

Rubric (FINAL 2026-06-23):
  forge_total = Fit_gate × (Acute + Event + Gravity)   # max 9, min 0
  - Fit is binary (hospital_type + non-excluded ownership; NO bed minimum)
  - Each dimension 0-3 (Gravity floored at 1)
  - Additive, not multiplicative
  - Tier A capped to B if StandaloneScore == 0 (mega-IDN guardrail)

Run:
    python3 skills/forge-score/run.py --all          # enrich + score + diagnostics
    python3 skills/forge-score/run.py --step score
    python3 skills/forge-score/run.py --diagnostics
    python3 skills/forge-score/run.py --check
    python3 skills/forge-score/run.py --test         # 5 spec test cases
"""
from __future__ import annotations
import argparse
import csv
import statistics
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data' / 'raw'
STAGE = ROOT / 'data' / 'staging'
MART = ROOT / 'data' / 'mart'

# ============================================================================
# TUNABLE CONSTANTS — surfaced for re-balancing without touching logic
# ============================================================================

# Per-dimension max scores. Lower GRAVITY_MAX to compress that signal.
ACUTE_MAX = 3
EVENT_MAX = 3
GRAVITY_MAX = 3

# Tier banding on forge_total (max = ACUTE_MAX + EVENT_MAX + GRAVITY_MAX = 9)
TIER_A_THRESHOLD = 7
TIER_B_THRESHOLD = 5
TIER_C_THRESHOLD = 1

# Hard cap: any facility with StandaloneScore == this value is mega-IDN
# and is capped at tier B regardless of forge_total.
STANDALONE_FLOOR = 0
TIER_CAP_FOR_FLOOR = 'B'

# Event deadline-distance curve breakpoints. Each boundary lives in exactly
# ONE bucket (the upper bucket; see _event for resolution).
IN_FORCE_FRESH_YEARS = 2.0   # in-force ≤ this many years ago → Event=3
IN_FORCE_STALE_YEARS = 5.0   # in-force > FRESH and ≤ this → Event=2; > this → Event=1
UPCOMING_NEAR_MONTHS = 12.0  # upcoming ≤ this many months → Event=3
UPCOMING_MID_MONTHS = 24.0   # upcoming > NEAR and ≤ this → Event=2; > this → Event=1

# Federal-exclusion gate. owner_class only — never read the bare "VA" token,
# which collides with the Virginia state code. Mirror skills/standalone-score.
EXCLUDED_OWNER_CLASSES = {
    'Veterans Health Administration',
    'Government - Federal',
    'Department of Defense',
    'Tribal',
}

# Fit-eligible hospital types. Critical Access included so small facilities
# can pass Fit (and surface in tier C). Long-Term, Federal-only types excluded.
FIT_ELIGIBLE_TYPES = {
    'Acute Care Hospitals',
    'Psychiatric',
    'Childrens',
    "Children's",
    'Critical Access Hospitals',
}

# Gravity title classifiers. Order matters: exec is checked before director
# (so "Executive Director" → exec, not director). Each pattern matched as
# substring on a lowercased title.
EXEC_TITLE_PATTERNS = (
    'ceo', 'cfo', 'coo', 'cio', 'cto', 'cmo', 'cno', 'cso', 'ciso', 'cho',
    'chief executive', 'chief financial', 'chief operating', 'chief medical',
    'chief nursing', 'chief security', 'chief safety', 'chief information',
    'chief technology', 'chief compliance', 'chief human',
    'president', 'vice president', ' vp ', 'executive director',
    'administrator',          # in healthcare, "Hospital Administrator" = CEO-equivalent
    'general counsel',
)
DIRECTOR_TITLE_PATTERNS = (
    'director', 'manager', 'head of',
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
    banner('PHASE 1 · ENRICH · AHRQ safety-net proxy fields + StandaloneScore join')
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

    # Join StandaloneScore (run skills/standalone-score/run.py --all first)
    standalone_path = STAGE / 'hgi_50states_scored.csv'
    standalone_cols = ('standalone_score', 'standalone_band',
                       'system_hospital_count', 'system_name',
                       'affiliation_unverified')
    if standalone_path.exists():
        standalone_rows = read_csv(standalone_path)
        by_ccn_st = {r['CCN'].zfill(6): r for r in standalone_rows if r.get('CCN')}
        joined = 0
        for r in mart:
            ccn = (r.get('ccn') or '').zfill(6)
            s = by_ccn_st.get(ccn)
            if s:
                joined += 1
                r['standalone_score'] = float(s['StandaloneScore'])
                r['standalone_band'] = s['Band']
                r['system_hospital_count'] = int(s['System_Hospital_Count'])
                r['system_name'] = s['System'] or None
                r['affiliation_unverified'] = s['Affiliation_Unverified'] == 'True'
            else:
                for c in standalone_cols:
                    r[c] = None
        pct_s = 100.0 * joined / max(len(mart), 1)
        print(f'    StandaloneScore joined: {joined}/{len(mart)} ({pct_s:.1f}%)')
    else:
        for r in mart:
            for c in standalone_cols:
                r[c] = None
        print(f'    StandaloneScore: skipped (run skills/standalone-score/run.py --all)')

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

def _classify_title(title: str) -> str:
    """Returns 'exec', 'director', or 'other'. Exec wins ties
    (so 'Executive Director' → exec, not director)."""
    t = (title or '').lower()
    if not t:
        return 'other'
    if any(kw in t for kw in EXEC_TITLE_PATTERNS):
        return 'exec'
    if any(kw in t for kw in DIRECTOR_TITLE_PATTERNS):
        return 'director'
    return 'other'

def _owner_excluded(owner_class: str) -> bool:
    """Federal-exclusion gate. Reads owner_class ONLY.
    Never collapses the Virginia state code into the VA owner class."""
    return owner_class in EXCLUDED_OWNER_CLASSES

def _fit(r: dict) -> tuple[bool, str]:
    """Binary gate: hospital_type + non-excluded ownership ONLY.
    NO bed minimum, NO mandate requirement. Small + CAH facilities pass.
    """
    htype = (r.get('hospital_type') or '').strip()
    owner_class = (r.get('ownership') or '').strip()  # CMS HGI ownership field
    htype_ok = htype in FIT_ELIGIBLE_TYPES
    owner_ok = not _owner_excluded(owner_class)
    if htype_ok and owner_ok:
        return True, 'PASS'
    reasons = []
    if not htype_ok:  reasons.append(f'type={htype or "?"}')
    if not owner_ok:  reasons.append(f'owner_excluded={owner_class}')
    return False, 'FAIL: ' + ', '.join(reasons)

def _event(r: dict) -> tuple[int, str]:
    """Deadline-distance curve. State-scope mandates score 1-3 based on
    distance to/from effective date. Federal-scope mandate matched → 1.
    No mandate row → 0.
    """
    status = (r.get('mandate_status') or '').strip()
    scope = (r.get('mandate_scope') or '').strip()
    eff = (r.get('effective_date') or '').strip()
    name = (r.get('mandate_name', '') or '')[:40]
    today = date.today()

    if not status:
        return 0, 'no mandate row matched'

    # Federal-scope mandate matched → weak Event signal (not zero).
    if scope and scope != 'state':
        return 1, f'{name} federal-scope mandate'

    # State-scope from here on.
    if status == 'In force' and eff:
        try:
            d = date.fromisoformat(eff)
            years_since = max(0.0, (today - d).days / 365.25)
            if years_since <= IN_FORCE_FRESH_YEARS:
                return 3, f'{name} in force {years_since:.1f}y (≤{IN_FORCE_FRESH_YEARS:g}y, fresh)'
            if years_since <= IN_FORCE_STALE_YEARS:
                return 2, f'{name} in force {years_since:.1f}y (mid)'
            return 1, f'{name} in force {years_since:.1f}y (stale)'
        except ValueError:
            return 1, f'{name} in force (no parseable date)'
    if status == 'Upcoming' and eff:
        try:
            d = date.fromisoformat(eff)
            months_out = (d - today).days / 30.4375
            if months_out <= UPCOMING_NEAR_MONTHS:
                return 3, f'{name} upcoming {months_out:.0f}mo (≤{UPCOMING_NEAR_MONTHS:g}mo)'
            if months_out <= UPCOMING_MID_MONTHS:
                return 2, f'{name} upcoming {months_out:.0f}mo (mid)'
            return 1, f'{name} upcoming {months_out:.0f}mo (far)'
        except ValueError:
            return 1, f'{name} upcoming (no parseable date)'

    # State-scope but missing a usable date OR unrecognized status.
    return 1, f'{name} state-scope, status={status or "?"}, no date'

def _acute_need(r: dict) -> tuple[int, str]:
    """AHRQ safety-net proxy. tier-b-osha overrides this to 3 + lifts
    forge_total when citation-grade OSHA SIR is present. Will be re-tuned
    when contracts + state-OSHA + 990 land.
    """
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
    return 1, 'no AHRQ proxy signal; refines later (OSHA, contracts, 990)'

def _gravity(r: dict) -> tuple[int, str]:
    """Contact seniority ONLY. No bed/size clause. Floor at 1 (never 0):
    a facility with no seed yet is presumed to have *some* admin contact,
    just not yet identified — don't zero the dimension.
    """
    edm_title = (r.get('edm_seed_title') or '').strip()
    edm_name = (r.get('edm_seed_name') or '').strip()
    if not edm_name:
        return 1, 'no edm_seed yet (Gravity floored)'
    cls = _classify_title(edm_title)
    if cls == 'exec':
        return 3, f'exec/C-suite: {edm_title}'
    if cls == 'director':
        return 2, f'director/manager: {edm_title}'
    return 1, f'non-exec: {edm_title or "—"}'

def _tier(total: int, fit_pass: bool, standalone_score: float | None) -> tuple[str, bool]:
    """Returns (tier, was_capped).
    A → B cap applied when StandaloneScore == STANDALONE_FLOOR (mega-IDN).
    """
    if not fit_pass:
        return 'X', False
    if total >= TIER_A_THRESHOLD:
        # mega-IDN guardrail
        try:
            if standalone_score is not None and float(standalone_score) <= STANDALONE_FLOOR:
                return TIER_CAP_FOR_FLOOR, True
        except (TypeError, ValueError):
            pass
        return 'A', False
    if total >= TIER_B_THRESHOLD:
        return 'B', False
    if total >= TIER_C_THRESHOLD:
        return 'C', False
    return 'X', False

def score_row(r: dict) -> dict:
    """Pure scoring of one row. Used by both phase_score and tier-b-osha
    when it lifts Acute Need post-hoc. Returns the dict mutations only."""
    fit_pass, fit_reason = _fit(r)
    if not fit_pass:
        return {
            'fit_pass': False, 'fit_reason': fit_reason,
            'acute_need': 0, 'event': 0, 'gravity': 0,
            'acute_need_evidence': 'fit fail',
            'event_evidence': 'fit fail',
            'gravity_evidence': 'fit fail',
            'forge_total': 0, 'forge_tier': 'X', 'forge_capped_to_b': False,
            'forge_rationale': f'Fit FAIL: {fit_reason}',
        }
    acute, acute_reason = _acute_need(r)
    event, event_reason = _event(r)
    gravity, gravity_reason = _gravity(r)
    total = acute + event + gravity  # ADDITIVE, max 9
    try:
        st = float(r.get('standalone_score')) if r.get('standalone_score') not in (None, '', 'None') else None
    except (TypeError, ValueError):
        st = None
    tier, capped = _tier(total, fit_pass, st)
    return {
        'fit_pass': True, 'fit_reason': 'PASS',
        'acute_need': acute, 'acute_need_evidence': acute_reason,
        'event': event, 'event_evidence': event_reason,
        'gravity': gravity, 'gravity_evidence': gravity_reason,
        'forge_total': total, 'forge_tier': tier, 'forge_capped_to_b': capped,
        'forge_rationale': (
            f'Acute={acute} ({acute_reason}) · '
            f'Event={event} ({event_reason}) · '
            f'Gravity={gravity} ({gravity_reason})'
            + (' · CAPPED A→B (StandaloneScore=0)' if capped else '')
        ),
    }

def phase_score() -> Path:
    banner('PHASE 2 · SCORE · apply additive FORGE rubric')
    rows = read_csv(STAGE / 'forge_01_enrich.csv')
    tier_counts = {'A': 0, 'B': 0, 'C': 0, 'X': 0}
    capped = 0
    for r in rows:
        out_fields = score_row(r)
        r.update(out_fields)
        r['resolve_status'] = 'confirm on call'
        r['clarity_status'] = 'confirm on call'
        r['is_qso_candidate'] = r['ccn'] in QSO_CCNS
        r['scored_at'] = datetime.utcnow().isoformat() + 'Z'
        tier_counts[r['forge_tier']] += 1
        if r.get('forge_capped_to_b'):
            capped += 1
    out = MART / 'tam_scored.csv'
    write_csv(out, rows)
    print(f'  → {out.relative_to(ROOT)} · {len(rows)} rows')
    for t in ('A', 'B', 'C', 'X'):
        pct = 100 * tier_counts[t] / max(len(rows), 1)
        print(f'    tier {t}: {tier_counts[t]:>4} ({pct:.1f}%)')
    if capped:
        print(f'    (of which {capped} were A→B capped by StandaloneScore={STANDALONE_FLOOR})')
    sample = _build_sample(rows)
    sample_path = MART / 'tam_scored_sample.csv'
    write_csv(sample_path, sample)
    print(f'  → {sample_path.relative_to(ROOT)} · {len(sample)} rows (PII redacted)')
    return out

# Hand-picked Tier-C QSOs from Step 4 of the runbook. Selection rationale +
# per-account briefs live in documents/qso-briefs/. These CCNs are flagged
# in the sample mart so reviewers can find them quickly.
QSO_CCNS = {
    '330028',  # Richmond University Medical Center (NY)   std=100, OSHA SIR 2024-12-11
    '330399',  # St Barnabas Hospital (NY)                 std=100, OSHA SIR 2025-09-16 psych nurse assault
    '140015',  # Blessing Hospital (IL)                    std=82,  OSHA SIR 2024-09-28 patient knockdown
    '490022',  # Mary Washington Hospital (VA)             std=71.5, news 2025-03-11 deputy attacked
    '500064',  # Harborview Medical Center (WA)            std=64,  news 2026-02-19 patient arson/assault
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


# ============================================================================
# PHASE 3 — diagnostics
# ============================================================================
def phase_diagnostics() -> int:
    """Print enrichment coverage, per-dimension stats, variance share, tier
    counts, and how many tier-A rows were capped to B by the StandaloneScore
    guardrail."""
    banner('PHASE 3 · DIAGNOSTICS')
    rows = read_csv(MART / 'tam_scored.csv')
    n = len(rows)
    if not n:
        print('  (no rows)'); return 1

    # ---- enrichment coverage (contact seniority) ----
    seniority = {'exec': 0, 'director': 0, 'non-exec/none': 0, 'no-seed': 0}
    for r in rows:
        seed = (r.get('edm_seed_name') or '').strip()
        title = (r.get('edm_seed_title') or '').strip()
        if not seed:
            seniority['no-seed'] += 1; continue
        cls = _classify_title(title)
        if cls == 'exec':       seniority['exec'] += 1
        elif cls == 'director': seniority['director'] += 1
        else:                   seniority['non-exec/none'] += 1
    print('  enrichment coverage (Gravity contact seniority):')
    for k in ('exec', 'director', 'non-exec/none', 'no-seed'):
        v = seniority[k]
        print(f'    {v:>5} {k:<16} ({100*v/n:.1f}%)')

    # ---- per-dimension stats + variance share ----
    def col_floats(name):
        out = []
        for r in rows:
            try:
                out.append(float(r.get(name) or 0))
            except (TypeError, ValueError):
                out.append(0.0)
        return out
    dims = {'Acute Need': col_floats('acute_need'),
            'Event':      col_floats('event'),
            'Gravity':    col_floats('gravity')}
    variances = {k: (statistics.variance(v) if len(v) > 1 else 0.0) for k, v in dims.items()}
    total_var = sum(variances.values()) or 1.0
    print()
    print('  per-dimension stats:')
    print(f'    {"dim":<14} {"mean":>6} {"var":>6}  var_share')
    for k, v in dims.items():
        m = statistics.mean(v) if v else 0
        var = variances[k]
        share = 100 * var / total_var
        print(f'    {k:<14} {m:>6.2f} {var:>6.2f}  {share:>5.1f}%')

    # ---- forge_total distribution ----
    totals = col_floats('forge_total')
    print()
    print(f'  forge_total: min={min(totals):.0f}  median={statistics.median(totals):.1f}  '
          f'mean={statistics.mean(totals):.2f}  max={max(totals):.0f}')

    # ---- tier counts + cap counter ----
    tier_counts = {'A': 0, 'B': 0, 'C': 0, 'X': 0}
    capped = 0
    for r in rows:
        tier_counts[r.get('forge_tier', 'X')] = tier_counts.get(r.get('forge_tier', 'X'), 0) + 1
        if _truthy(r.get('forge_capped_to_b')):
            capped += 1
    print()
    print('  tier counts:')
    for t in ('A', 'B', 'C', 'X'):
        c = tier_counts[t]
        print(f'    tier {t}: {c:>5} ({100*c/n:.1f}%)')
    print(f'    A→B capped by StandaloneScore guardrail: {capped}')

    return 0


# ============================================================================
# TESTS — spec-required scenario assertions
# ============================================================================
def run_tests() -> int:
    """5 scenario tests per Ryan's spec. Pure: no I/O."""
    failures = 0
    def check(name, cond, detail=''):
        nonlocal failures
        ok = bool(cond)
        if ok: print(f'  PASS  {name}')
        else:
            failures += 1
            print(f'  FAIL  {name}{("  -- " + detail) if detail else ""}')

    today = date.today().isoformat()
    # Test 1: sub-250-bed standalone, exec seed, recent state mandate, Acute 3 -> forge 9, tier A
    r1 = {
        'hospital_type': 'Acute Care Hospitals',
        'ownership': 'Voluntary non-profit - Private',
        'beds': '180',                    # sub-250
        'edm_seed_name': 'Jane Smith',
        'edm_seed_title': 'Chief Executive Officer',
        'mandate_status': 'In force',
        'mandate_scope': 'state',
        'effective_date': today,          # fresh in-force
        'hos_highdpp': '1',               # safety-net → Acute=3
        'standalone_score': '100',        # standalone
    }
    o1 = score_row(r1)
    check('T1: sub-250-bed standalone exec mandate Acute3 → forge=9 tier A',
          o1['forge_total'] == 9 and o1['forge_tier'] == 'A',
          detail=f'got forge_total={o1["forge_total"]} tier={o1["forge_tier"]}')

    # Test 2: HCA-sized (StandaloneScore=0) at forge 9 → tier capped at B
    r2 = dict(r1, standalone_score='0')
    o2 = score_row(r2)
    check('T2: StandaloneScore=0 at forge=9 → tier capped to B',
          o2['forge_total'] == 9 and o2['forge_tier'] == 'B' and o2['forge_capped_to_b'],
          detail=f'got forge_total={o2["forge_total"]} tier={o2["forge_tier"]} capped={o2.get("forge_capped_to_b")}')

    # Test 3: Rural CAH, federal-only mandate, CEO seed, Acute 1 -> 1+1+3 = 5, tier B
    r3 = {
        'hospital_type': 'Critical Access Hospitals',
        'ownership': 'Government - Hospital District or Authority',
        'beds': '24',
        'edm_seed_name': 'Mary Doe',
        'edm_seed_title': 'CEO',
        'mandate_status': 'In force',
        'mandate_scope': 'federal',
        'effective_date': '',
        'standalone_score': '100',
    }
    o3 = score_row(r3)
    check('T3: rural CAH federal-only CEO Acute1 → 1+1+3=5 tier B',
          o3['forge_total'] == 5 and o3['forge_tier'] == 'B',
          detail=f'got acute={o3["acute_need"]} event={o3["event"]} gravity={o3["gravity"]} total={o3["forge_total"]} tier={o3["forge_tier"]}')

    # Test 4: facility with no seed → Gravity=1 (floor, not 0)
    r4 = {
        'hospital_type': 'Acute Care Hospitals',
        'ownership': 'Voluntary non-profit - Private',
        'beds': '120',
        'edm_seed_name': '',
        'edm_seed_title': '',
        'mandate_status': '',
        'mandate_scope': '',
        'effective_date': '',
        'standalone_score': '50',
    }
    o4 = score_row(r4)
    check('T4: no edm_seed → Gravity=1 (floored, never 0)',
          o4['gravity'] == 1,
          detail=f'got gravity={o4["gravity"]}')

    # Test 5: federal-owned (VA system facility) → excluded (tier X) regardless of mandate
    r5 = {
        'hospital_type': 'Acute Care Hospitals',
        'ownership': 'Veterans Health Administration',
        'beds': '400',
        'edm_seed_name': 'John Doe',
        'edm_seed_title': 'CFO',
        'mandate_status': 'In force',
        'mandate_scope': 'state',
        'effective_date': today,
        'hos_highdpp': '1',
        'standalone_score': '100',
    }
    o5 = score_row(r5)
    check('T5: federal-owned → tier X regardless of mandate',
          o5['forge_tier'] == 'X' and not o5['fit_pass'],
          detail=f'got fit_pass={o5["fit_pass"]} tier={o5["forge_tier"]}')

    # Bonus: state code "VA" must NOT collide with owner_class VA
    r6 = {
        'hospital_type': 'Acute Care Hospitals',
        'ownership': 'Voluntary non-profit - Private',   # ← not federal
        'state': 'VA',                                    # ← Virginia
        'beds': '200',
        'edm_seed_name': 'A B', 'edm_seed_title': 'CEO',
        'mandate_status': 'In force', 'mandate_scope': 'federal',
        'effective_date': '',
        'standalone_score': '50',
    }
    o6 = score_row(r6)
    check('Label hygiene: state=VA must not trigger owner-class VA exclusion',
          o6['fit_pass'],
          detail=f'got fit_pass={o6["fit_pass"]}')

    print()
    if failures:
        print(f'  {failures} FAILED'); return 1
    print('  all tests passed'); return 0


# ----------------------------------------------------------------------------
STEPS = {'enrich': phase_enrich, 'score': phase_score, 'diagnostics': phase_diagnostics}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--step', choices=list(STEPS))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--diagnostics', action='store_true')
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()
    if args.test:
        sys.exit(run_tests())
    if args.check:
        sys.exit(acceptance())
    if args.diagnostics:
        sys.exit(phase_diagnostics())
    if args.step:
        STEPS[args.step](); return
    if not args.all:
        ap.print_help(); return
    for name, fn in STEPS.items():
        fn()
    acceptance()

if __name__ == '__main__':
    main()
