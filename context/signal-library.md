# Signal Library — Firefly

Structured signal data lives in `data/reference/signal-sources.csv`, `mandates.csv`, and `coverage-grid.csv`. This file is the logic layer.

## QSO = call-stage bar; signals = pre-call proxies
F.O.R.G.E. is what Sam reviews after a conversation. Signals predict which accounts will clear it. Detectability:
- **Fit (gate):** care-delivery facility + product-relevant initiative. **Detectable.**
- **Outcome / Acute Need:** a real event (incident OR structural change with an endpoint), NOT dissatisfaction. **Detectable.**
- **Resolve / No-Inaction:** earned on the call. **Do NOT score pre-call.**
- **Gravity:** org sponsor + budget + EDM access. **Partially detectable.**
- **Event / Force Function:** a deadline. **Highly detectable** (mandates).
Score Fit as a gate → rank by Acute Need × Event × Gravity. Leave Resolve/Clarity as "confirm on call."

## Signal types (all public / firewall-safe), by FORGE pillar
- **Mandate / regulatory clock** (Event) — LegiScan/NCSL + `mandates.csv`.
- **Incident** — news, assault/shooting (Acute Need).
- **OSHA citation / DOH violation** — OSHA enforcement data (Acute Need).
- **RFP / procurement posted** — SAM.gov, Bonfire, GovSpend (Event + budget).
- **Contract expiry / incumbent EOL** — awards × competitor testimonials (structural change).
- **Exec hire** — new VP Security / Chief Safety / EM Director / WPV Coordinator (Gravity + intent).
- **Funding / grant / bond** — grant DBs, board minutes (budget).
- **Competitor-follower / engagement** — engaged with CENTEGIX/Strongline on LinkedIn (intent). JD-mandated.
- **Job posting w/ vendor mention** — tech-stack + intent.
- NOT feasible: real-time 911/PSAP dispatch volume (not a public feed) — do not build it.

## Tech-stack signal: replace vs integrate
Tag every detected vendor by layer:
- **Replace-layer = green flag:** duress/panic, standalone notification, incident/PSIM.
- **Integrate-layer = neutral:** cameras/VMS (Genetec, Exacq, Milestone, Avigilon), access control, PA. Do NOT reward integrate-layer presence.

## Mandate-status logic (not a raw countdown)
Use `mandate_status` ∈ {Upcoming, In force, Enforcement}. In-force mandates (e.g., WA RCW 49.19) → sell on enforcement risk, not "beat the clock." Future-dated → countdown + "beat the clock."

## Corrected seed recipe (CMS-first — learned from the WA mock)
Do NOT seed from NPPES (junk names, duplicates, critical-access, no beds/ED/system). Order:
1. CMS Hospital General Information → clean list + ccn, hospital_type, ownership, ED flag.
2. Dedup on CCN + name+address (NOT NPI).
3. AHRQ Compendium → parent_system + facilities_in_system.
4. CMS POS/HCRIS → certified beds.
5. NPPES → addresses, identifiers, free EDM seed (authorized_official). Prefer the DBA name.
6. Census geocoder → lat/lng (free).
7. Mandate-join with status logic.
8. Tier by bed count + type → deprioritize critical-access.

## Depth gradient + cost guardrail
- Tier A (all ~3,000): free sources only. Single-digit $.
- Tier B (~300–400 curated): Maps footprint + tech-stack + contacts. Metered.
- Tier C (5 QSOs): Apify + full contact + Street View recon, hand-validated.
- Paid tools (Apify, contact lookups) run ONLY on the 5 QSOs.
