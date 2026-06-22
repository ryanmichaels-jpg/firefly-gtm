# CLAUDE.md — Firefly GTM Engine (TAM build + dashboard)

> This file is the project brain. Read it (and everything in `context/`) at the start of every session before running any skill or pipeline step.

## Objective
Build a real, queryable TAM of U.S. **hospitals** in the priority mandate states, enrich each with the signals that predict a Qualified Sales Opportunity (QSO), score them against Firefly's **F.O.R.G.E.** framework, and render the result as an interactive hub (US map + Clay-style list). Deliverable doubles as (a) proof we can source 5 real QSOs now and (b) the v1 of the engine that scales to the next 500.

## Scope (locked)
- **Vertical:** Healthcare = care-delivery providers (acute-care hospitals + behavioral health). Exclude payers/pharma/biotech/medtech HQ (those are "Corporate").
- **Geography:** the **top ~15 mandate states** by enacted-mandate strength (from the ranked Coverage Grid): WA, CA, NY, NJ, LA, FL, IL, TX, AZ, MA, NC, OR, CO, CT, MD. ~3,000 hospital facilities.
- **Grain:** one row = one **facility** (individual hospital/campus), with `parent_system_id` to roll up to the health system. NOT system-level, NOT building-level (building-level only in Tier-C recon for the 5 QSOs).

## Firefly context (1-paragraph)
Firefly = unified AI + IoT physical-safety platform. **Ember** (software: digital twin, AI detection/response, EMS integration, mass notification, mustering) + **Lattice** (hardware: panic buttons, gunshot detection, resilient no-IT private-network gateway). Job-to-be-done: "Detect → Locate → Alert → Respond." Sells into mandate-driven verticals. **Primary moat to reinforce: trusted-standard / regulatory** (certified, validated, embedded). See `context/`.

## NON-NEGOTIABLE RULE: one-offs, not sequences
Firefly's core GTM insight is that **email sequencing does not work** in these segments; **high-context one-offs do**. Do NOT build email-blast/sequencing flows. The pipeline ends by routing scored accounts to a rep worklist for human-finished one-offs. (Ignore the cold-email/Smartlead/deliverability skills from any forked repo.)

## F.O.R.G.E. (the qualification framework)
QSO is a *call-stage* bar; signals are *pre-call* proxies. Detectability:
- **Fit (gate):** care-delivery facility + product-relevant initiative. Detectable.
- **Outcome / Acute Need:** a real event (incident OR structural change w/ endpoint) — NOT dissatisfaction. Detectable.
- **Resolve / No-Inaction:** earned on the call. NOT scored pre-call.
- **Gravity:** org-level sponsor + budget + EDM access. Partially detectable.
- **Event / Force Function:** a deadline. Highly detectable (mandates).
Score Fit as a gate → rank by Acute Need × Event × Gravity. **Never score Resolve/Clarity** (leave as "confirm on call").

