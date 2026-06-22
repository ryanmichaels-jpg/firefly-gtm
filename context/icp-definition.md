# ICP Definition — Firefly (Healthcare beachhead)

## The locked definition
"Healthcare" for Firefly = **U.S. staffed care-delivery facilities where clinical staff and patients face physical-safety risk** — centered on **acute-care hospitals/health systems and behavioral health** — with **workplace-violence prevention** as the organizing acute need and **state mandates + Joint Commission surveys** as the force functions.

## Explicitly EXCLUDED (anti-ICP)
- Payers/insurers, pharma, biotech, medtech HQs, digital-health offices. These are office environments → Firefly's "Corporate" segment, not the safety-pain buyer. Including them pollutes the list.
- Critical-access / rural hospitals (≤25 beds): keep but **deprioritize to Tier 3** (small, low budget, not multi-building).
- Home health / hospice: product mismatch (mobile lone-worker, no site hardware).

## Grain
**One row = one facility** (individual hospital/campus), with `parent_system_id` to roll up to the health system. NOT system-level, NOT building-level (building-level only for the 5-QSO Tier-C recon).

## Geography
Top ~15 mandate states by enacted-mandate strength: WA, CA, NY, NJ, LA, FL, IL, TX, AZ, MA, NC, OR, CO, CT, MD. ~3,000 hospital facilities. See `data/reference/coverage-grid-ranked.csv`.

## Fit tiers
- **Tier 1:** larger acute-care hospitals + behavioral units, multi-building, in a mandate state, with exec sponsorship/budget signals.
- **Tier 2:** mid-size or specialty (e.g., pediatric) acute facilities; review fit.
- **Tier 3 (deprioritized):** critical-access / rural; kept for completeness, scored down.

## Why facility-grain
Mandates are by state (a system spans states with different laws); beds/ED/footprint are per hospital; each map dot = a hospital; deployments land-and-expand building-by-building. Keep `facilities_in_system` as the expansion signal.

## TAM sizing (estimates — flag as such)
~6,100 hospitals nationally; ~3,000 in the 15 states. Total cross-vertical addressable ~70–90k orgs; realistic ICP ~20–35k; act-now sliver low thousands. Sources: AHA, NCES, AHLA public counts.
