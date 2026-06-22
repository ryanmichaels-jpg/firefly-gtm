# Firefly Revenue Intel — a working GTM engine for the Healthcare WPV vertical

A live, queryable TAM of **2,353 U.S. hospitals** in the 15 priority mandate states, scored against Firefly's **F.O.R.G.E.** qualification framework, surfaced as a static dashboard, and refined down to **5 hand-picked QSOs** with research briefs and one-off email drafts.

Built end-to-end from public data sources. **$0 of marginal spend.** The kind of thing a GTM Engineer ships in week one.

---

## What you can do with this repo in 90 seconds

| | Link |
|---|---|
| **Live dashboard** (US map, Clay-style accounts list, FORGE rankings) | _deploy URL — pending push_ |
| **5 named QSOs** with full briefs + one-off email drafts | [documents/qso_briefs.md](documents/qso_briefs.md) |
| **The pipeline source-map** (regenerable SVG) | [diagrams/source-map.svg](diagrams/source-map.svg) |
| **What got scored on what** (methodology, dimension by dimension) | [skills/forge-score/SKILL.md](skills/forge-score/SKILL.md) |
| **Why we don't seed from NPPES** (and what we do instead) | [skills/seed-tier-a/SKILL.md](skills/seed-tier-a/SKILL.md) |
| **The hard scope rules (no email sequences, no fabrication, no PHI)** | [CLAUDE.md](CLAUDE.md) |

---

## The five QSOs

| # | Facility | State | Beds | System | Mandate | Play |
|---|---|---|---|---|---|---|
| 1 | [Harborview Medical Center](documents/qso-briefs/qso-1-harborview.md) | WA | 413 | UW Medicine | RCW 49.19 — **In force** | Feb 14, 2026 ED rampage ($100K damage) + enforcement clock |
| 2 | [Clara Maass Medical Center](documents/qso-briefs/qso-2-clara-maass.md) | NJ | 472 | RWJBarnabas Health | N.J.S.A. 26:2H-5.17 — **In force** | RWJB's published 5-step framework + 1199SEIU contract pressure |
| 3 | [NewYork-Presbyterian Hospital](documents/qso-briefs/qso-3-nyp.md) | NY | 2,262 | NYP Healthcare | Ch.618/2025 — **Upcoming 2027-01-01** | TVTP-grant peer-leader, scale to 10+ campuses before deadline |
| 4 | [CHRISTUS Spohn — Corpus Christi](documents/qso-briefs/qso-4-christus-spohn.md) | TX | 1,040 | CHRISTUS Health | SB240 — **In force** | Nov 13, 2024 dementia-hoax — 50 officers, false-alarm operational cost |
| 5 | [Our Lady of the Lake](documents/qso-briefs/qso-5-our-lady-of-the-lake.md) | LA | 976 | FMOL Health | **Lynne Truxillo Act** — **In force** | Two homicides + active lawsuit naming incumbent vendor |

Each brief has: account snapshot · FORGE rationale · buying committee · evidence URLs · 80–125 word one-off draft · *why this opening*.

> **Important constraint**: QSO 5 has active wrongful-death litigation. The brief is internal-only until Legal + CRO clear external outreach. See the brief for the full constraint section.

---

## How the engine works

```
CMS HGI ──┐
AHRQ ─────┤
CMS POS ──┼──→  data/staging/  ──→  data/mart/tam.csv  ──→  FORGE scoring  ──→  5 QSOs
NPPES ────┤                          (2,353 rows)              (622 Tier-A)         (briefs + drafts)
Census ───┤                                                          │
mandates ─┘                                                          ▼
                                                              dashboard/index.html
                                                              (static, single-file)
```