## CORRECTED SEED RECIPE (use this order — learned from the WA mock)
Do NOT seed from NPPES first (it returns junk names, staffing agencies, duplicates, and critical-access rurals; no beds/ED/system). Order:
1. **CMS Hospital General Information** (data.cms.gov) → primary clean hospital list + `ccn`, hospital_type, ownership, **ED flag**.
2. **Dedup / entity-resolution** → key on CCN + name+address, NOT NPI (NPPES has many subpart NPIs per facility).
3. **AHRQ Compendium of U.S. Health Systems** → `parent_system` + `facilities_in_system`.
4. **CMS POS / HCRIS** → certified `beds`.
5. **NPPES** → enrich addresses/identifiers + free `edm_seed` from `authorized_official` (CEO/CFO/CIO name + phone). Prefer the **DBA** (`other_names`) for `facility_name`, not the legal name.
6. **U.S. Census Geocoder** → `lat`/`lng` (free, batch ≤10k).
7. **Mandate-join** against `data/reference/mandates.csv` with status logic (below).
8. **Tier** by bed count + hospital type → deprioritize Critical Access (≤25 beds) as Tier 3 (keep, don't delete).

### Mandate-status logic (don't use a raw countdown)
Mandates already in force break a `days_to_deadline` countdown (goes negative). Use `mandate_status` ∈ {Upcoming, In force, Enforcement}. WA RCW 49.19 is **In force** → sell on *enforcement risk / compliance now*, not "beat the clock." Future-dated mandates → countdown + "beat the clock" angle.

## Field → source map (Tier A = all ~3,000, free)
| Field | Source | Notes |
|---|---|---|
| name (DBA), legal_name, ccn, hospital_type, ownership, has_ED | CMS HGI | primary seed |
| address, city, state, zip, edm_seed | NPPES | prefer DBA name |
| parent_system, facilities_in_system | AHRQ Compendium | roll-up |
| beds | CMS POS/HCRIS | ICP-fit / ACV |
| has_behavioral_unit | CMS POS / SAMHSA | |
| lat, lng | Census geocoder | free |
| mandate_*, days_to_deadline/status | mandates.csv | local join |
Tier B/C (curated subset + 5 QSOs only): footprint (Maps), tech_stack/incumbent (Apify+vendor case studies), contract_expiry (SAM.gov/awards × testimonials), contacts/EDM (Prospeo/Apollo + 990s + IAHSS), recon/num_entrances (Street View).

## Depth gradient + COST GUARDRAILS
- **Tier A (all ~3,000):** free sources only (CMS/NPPES/AHRQ/Census/mandates). Single-digit $.
- **Tier B (~300–400 curated):** Maps footprint + tech-stack + contacts. Metered.
- **Tier C (5 QSOs):** Apify + full contact enrichment + Street View recon, hand-validated.
- **Apify and paid contact lookups run ONLY on the 5 QSOs (Tier C).** Never enrich all 3,000 with paid per-record tools. QA a sample before any at-scale paid run.

## Guardrails
- **Never fabricate.** If a field is unknown, leave null + set `needs_review`. No invented vendors, beds, or contacts.
- **Every signal carries a `*_source_url`.** Any cell must be auditable in one click.
- **Public data only.** No PHI. Crawl only public org-level pages (safety/board/leadership). LinkedIn scraping is ToS-sensitive — prefer Apollo/official APIs.
- **Tech-stack signals:** flag replace-layer (duress/notification/incident = green flag) vs integrate-layer (cameras/VMS/access = neutral). Don't reward integrate-layer presence.

## Schema
**Mart — `data/mart/tam.csv`** (one row per facility): identity (account_id, ccn, facility_name, parent_system, parent_system_id, ownership_type, hospital_type, sub_segment) · footprint (address, city, state, zip, lat, lng, beds, building_count, num_entrances, has_ED, has_behavioral_unit, facilities_in_system) · mandate (mandate_applies, mandate_name, mandate_type, mandatory_vs_permissive, effective_date, mandate_status, days_to_deadline, source_url) · acute_need (incident_flag, incident_type, incident_date, osha_flag, wpv_program_mentioned, source_url) · gravity (exec_hire_flag/title/date, board_safety_mention, budget_signal, funded_flag, source_url) · tech/incumbent (incumbent_duress_vendor, incumbent_notification_vendor, incumbent_vms_vendor, competitor_follower_flag, contract_start, contract_expiry, contract_evidence_url) · committee (edm_name/title/email/linkedin, champion_name/title/email/linkedin, reachability_score) · FORGE (fit_pass, acute_need, event, gravity, total, tier, rationale, resolve_status, clarity_status) · outreach (recommended_channel, one_off_draft_ref, outreach_status, is_qso_candidate) · meta (enrichment_tier, confidence, last_enriched_at, needs_review, facility_tier).

**Raw (one-to-many per account):** `data/raw/` → testimonials.csv, contracts.csv, jobposts.csv, news.csv, rfps.csv, techstack.csv, contacts.csv; `data/raw/crawl/` (html2text dumps). Pattern: raw → resolve/derive → write distilled answer + evidence_url to mart.

## Folder layout
```
data/raw/ · data/staging/ · data/mart/tam.csv · data/reference/mandates.csv · documents/
context/ (profile, icp-definition, signal-library, positioning, competitor-radar, personas/)
skills/ (seed-pull, geocode, mandate-join, enrich-*, forge-score, build-dashboard, + Karl's account-research/icp-scoring/weekly-update)
dashboard/ (static app reading data/mart/tam.csv: US map view + Clay-style list view)
```

## Acceptance criteria (per run)
- Row count ≈ expected hospital count for the 15 states; no duplicates (CCN-unique).
- 100% of Tier-A rows have name (DBA), state, mandate_status, lat/lng.
- 0 fabricated values; unknowns = null + needs_review.
- 5 QSOs fully enriched (contacts + recon + one-off draft) and is_qso_candidate=TRUE.
- Stop-and-confirm before any paid (Apify/contact) run.
