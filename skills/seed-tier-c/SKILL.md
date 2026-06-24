# seed-tier-c — build the Firefly TAM (Tier-C broad seed, all 50 + DC, all free)

Runs the corrected CMS-first seed recipe end-to-end. Produces `data/mart/tam.csv` — one row per hospital facility across all 50 states + DC (~5,362 facilities). v1 was locked to 15 priority mandate states; v2 expanded to surface HARD-GATE incidents nationwide.

**Tier convention** (v2 flipped letters): **Tier C = broad seed** (this skill), Tier B = curated middle, Tier A = the 5 QSOs.

## What it does

Eight ordered, idempotent steps. Each step writes a staging file to `data/staging/`. Re-running picks up from the latest cached output.

| # | Step | Input | Output |
|---|---|---|---|
| 1 | Filter CMS HGI to 15 states | `data/raw/cms-hgi/Hospital_General_Information_2026-05-13.csv` | `data/staging/01_cms_hgi.csv` |
| 2 | Dedup on CCN + name+address | 01 | `data/staging/02_dedup.csv` |
| 3 | Join AHRQ Compendium (parent_system, facilities_in_system) | 02 + `data/raw/ahrq-compendium/*` | `data/staging/03_ahrq.csv` |
| 4 | Join CMS POS (certified beds, has_behavioral_unit) | 03 + `data/raw/cms-pos/*` | `data/staging/04_pos.csv` |
| 5 | NPPES enrichment (DBA, physical addr, edm_seed) | 04 + NPPES API | `data/staging/05_nppes.csv` |
| 6 | Census batch geocode (lat, lng) | 05 + Census API | `data/staging/06_geocode.csv` |
| 7 | Mandate-join with status logic | 06 + `data/reference/mandates.csv` | `data/staging/07_mandate.csv` |
| 8 | Tier classification + final mart | 07 | `data/mart/tam.csv` |

## Priority states (locked in CLAUDE.md)

WA, CA, NY, NJ, LA, FL, IL, TX, AZ, MA, NC, OR, CO, CT, MD — expected ~2,354 facilities from CMS HGI.

## How to run

```bash
# full pipeline, end-to-end
python3 skills/seed-tier-c/run.py --all

# just one step (for verification / re-runs)
python3 skills/seed-tier-c/run.py --step 1

# skip the NPPES + geocode network steps (offline rerun for tier logic etc.)
python3 skills/seed-tier-c/run.py --skip nppes,geocode
```

## Acceptance criteria (CLAUDE.md, locked)

- Row count is in expected range for 15 states (~2,300–3,000)
- `ccn` is unique
- 100% of Tier-A rows have `facility_name`, `state`, `mandate_status`, `lat`, `lng`
- 0 fabricated values — unknowns are `null` with `needs_review=TRUE`
- Each derived field carries a `*_source_url` where applicable

## What this skill does NOT do

- Tier-B curation (~300–400 with footprint + tech-stack + contacts) — separate skill
- Tier-C 5-QSO enrichment (Apify + paid contact lookups) — separate skill, paid, stop-and-confirm
- FORGE scoring — runs on the output of this skill
- Dashboard build — reads `data/mart/tam.csv`

## Cost

Single-digit dollars at most (CMS, AHRQ, NPPES, Census are free; minor compute only). NPPES rate-limit slows Step 5 to ~15 min wall-clock; that's the only constraint.

## Failure modes + recovery

- **NPPES rate-limited (429):** script backs off and retries; cached responses survive re-runs.
- **Census 502:** script retries on the failed batch with cleaned addresses.
- **AHRQ no-match:** expected ~2% (military, Kaiser, etc.) — left null, `needs_review` flagged.
- **Mandate status ambiguous:** dropped rows logged to `data/staging/mandate_dropped.csv` for human review.
