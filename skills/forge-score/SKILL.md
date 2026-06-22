# forge-score — apply the F.O.R.G.E. framework to data/mart/tam.csv

Scores every facility in `data/mart/tam.csv` on the F.O.R.G.E. qualification framework and writes `data/mart/tam_scored.csv` with FORGE columns added.

## The framework (locked in CLAUDE.md)

Score **Fit as a gate** → rank by **Acute Need × Event × Gravity** (each 0–3, product 0–27).
**Never** score Resolve/Clarity — those are *call-stage* qualifications. Leave as `confirm on call`.

## Scoring rubrics (Tier-A)

### FIT (boolean gate)

**PASS** if **all** of:
- `hospital_type ∈ {Acute Care Hospitals, Psychiatric, Childrens}` (no critical-access-without-ED, no specialty-only)
- `has_ED` OR `has_behavioral_unit` OR `beds ≥ 50`
- `mandate_status` is set (any value)

**FAIL** → `forge_total=0, forge_tier=X`, excluded from ranking.

### EVENT (mandate clock, 0–3)

- **0**: no state-specific mandate (federal-only fallback — FL)
- **2**: state-specific **Upcoming** with deadline > 12 months out (low urgency)
- **3**: state-specific **In force** OR Upcoming ≤ 12 months (enforcement-risk-now OR beat-the-clock)

### ACUTE NEED (incident / structural change, 0–3)

Tier-A uses **research-backed AHRQ proxies** (not direct incident data — that comes in Tier-B):

- **1 (default)**: no proxy signals
- **2**: `hos_majteach=1` (major teaching hospital) OR `has_behavioral_unit=True` — proxies for higher acuity / WPV exposure
- **3**: `hos_highdpp=1` (high DSH share) OR `hos_highuc=1` (high uncompensated care) — urban safety-net hospitals, documented in BLS/NIOSH data as having elevated WPV incident rates

**Important**: these are clearly labeled proxies, not direct citations. The `acute_need_evidence` column states the source. Tier-B enrichment (OSHA SIR, IRS 990 narrative, news incidents) will lift these to citation-grade signal in a separate skill.

### GRAVITY (sponsor + budget + EDM access, 0–3)

- **0**: no `edm_seed_name` OR exec_title_score=0 (no detectable buyer)
- **1**: `edm_seed_name` exists, non-exec title (Social Worker, RN, etc.)
- **2**: `edm_seed_name` has exec title (CEO/CFO/COO/CIO/President/Administrator)
- **3**: exec-title `edm_seed_name` **AND** `beds ≥ 250` **AND** in a multi-facility system

### FORGE_TIER cutoffs

- **A** (priority): total ≥ 12
- **B**: total 6–11
- **C**: total 1–5
- **X**: total = 0 OR fit_fail (excluded)

## How to run

```bash
python3 skills/forge-score/run.py --all
python3 skills/forge-score/run.py --step enrich
python3 skills/forge-score/run.py --step score
python3 skills/forge-score/run.py --check
```

## Outputs

- `data/staging/forge_01_enrich.csv` — mart + AHRQ proxy fields appended
- `data/mart/tam_scored.csv` — full mart with FORGE columns (LOCAL ONLY — has edm_seed contact info, gitignored)
- `data/mart/tam_scored_sample.csv` — committable sample (contact fields redacted)

## Acceptance criteria

- 100% of rows have `fit_pass`, `acute_need`, `event`, `gravity`, `forge_total`, `forge_tier`, `forge_rationale` populated
- 0 fabricated values — proxy signals are explicitly labeled in `acute_need_evidence`
- Tier-A distribution is reasonable (expect ~5–15% Tier A, ~20–30% Tier B, rest C/X)
- Resolve/Clarity columns stay as the literal string `confirm on call`

## What this skill does NOT do

- Pull OSHA Severe Injury Reports (Tier-B, separate skill — friction with discovery URLs)
- Fetch IRS 990 narrative text for WPV mentions (Tier-B, requires IRS XML S3 fetch + parser)
- Pull news incidents (Tier-B, requires per-facility queries — only realistic for ~300 curated)
- Score Resolve / Clarity (those are call-stage, never pre-call)
