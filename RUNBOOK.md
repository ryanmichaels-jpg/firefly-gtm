# RUNBOOK — building the Firefly TAM + dashboard in Claude Code

Read `CLAUDE.md` and all of `context/` first. This is the ordered, decomposed runbook. Do NOT one-shot it. Verify after each step.

## 0. Sanity check
Prompt: "Read CLAUDE.md and everything in context/. Summarize the scope, schema, and the corrected CMS-first seed recipe, then list the runbook steps." Confirm the context loaded.

## 1. Seed (Tier A, free, all ~3,000)
1. Pull **CMS Hospital General Information** for the 15 states → clean hospital list + ccn, hospital_type, ownership, ED flag.
2. **Dedup** on CCN + name+address (NOT NPI).
3. **AHRQ Compendium** → parent_system + facilities_in_system.
4. **CMS POS/HCRIS** → certified beds.
5. **NPPES** → addresses, identifiers, edm_seed (authorized_official); prefer DBA name.
6. **Census geocoder** → lat/lng.
7. **Mandate-join** against `data/reference/mandates.csv` with status logic (Upcoming/In force/Enforcement).
8. **Tier** by beds + type (deprioritize critical-access).
Output: `data/mart/tam.csv`. Acceptance: no dupes (CCN-unique), 100% have name/state/lat/lng/mandate_status, 0 fabricated values.

## 2. Score (Tier A)
Compute FORGE (Fit gate → Acute Need × Event × Gravity; leave Resolve/Clarity as "confirm on call"). Write forge_total, forge_tier, rationale.

## 3. Curate Tier B (~300–400)
Top by beds + mandate proximity per state. Enrich: footprint (Maps), tech-stack/incumbent (Apify job posts + vendor case studies), contract-expiry (SAM.gov awards × testimonials). Classify replace vs integrate.

## 4. The 5 QSOs (Tier C) — STOP-AND-CONFIRM before paid runs
Hand-pick 5. Full contact/EDM (Prospeo + 990s + IAHSS), Street View recon (num_entrances), and a human-written one-off. Set is_qso_candidate=TRUE. **This is the only place Apify + paid contact lookups run.**

## 5. Dashboard
1. In Claude design: run the v2 combined prompt + attach `data/mart/tam_sample.csv`.
2. In Claude Code: "Build `dashboard/` as a static app reading `data/mart/tam.csv`, matching this mock, per the data contract in CLAUDE.md."
3. Export tam.csv → tam.json for the dashboard.

## 6. Refresh (the "learn every week" loop)
Re-run the signal sweep (mandates, RFPs, incidents, exec hires) weekly; feed outcomes back to re-weight scoring.

## Cost guardrail
Tier A free for all ~3,000 (single-digit $). Paid enrichment only on the 5 QSOs. QA a sample before any at-scale paid run.

## Never
Commit `.env` or contact/PII data. Fabricate values (unknown = null + needs_review). Build email sequences (one-offs only). Reward integrate-layer tech presence. Seed from NPPES first.
