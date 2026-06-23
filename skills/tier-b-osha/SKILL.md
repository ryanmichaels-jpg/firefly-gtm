# tier-b-osha — OSHA Severe Injury Report enrichment

Reads `data/raw/osha-sir/January2015toOctober2025.csv` (the federal OSHA SIR bulk download, 105K records, 11 years), filters to NAICS-622 (healthcare) in our priority federal-OSHA states, fuzzy-matches `Employer` to mart `facility_name`, populates `osha_*` columns + optionally lifts FORGE Acute Need from proxy to citation-grade.

## Why this signal matters

OSHA Severe Injury Reports are federally-mandated employer self-reports of severe workplace injuries (hospitalization, amputation, loss of eye) within 24 hours of occurrence. For hospitals, the most common SIR triggers are:
- Staff assaulted by a patient (the WPV pattern)
- Needle-stick / sharps injuries
- Patient-handling musculoskeletal injuries
- Workplace violence-related hospitalizations

A facility with **multiple SIR records in the last 24 months** has demonstrated WPV / safety exposure. That's a direct citation-grade Acute Need signal — replaces the AHRQ safety-net *proxy* with documented federal evidence.

## Source

**OSHA Severe Injury Report** dataset
- URL: https://www.osha.gov/severe-injury-reports/data
- Bulk download: `January2015toOctober2025.csv` inside the published ZIP
- Refresh cadence: periodic (last refresh Oct 2025 at time of build)
- Cost: $0
- License: public domain (federal data)

**Important constraint**: federal OSHA jurisdiction **only**. State-plan states (CA, WA, OR, MD, NC, and 17 others) are NOT in this dataset. They report to state OSHA agencies with separate enforcement portals (each one slightly different). Of our 15 priority states:

- ✅ Federal-OSHA (10): TX, NY, NJ, LA, FL, IL, AZ, MA, CT, CO — full coverage
- ❌ State-plan (5): CA, WA, OR, MD, NC — would need separate scrapes

QSO 1 (Harborview, WA) won't get an OSHA tag from this dataset — the Feb 14, 2026 ED attack happened in a state-plan state.

## Schema (relevant columns from OSHA SIR)

| Column | What it is |
|---|---|
| `ID` / `UPA` | OSHA's unique identifier for the report |
| `EventDate` | Incident date (M/D/YYYY format) |
| `Employer` | Hospital legal/dba name |
| `Address1`, `City`, `State`, `Zip` | Incident location |
| `Primary NAICS` | Industry code (we filter to `622*`) |
| `Hospitalized`, `Amputation`, `Loss of Eye` | Boolean injury severity |
| `Nature`, `NatureTitle` | Injury nature codes + readable label |
| `Part of Body`, `Part of Body Title` | Body part affected |
| `Event`, `EventTitle` | Triggering event codes (workplace violence = code 7) |
| `Source`, `SourceTitle` | What caused the injury (e.g., "Person — patient") |
| `Final Narrative` | Free-text incident description |
| `Inspection` | Linked OSHA inspection number if any |

## Phases

### Phase 1 — extract (~10 sec, local)
Parse the 57MB SIR CSV. Filter to:
- `Primary NAICS` starts with `622`
- `State` in our 10 priority federal-OSHA states
- `EventDate` ≥ 2024-06-22 (last 24 months)

Output: `data/staging/osha_filtered.csv` with ~193 incidents (per current data).

### Phase 2 — match (~5 sec, local)
For each filtered incident, fuzzy-match `Employer` against mart `facility_name` scoped to that state. Confidence = name-similarity (Jaccard + sequence). Threshold ≥ 0.6.

Output: `data/staging/osha_matches.csv` with `(ccn, evidence_url, evidence_date, evidence_nature, evidence_event, count_24m, confidence)`.

### Phase 3 — merge (~5 sec, local)
For each matched CCN:
- Aggregate count of incidents in last 24 months
- Write `osha_severe_injury_count_24mo`, `osha_first_evidence_url`, `osha_first_evidence_date`, `osha_evidence_natures` (comma-separated injury types)
- **Lift Acute Need to 3** when `count_24m ≥ 1` (one SIR is one incident too many)
- Recompute `forge_total` (Acute × Event × Gravity) + re-tier
- Update `acute_need_evidence` text to point to OSHA

## Run

```bash
python3 skills/tier-b-osha/run.py --all
python3 skills/tier-b-osha/run.py --phase extract
python3 skills/tier-b-osha/run.py --phase match
python3 skills/tier-b-osha/run.py --phase merge
```

## Honest expectations

Based on counts:
- 1,380 NAICS-622 incidents in our 10 federal-OSHA priority states (Jan 2015 – Oct 2025)
- **193 in the last 24 months** — these are the rows that drive Acute Need lift
- Match rate after fuzzy: realistic **80–150 facilities** matched (some employers don't appear in CMS HGI; some have name divergence too wide for fuzzy)

For the 5 priority state-plan states (CA, WA, OR, MD, NC), there's no OSHA SIR signal in this dataset. We document that as a known gap; future work would scrape the 5 state portals separately.

## What this skill does NOT do

- Doesn't pull state-OSHA enforcement data (5 of our 15 states are state-plan)
- Doesn't pull general OSHA citations (only Severe Injury Reports here; full inspection data is a separate file at OSHA enforcement APIs)
- Doesn't classify WPV-specific incidents vs. all severe injuries (the `EventTitle` field has codes; future enhancement could narrow to assault-related)
