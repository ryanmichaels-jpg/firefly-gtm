# QSO Portfolio — v2 (incident-gate locked, std-first ranked)

5 qualified sales opportunities selected after introducing the **HARD GATE on criterion #1** (verifiable on-site violent incident, not transported-to) and **decoupling footprint from independence** in criterion #3. Ranked by StandaloneScore desc.

| # | Hospital | State | std | Beds | Incident | Mandate (state-scope) |
|---|---|---|---|---|---|---|
| [1](qso-briefs/qso-1-richmond-university.md) | Richmond University Medical Center | NY | **100** | 473 | 2024-03-05 rampage stabbing 6 workers · OSHA SIR 2024-12-11 | NY S5294-B · eff 9/18/2026 |
| [2](qso-briefs/qso-2-st-barnabas.md) | St Barnabas Hospital (SBH Health) | NY | **100** | 446 | OSHA SIR 2025-09-16 psych nurse fractured spine | NY S5294-B · eff 9/18/2026 |
| [3](qso-briefs/qso-3-blessing.md) | Blessing Hospital | IL | **82** | 312 | OSHA SIR 2024-09-28 patient charged at staff, head injury | IL 210 ILCS 160 + HB3435 (PA 104-0306) signed 8/15/2025 |
| [4](qso-briefs/qso-4-mary-washington.md) | Mary Washington Hospital | VA | **71.5** | 451 | 2025-03-11 deputy unprovoked attack (Stafford SO release) | VA HB2269/SB1260 · eff 7/1/2025 |
| [5](qso-briefs/qso-5-harborview.md) | Harborview Medical Center | WA | **64** | 413 | 2026-02-19 ED arson + nurse assault ($100K damage) | WA RCW 49.19 · eff 1/1/2026 |

## Profile

- **4 of 5 true-independent** (std ≥ 70). Harborview at std=64 is the original brief preserved.
- **Zero mega-IDNs** — Mount Sinai, NYP, OLOL were benched as off-thesis (`bench/`).
- **5 distinct states** (NY · NY · IL · VA · WA) — 2 NY anchors enable shared NYC field motion (Bronx + Staten Island).
- **All 5 pass the incident HARD GATE** — 3 via OSHA SIR (employer self-report = on-site by definition); 2 via verified news + law-enforcement release.
- **All 5 mandates are state-scope, active or in 12-month runway**.

## Selection logic (v2)

Criterion | Implementation
---|---
**#1 incident (HARD GATE)** | News + OSHA SIR with AT-vs-transported classifier; cyber / drill / hoax / showed-up-at exclusions enforced. **OSHA SIR is the primary source going forward** — on-site by definition, no ambiguity.
**#2 proximity** | State spread WA/NY/VA/IL — pair-NY anchors for shared field motion
**#3 footprint** | Beds ≥ 150 floor only — does NOT fuse with #4 independence (earlier draft conflated; fixed)
**#4 incumbent recompete** | Blank for all 5 — no incumbent vendor case-study evidence in our 10-vendor batch
**#5 mandate** | State-scope active or upcoming; effective dates verified against legislative sources

## Benched (do NOT promote — kept for sunk-cost reference work)

`bench/` directory:
- **NYP** (mid-IDN, std=46) — 8-facility system, fits the "no mega-IDN" rule we corrected against. Real incident + buying committee + paid Apify research. Reference only.
- **OLOL** (mid-IDN, std=37.7) — 11-facility FMOL Catholic system. Patricia Jackson 2025 parking-lot homicide + named-incumbent lawsuit (Inner Parish Security Corp). Legally complicated outreach.
- **Clara Maass** (NJ) — FAILED incident gate (no verified on-site event)
- **CHRISTUS Spohn** (TX) — FAILED incident gate (Nov 2024 was a hoax; May 2022 was transported-to)

## Buying committee data — LinkedIn / Apify status

| QSO | LinkedIn URL | Apify scan | Security champion confirmed? |
|---|---|---|---|
| Richmond U | `linkedin.com/company/richmond-university-medical-center` (URL fixed mid-run) | ⚠ pending Apify top-up | not yet — CEO confirmed via web |
| St Barnabas (SBH) | `linkedin.com/company/sbhbronx` (URL fixed mid-run) | ⚠ pending Apify top-up | not yet — CEO confirmed via web |
| Blessing | `linkedin.com/company/blessing-health` | ✓ 100 employees scraped | ✓ **David Schlosser** (Security Officer) + **Andrew S.** (CISO) + **Justin McDermott** (Risk Mgr) |
| Mary Washington | `linkedin.com/company/mary-washington-healthcare` | ✓ 100 employees scraped | ✓ **Calvin Bostic, CPP, CHPA** (Director of Security, Safety & Emergency Management) — credentialed hospital security pro |
| Harborview | `linkedin.com/company/harborview-medical-center` | ✓ cached 100 employees reclassified | ⚠ no formal champion title surfaced; UW Medicine structure puts security under separate org |

**Apify budget exhausted ($0.04 remaining)** after Mary Washington + Blessing + reclassify ran. Richmond + St Barnabas LinkedIn URLs were wrong on first attempt (corrected; cached run failed before budget top-up). To resume:
```bash
python3 skills/qso-linkedin/run.py --ccn 330028   # Richmond
python3 skills/qso-linkedin/run.py --ccn 330399   # St Barnabas
```

## See also

- Previous portfolio index: [qso_briefs_v1.md](qso_briefs_v1.md)
- Old briefs (bench): [qso-briefs/bench/](qso-briefs/bench/)
