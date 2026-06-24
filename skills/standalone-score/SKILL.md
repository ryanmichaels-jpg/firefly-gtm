# standalone-score — rank facilities by independence from large health systems

Adds a continuous 0–100 `StandaloneScore` keyed on system size. Built to give the GTM engine a real discriminator above the FORGE rubric, which bunches most large urban hospitals at the same total.

Designed as a **standalone** scoring component — own column, own band — so it can later be blended into a weighted composite (e.g. `0.4 × Standalone + 0.4 × FORGE_normalized + 0.2 × Reach`).

## Formula

```
StandaloneScore = max(0, 100 - SCORE_DECAY × log2(N))
```

Where `N` = the parent system's total hospital count (from AHRQ Compendium 2023). Constants live at the top of `run.py`:

| Constant | Value | What it controls |
|---|---|---|
| `SCORE_DECAY` | 18 | Slope of the decay. Higher = bigger systems punished faster. |
| `PRIMARY_CUTOFF` | 40 | Band boundary. Score ≥ 40 → Primary, < 40 → Deprioritized. |

Reference points: N=1 → 100, N=2 → 82, N=10 → 40, N=50 → 0.

## Gates (applied after the formula)

1. **Federal exclusion** — `StandaloneScore = 0`, `Excluded = True`. Triggers on:
   - Hospital Ownership ∈ {Veterans Health Administration, Government - Federal, Department of Defense, Tribal}
   - Or parent system name contains "Veterans Health Administration" / "Indian Health Service"
2. **Unknown affiliation** — if CCN isn't in the AHRQ linkage file, treat as `N=1` (score 100) but set `Affiliation_Unverified = True`. These get the standalone score but are flagged for human confirmation rather than silently trusted.

## Bands

| Score | Band |
|---|---|
| ≥ 40 | Primary |
| < 40 | Deprioritized |
| federal-gated | Excluded |

## How to run

```bash
# Run assertion tests (12 tests, no network)
python3 skills/standalone-score/run.py --test

# One-state sample (writes data/staging/standalone_scored_WA.csv)
python3 skills/standalone-score/run.py --state WA

# Full 50 states + DC (writes data/staging/hgi_50states_scored.csv)
python3 skills/standalone-score/run.py --all
```

Free, stdlib only, ~5 seconds for the 50-state run.

## Output schema

`data/staging/hgi_50states_scored.csv` — sorted by `StandaloneScore` desc, then `System_Hospital_Count` asc, then `Name` asc.

| Column | Type | Source |
|---|---|---|
| CCN | str (zero-padded 6) | CMS HGI |
| Name, City, State, Type, Ownership | str | CMS HGI |
| System | str | AHRQ Compendium `health_sys_name` |
| System_Hospital_Count | int | AHRQ Compendium `hosp_cnt` (defaults to 1 if unmatched) |
| StandaloneScore | float (0–100, 2dp) | computed |
| Band | enum | Primary / Deprioritized / Excluded |
| Excluded | bool | True if federal-gated |
| Affiliation_Unverified | bool | True if CCN not in AHRQ linkage |

## Honest data limitations

- **AHRQ Compendium is 2023 vintage.** New systems / acquisitions after 2023 won't be picked up. Verify before sending.
- **Public hospital districts have high Unverified rates** (~74% in WA). Most are genuinely standalone, but AHRQ doesn't track informal public-district networks. They default to N=1, score=100, flagged Unverified.
- **Tiny critical-access hospitals dominate the top.** Score=100 doesn't mean "good QSO" — it means "no parent system." Blend with size + FORGE downstream to find the actual sweet spot (mid-IDN, 200+ beds, N=2–10).

## Why this exists

FORGE alone bunches dozens of large hospitals at the same `forge_total=27` ceiling because Acute/Event/Gravity each cap at 3 and the maxes co-occur in urban safety-net facilities. Adding StandaloneScore introduces a continuous, log-decayed dimension keyed on a signal FORGE doesn't touch — independence from large IDNs — which matches Firefly's land-and-expand reality as a new healthcare entrant: easier wins in standalones + mid-IDNs, longer cycles in HCA / CommonSpirit / Ascension.