**Step 1 — Seed.** Filter CMS Hospital General Information to 15 priority states. Dedup. Left-join AHRQ Compendium (parent_system, facilities_in_system). Left-join CMS POS Q1 2026 (certified beds, has_behavioral_unit). Enrich via NPPES (DBA name, physical address, edm_seed from auth_official — with hospital-aware DBA preference so we don't end up with "...PHARMACY" or "...TRANSPORT" as the facility name). Batch-geocode via Census. Join state WPV mandates with status logic (In force / Upcoming / Enforcement). Tier by beds + hospital type. Output: `data/mart/tam.csv`.

**Step 2 — Score.** F.O.R.G.E. = Fit (gate) → **Acute Need × Event × Gravity**, each 0-3, product 0-27. Per CLAUDE.md: never pre-call score Resolve or Clarity. Acute Need uses **research-backed AHRQ safety-net proxies** (high-DSH, high-UC, major-teaching) clearly labeled in the `acute_need_evidence` column — not direct OSHA citations or 990 narrative, which are deferred Tier-B work documented in the SKILL.md. **No fabricated values anywhere.** Distribution: A=622, B=426, C=94, X=1211.

**Step 4 — QSOs.** Hand-picked 5 from FORGE-A across state / system / mandate-status diversity, with C-suite NPPES EDM contacts, with public-evidence signal stacks researched via free sources only (news, AHA case studies, DHS grantee reports, lawsuit filings).

**Step 5 — Dashboard.** Single-file static HTML (no framework) reading `dashboard/data.json` (the PII-redacted JSON-ified mart). D3.js + topojson-client from CDN. Overview, Map, Campaigns, Accounts. Detail drawer per row.

---

## What's deliberately NOT in scope

| Step | Status | Why |
|---|---|---|
| Step 3 (Tier-B at-scale enrichment) | Deferred | Incumbent-vendor signal at scale hit anti-scraping walls (Cloudflare gates, customer logos as images, federal-only USA Spending coverage). Realistic only via manual list-building or paid Apify (~$50-100). |
| Step 6 (Weekly refresh loop) | Not started | Operational, not portfolio-critical |
| OSHA Severe Injury Reports → real Acute Need | Deferred | Direct CSV URL not publishable from OSHA's docs page; would require dashboard navigation or DOL data-catalog hunt |
| IRS 990 narrative grep → real WPV-program signal | Deferred | ProPublica API exposes financial summary only; current 990 PDFs unavailable through API; would require AWS S3 e-file XML fetch + parser (~3-4 hours infra) |
| News-incident enrichment at scale | Deferred | Free-tier API limits don't cover 2,353 facilities. Realistic only at Tier-B (curated ~300). |
| Apify / Apollo / LinkedIn Sales Nav | Not used | Per CLAUDE.md: paid contact tools reserved for Tier-C 5-QSO scope under explicit gate. Not invoked this build. |
| Chat mode / Code mode in dashboard | Decorative | The Claude Design mockup included them; we shipped stub panes acknowledging the scope cut |

**This is the honest scope.** Every deferred item is documented in its skill's `SKILL.md` with a specific reason and a future-session restart point.

---

## Repository map

```
firefly-gtm/
├── CLAUDE.md                       # locked scope + framework (read first)
├── RUNBOOK.md                      # the 6 ordered steps
├── README.md                       # this file
│
├── context/                        # ICP, positioning, signal library, personas
├── data/
│   ├── reference/                  # hand-curated CSVs — 87-row mandate database, coverage grid, competitors
│   ├── raw/                        # source data (gitignored — large + regenerable)
│   ├── staging/                    # pipeline intermediates (gitignored)
│   └── mart/
│       ├── tam.csv                 # full mart with contact info (gitignored, PII)
│       ├── tam_scored.csv          # full scored mart with PII (gitignored)
│       └── tam_scored_sample.csv   # 170-row redacted committable sample
│
├── skills/
│   ├── seed-tier-a/                # 8-step CMS-first pipeline (Python stdlib + httpx)
│   ├── forge-score/                # FORGE rubrics + scoring (Python stdlib)
│   └── …                           # account-research, weekly-update, etc. (from starter kit)
│
├── documents/
│   ├── qso_briefs.md               # the 5-QSO index
│   └── qso-briefs/qso-N-*.md       # per-account briefs + one-offs
│
├── dashboard/
│   ├── index.html                  # single-file static dashboard (~30KB JS + inline CSS)
│   ├── build-data.py               # tam_scored.csv → data.json (PII-redacted)
│   └── data.json                   # the PII-redacted artifact (2.7MB, regenerable)
│
├── diagrams/
│   ├── source-map.svg              # pipeline diagram, hand-drawn aesthetic
│   ├── generate_source_map.py      # regenerator
│   └── source-map.tldraw.js        # tldraw exec-ready version (for when MCP works)
│
└── reference-artifacts/            # Firefly framework HTMLs, tracker, interview brief
```

---

## How to reproduce locally

```bash
# 1. Seed the TAM (~25 min wall-clock; mostly NPPES network)
python3 skills/seed-tier-a/run.py --all

# 2. Apply FORGE scoring (~30 sec)
python3 skills/forge-score/run.py --all

# 3. Rebuild the dashboard data artifact
python3 dashboard/build-data.py

# 4. Serve the dashboard
cd dashboard && python3 -m http.server 4173
# → http://127.0.0.1:4173
```

**Requires**: Python 3.9+ with `httpx`. No npm, no React build, no framework dependencies. Standard library does the work.

---

## Hard rules the engine respects

From `CLAUDE.md`, non-negotiable:

1. **Never fabricate.** Unknown fields are `null` + `needs_review=TRUE`. Acute Need proxies are explicitly labeled as proxies in the `acute_need_evidence` column.
2. **Public data only. No PHI.** NPPES auth_official is the strongest contact signal we use; phone numbers stripped from public artifacts.
3. **One-offs, not sequences.** Five emails to five humans about five specific events. No drip cadence, no `{{first_name}}`, no automation.
4. **Apify / paid contact tools reserved for Tier-C** (the 5 QSOs) — and only under explicit stop-and-confirm. Not invoked this build.
5. **Source URLs everywhere.** Every signal in every QSO brief carries a public evidence URL. Every derived field in the mart carries a `*_source_url`.
6. **Trusted-standard moat reinforced, never undercut.** Firefly's positioning is regulatory / mandate-driven. Outputs reflect that.

---

## Build history

```
b59edde  feat(dashboard):    single-file Firefly Revenue Intel dashboard
b40e3ac  feat(qsos):         ship 5 hand-picked QSOs with per-account briefs + one-offs
5bc9251  feat(forge-score):  rank TAM via F.O.R.G.E. framework (622 Tier-A)
68f9a5d  feat(seed-tier-a):  build 15-state TAM seed pipeline (2,353 hospitals)
6b810cb  feat(firefly):      customize starter kit for Firefly GTM engine
```

Each commit message tells the story of what shipped + what got deferred and why.

---

## Author

**Ryan Michaels** · Sales Engineering · ex-SDR/AE pivoting to GTM Engineering

Built in collaboration with Claude Code (Opus 4.7) as the implementation partner — judgment, scope, and architectural calls are mine; the engine code was paired.

— 2026-06-22
