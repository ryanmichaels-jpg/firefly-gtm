# Firefly Revenue Intel — a working GTM engine for the Healthcare WPV vertical

A live, queryable TAM of **~5,362 U.S. hospitals across all 50 states + DC**, scored against Firefly's **F.O.R.G.E.** framework, surfaced as a static dashboard, and refined down to **5 hand-picked QSOs** with research briefs + one-off email drafts.

Built end-to-end from public data sources. **Total spend ≈ $5.** The kind of thing a GTM Engineer ships in week one.

---

## What you can do with this repo in 90 seconds

| | Link |
|---|---|
| **Live dashboard** (US map, Clay-style accounts list, FORGE rankings) | [dashboard-steel-omega-96.vercel.app](https://dashboard-steel-omega-96.vercel.app) |
| **5 named QSOs** with full briefs + one-off email drafts | [documents/qso_briefs.md](documents/qso_briefs.md) |
| **The pipeline source-map** (regenerable SVG) | [diagrams/source-map.svg](diagrams/source-map.svg) |
| **What got scored on what** (methodology) | [skills/forge-score/SKILL.md](skills/forge-score/SKILL.md) |
| **Why we don't seed from NPPES** | [skills/seed-tier-c/SKILL.md](skills/seed-tier-c/SKILL.md) |
| **The hard scope rules (no email sequences, no fabrication, no PHI)** | [CLAUDE.md](CLAUDE.md) |

---

## The five QSOs — and why each one

Ranked by **StandaloneScore desc** (independence proxy: `max(0, 100 − 18·log₂(facilities_in_system))`). All 5 cleared the v2 HARD GATE: a verifiable on-site violent event (not transported-to, not hoax, not cyber). All 5 sit inside a state-scope mandate that's already in force or hits inside a 12-month runway.

| # | Facility | State | std | Beds | Mandate | Incident |
|---|---|---|---|---|---|---|
| 1 | [Richmond University Medical Center](documents/qso-briefs/qso-1-richmond-university.md) | NY | **100** | 473 | NY S5294-B · eff 2026-09-18 | Mar 2024 rampage stabbing 6 workers + OSHA SIR Dec 2024 |
| 2 | [St Barnabas Hospital / SBH](documents/qso-briefs/qso-2-st-barnabas.md) | NY | **100** | 446 | NY S5294-B + Bronx >1M ED-LEO requirement | OSHA SIR Sep 2025 — psych monitor spinal fracture |
| 3 | [Blessing Hospital](documents/qso-briefs/qso-3-blessing.md) | IL | **82** | 312 | IL HB3435 (PA 104-0306) signed 2025-08-15 | OSHA SIR Sep 2024 — patient charge, head injury |
| 4 | [Mary Washington Hospital](documents/qso-briefs/qso-4-mary-washington.md) | VA | **71.5** | 451 | VA HB2269 · eff 2025-07-01 | Mar 2025 — deputy attacked at hospital (sheriff release) |
| 5 | [Harborview Medical Center](documents/qso-briefs/qso-5-harborview.md) | WA | **64** | 413 | WA RCW 49.19 · eff 2026-01-01 | Feb 2026 ED rampage + arson ($100K damage) |

### Why each one (the rationale, plain)

**#1 — Richmond University (NY).** True standalone (1 hospital, std=100). Two documented on-site violent events at the same building inside nine months — a March 2024 multi-victim stabbing rampage and an OSHA-reported December 2024 security-staff injury during a patient restraint. NY S5294-B becomes effective 2026-09-18 (Hochul signed 2025-12-12). Independent hospitals carry the full WPV-program lift without a system shared-services team. **Why this one and not a bigger NY system: because we're not selling a system, we're selling to a building, and the building has the strongest on-record incident pattern in the state.**

**#2 — St Barnabas / SBH (NY).** Also a true standalone (SBH Health System runs only the Bronx campus, std=100). OSHA SIR 2025-09-16 is the canonical Firefly use case verbatim: a 1:1 psychiatric monitor was thrown to the floor by the patient and hospitalized with an acute spinal compression fracture. The legal disclosure itself is the evidence. Bronx population >1M triggers S5294-B's strictest provision — at least one off-duty LEO or trained security in the ED at all times. Governor Hochul announced $140M of state-funded modernization in Nov 2024, so the safety-capex window is open. **Why this one: state mandate has unique teeth at this address (population trigger), the incident is medical-record clean, and there's active budget.**

**#3 — Blessing Hospital (IL).** Regional referral hospital, 2-hospital system (std=82 — above the "true independent" std≥70 bar but with a critical-access satellite). OSHA SIR 2024-09-28 logs a patient charging at staff in a hallway, head injury. Illinois 210 ILCS 160 (Health Care Violence Prevention Act) was in force since 2019 and got real teeth on 2025-08-15 when Pritzker signed HB3435 (PA 104-0306), adding explicit alarm + security-assessment requirements plus expanded reporting. Western IL Tri-State EMS hub. **Why this one: post-amendment compliance window is hot, the incident sits inside the lookback period, and a regional independent buys without an enterprise IT integration ladder.**

**#4 — Mary Washington (VA).** Regional independent, 3-facility system (std=71.5). The HARD GATE here is extraordinary: a sworn Stafford County Deputy was attacked, unprovoked, inside the hospital on 2025-03-10 — the sheriff's office published the incident report itself. Virginia Code §32.1-127 has been enforceable since 2025-07-01, and VDH quarterly reporting comes online 2026-07-01 (incident metrics go public). CEO transition in spring 2025 (Christopher Newman from COO/CMO into the seat) creates a fresh strategy-review window for security capex. **Why this one: if a deputy isn't safe inside the building, the perimeter is asking too much of unarmed staff — that's the single cleanest single-sentence pitch in the portfolio.**

**#5 — Harborview (WA).** 4-facility system (UW Medicine), std=64 — the only QSO below the std≥70 true-independent bar, preserved as the WA anchor for a freshly documented incident. 2026-02-14: a discharged patient attacked nurses and security, broke an oxygen line, set fire to a bucket of medical supplies in a trauma room, made a noose with plastic tubing — $100K in damage, no staff injuries. WA RCW 49.19 became effective 2026-01-01 (in force). Apify LinkedIn confirmed the direct security-tech buyer is Shaun Geraghty, Manager of Public Safety / Security Technology, UW Medicine. **Why this one: the freshest documented event in the portfolio + the only Pacific-NW anchor + a confirmed-by-name security-tech buyer at the parent system.**

---

## How the engine works

```
CMS HGI ──┐
AHRQ ─────┤                                                      ┌─→ Tier B: incident HARD GATE
CMS POS ──┼──→ data/staging/ ──→ data/mart/tam.csv ──→ FORGE ──┤   (on-site violence)
NPPES ────┤                       (5,362 rows)        scored    │
Census ───┤                                          (additive  ├─→ Tier B: OSHA SIR lift
mandates ─┤                                           max 9)    │   (citation-grade Acute)
OSHA SIR ─┤                                                     │
USAspd ───┘                                                     ├─→ Tier B: incumbent vendor
                                                                │   (Indeed regex)
                                                                │
                                                                ▼
                                              5 hand-picked QSOs (Tier A)
                                              ├─→ Apify LinkedIn buying committees
                                              ├─→ hand-written brief + one-off draft
                                              └─→ dashboard/index.html
                                                  (static, single-file)
```

**Step 1 — Seed (Tier C, ~5,362 rows, free).** CMS HGI primary list → dedup on CCN → AHRQ Compendium for parent_system + facilities_in_system → CMS POS for certified beds + behavioral-unit flag → NPPES for DBA name, physical address, edm_seed → Census batch geocoder → mandate-join (all 50 + DC) with `mandate_status` ∈ {Upcoming, In force, Enforcement}. Output: `data/mart/tam.csv`. *(`skills/seed-tier-c/run.py`)*

**Step 2 — Score FORGE (additive, max 9).** `forge_total = Fit_gate × (Acute + Event + Gravity)`, each pillar 0–3. Mega-IDN cap: if `StandaloneScore == 0` (massive system), `forge_tier` is capped at B. v1 was multiplicative (max 27); v2 is additive (max 9) with a deadline curve on Event, a contact-seniority weighting on Gravity, and the Standalone cap. *(`skills/forge-score/run.py`)*

**Step 3 — Tier-B enrichment (free / low-metered).** `tier-b-osha` matches OSHA SIR federal NAICS-622 records to facilities and lifts Acute Need to citation-grade. `tier-b-incident` runs the HARD GATE on-site-violence classifier with AT-vs-transported / hoax / drill / cyber exclusions and a 2022 recency floor. `tier-b-incumbent` extracts incumbent vendor mentions from Indeed job posts with replace-vs-integrate layer classification. `tier-b-contracts` pulls federal contract awards from USAspending. All at-scale, free, no key.

**Step 4 — Tier-A 5 QSOs (paid Apify, stop-and-confirm).** Hand-pick 5 from the FORGE-A pool that pass the incident HARD GATE + sit inside a state-scope mandate + clear the footprint floor (beds ≥ 150), ranked primarily by StandaloneScore desc. `qso-linkedin` uses Apify's `harvestapi~linkedin-company-employees` actor (~$0.80 per 100 employees) to surface real role-mapped buying committees: champion (security/safety/EM), EDM (C-suite + system VP Support Services), cosponsor (CNO), influencer (facilities/IT/risk/CMO).

**Step 5 — Dashboard.** Single-file static HTML (no framework) reading `dashboard/data.json` (PII-redacted JSON-ified mart). D3.js + topojson-client from CDN. Overview / Map / Campaigns / Accounts / Code views. Drawer per row with all signals + evidence URLs.

---

## v2 changes since v1 (what shipped this session)

| Area | v1 | v2 |
|---|---|---|
| Universe | 15 priority mandate states, ~2,353 facilities | All 50 states + DC, ~5,362 facilities |
| FORGE formula | Multiplicative: Fit × Acute × Event × Gravity (max 27) | Additive: Fit × (Acute + Event + Gravity) (max 9) + Standalone cap |
| Tier convention | A = broad/cheap, C = QSO/deep | A = QSO/deep, C = broad/cheap (flipped to match grading intuition) |
| Acute Need source | AHRQ safety-net proxies | OSHA SIR (citation-grade) + HARD-GATE news classifier |
| 5 QSO selection method | FORGE-27 pool, hand-picked for diversity | HARD-GATE + state mandate + std-first ranking |
| Buying committee | NPPES auth_official (proxy, no email) | Apify LinkedIn role-mapped + named champion per QSO |
| 5 QSOs themselves | Harborview, Clara Maass, NYP, CHRISTUS Spohn, OLOL | Richmond U, St Barnabas, Blessing, Mary Washington, Harborview |
| Why the swap | n/a | Clara/CHRISTUS failed HARD GATE; NYP/OLOL drifted to mid-IDN per "no mega-IDN" rule. Old set is archived to `qso-briefs/bench/` for sunk-cost reference. |

---

## What's deliberately NOT in scope

| Step | Status | Why |
|---|---|---|
| tier-b-contracts v2 (SAM.gov opportunities + recompete radar) | Parked | SAM.gov public API has ~10/day quota — unusable for scale. Code exists, waiting on a viable API. |
| tier-b-incumbent v2 (vendor case studies + board minutes via RAG Web Browser) | Pending | Apify RAG Web Browser actor identified; next iteration. |
| Step 6 (weekly refresh loop) | Not started | Operational, not portfolio-critical. |
| IRS 990 narrative grep → real WPV-program signal | Deferred | ProPublica exposes financial summary only; full path requires IRS S3 e-file XML + parser. |
| News-incident at scale | Deferred | Free-tier API limits don't cover 5,362. v2 added OSHA SIR + targeted news HARD GATE — covers the QSO selection problem. |

**This is the honest scope.** Every deferred item is documented in its skill's `SKILL.md` with a specific reason and a future-session restart point.

---

## Repository map

```
firefly-gtm/
├── CLAUDE.md                       # locked scope + framework (read first)
├── RUNBOOK.md                      # the 6 ordered steps
├── README.md                       # this file
├── HANDOFF.md                      # latest session handoff
│
├── context/                        # ICP, positioning, signal library, personas
├── data/
│   ├── reference/                  # hand-curated CSVs — mandate database (all 50 + DC), coverage grid, competitors, signal-sources
│   ├── raw/                        # source data (gitignored — large + regenerable)
│   ├── staging/                    # pipeline intermediates (gitignored)
│   └── mart/
│       ├── tam.csv                 # full mart with contact info (gitignored, PII)
│       ├── tam_scored.csv          # full scored mart with PII (gitignored)
│       └── tam_scored_sample.csv   # 170-row redacted committable sample
│
├── skills/
│   ├── seed-tier-c/                # broad seed pipeline — 8 steps, all 50 + DC
│   ├── forge-score/                # FORGE additive max 9 + Standalone cap
│   ├── standalone-score/           # std = max(0, 100 − 18·log₂(N))
│   ├── tier-b-osha/                # OSHA SIR → citation-grade Acute Need
│   ├── tier-b-incident/            # HARD GATE on-site violence classifier
│   ├── tier-b-incumbent/           # Indeed regex incumbent vendor detection
│   ├── tier-b-contracts/           # USAspending federal contract awards
│   ├── qso-linkedin/               # Apify LinkedIn buying-committee scraper (Tier A only)
│   ├── account-researcher/         # LLM agent — per-account research brief
│   ├── one-off-writer/             # LLM agent — one-off email draft
│   └── compliance/                 # state-by-state mandate brief generator
│
├── documents/
│   ├── qso_briefs.md               # the 5-QSO portfolio index (v2)
│   ├── qso_briefs_v1.md            # preserved v1 portfolio for history
│   └── qso-briefs/
│       ├── qso-{1..5}-*.md         # hand-written briefs (gold standard)
│       ├── bench/                  # benched v1 QSOs (NYP, OLOL, Clara Maass, CHRISTUS)
│       └── auto/                   # auto-generated artifacts + _archive/ for stale
│
├── dashboard/
│   ├── index.html                  # single-file static dashboard
│   ├── build-data.py               # tam_scored.csv → data.json (PII-redacted)
│   └── data.json                   # the PII-redacted artifact (regenerable)
│
└── diagrams/                       # source-map.svg + regenerator
```

---

## How to reproduce locally

```bash
# 1. Seed the TAM (~25 min wall-clock; mostly NPPES network)
python3 skills/seed-tier-c/run.py --all

# 2. Apply FORGE scoring (~30 sec)
python3 skills/forge-score/run.py --all

# 3. Tier-B enrichment (OSHA SIR + HARD-GATE incident + incumbent + contracts)
python3 skills/tier-b-osha/run.py --all
python3 skills/tier-b-incident/run.py --all
python3 skills/tier-b-incumbent/run.py --all
python3 skills/tier-b-contracts/run.py --all

# 4. Rebuild the dashboard data artifact
python3 dashboard/build-data.py

# 5. Serve the dashboard
cd dashboard && python3 -m http.server 4173
# → http://127.0.0.1:4173
```

**Requires**: Python 3.9+ with `httpx`. No npm, no React build, no framework dependencies. Standard library does the work.

---

## Hard rules the engine respects

From `CLAUDE.md`, non-negotiable:

1. **Never fabricate.** Unknown fields are `null` + `needs_review=TRUE`. Acute Need proxies are explicitly labeled as proxies.
2. **Public data only. No PHI.** NPPES auth_official is the strongest contact signal we use; phone numbers stripped from public artifacts.
3. **One-offs, not sequences.** Five emails to five humans about five specific events. No drip cadence, no `{{first_name}}`, no automation.
4. **Apify / paid contact tools reserved for Tier-A** (the 5 QSOs) under explicit stop-and-confirm.
5. **Source URLs everywhere.** Every signal in every QSO brief carries a public evidence URL.
6. **Trusted-standard moat reinforced, never undercut.** Firefly's positioning is regulatory / mandate-driven. Outputs reflect that.

---

## Cost summary (cumulative ≈ $5)

| Source | Spent | Notes |
|---|---|---|
| All public-data pulls (CMS / AHRQ / NPPES / Census / OSHA SIR / USAspending / mandates) | $0 | free, no key |
| Anthropic Haiku 4.5 (5 briefs + 5 one-offs + agents) | ~$0.10 | |
| Apify LinkedIn (5 QSOs × ~$0.80) | ~$4.00 | `harvestapi~linkedin-company-employees`, "Full $8/1k" mode |
| Vercel hosting | $0 | Hobby tier static |

---

## Author

**Ryan Michaels**

Built in collaboration with Claude Code (Opus 4.7) as the implementation partner — judgment, scope, and architectural calls are mine; the engine code was paired.

— 2026-06-24
