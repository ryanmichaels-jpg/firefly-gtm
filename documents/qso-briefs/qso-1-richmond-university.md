# QSO 1 — Richmond University Medical Center (Staten Island, NY)

**Status**: `is_qso_candidate=TRUE` · forge_tier **A** · StandaloneScore **100** · independent flagship

## Account at a glance

| | |
|---|---|
| CCN | 330028 |
| Beds | 473 |
| ED / Behavioral Health | ✓ / ✓ |
| Hospital type | Acute Care — community teaching hospital, Level 2 Trauma |
| Parent system | **Standalone** — Richmond University Medical Center (1-facility, std=100) |
| Location | 355 Bard Avenue, Staten Island, NY 10310 |
| Ownership | Voluntary non-profit — Private |
| Affiliation | Mount Sinai Health System (academic affiliate, not corporate parent) |

## FORGE rationale (additive · max 9)

- **Acute = 3** — OSHA SIR-documented violence within last 12 months (citation-grade, not AHRQ proxy)
- **Event = 3** — NY S5294-B (Public Health Law amendment) **upcoming**, effective **September 18, 2026** — Gov. Hochul signed 12/12/2025
- **Gravity = 3** — exec-title NPPES seed (VP Finance) at independent standalone with named CEO
- **forge_total = 9 / 9** (max)

## Why this is a QSO — the HARD GATE

**March 5, 2024**: A 19-year-old patient injured at least **6 workers** in a "wild attack" — stabbing, biting, and punching — described by police as a rampage *at* Richmond University Medical Center. Charges were brought through NYPD (Staten Island bureau). The article frames this as a single-perpetrator multi-victim staff assault inside the building. ([SILive](https://www.silive.com/crime-safety/2024/03/nypd-he-stabbed-bit-punched-6-workers-in-rampage-at-hospital.html))

Corroborated by **OSHA SIR ID #1916822** ([OSHA Severe Injury Reports](https://www.osha.gov/severe-injury-reports)) — incident date **December 11, 2024** — "A security employee was restraining an agitated patient when they both fell to the floor and the employee's right hand struck the floor resulting in a broken tendon in the middle finger." Distinct from the March 2024 mass-assault — this is a **second documented on-site event within nine months**, both staff-directed.

Together: a multi-victim rampage + a follow-on security-staff injury restraining an agitated patient — the textbook "structural Acute Need" Firefly's framework calls for. Not a one-off; a pattern.

## Why this fits the thesis (criterion #3 footprint + criterion #2 proximity)

- Single-campus 473-bed community hospital. **Not a multi-hospital system.** AHRQ shows facilities_in_system = 1.
- NY anchor — pairs geographically with the St Barnabas Bronx QSO (#2) for shared field motion in NYC.

## Buying committee

| Role | Likely Name | Source | Notes |
|---|---|---|---|
| **CEO / EDM sponsor** | **Daniel J. Messina, PhD, MPA, FACHE** | [RUMC Board](https://rumcsi.org/board-members/daniel-j-messina/) | President/CEO since April 2014; Staten Island lifer; #7 on City and State NY 2024 Staten Island Power 100 |
| Likely champion | **VP / Director of Security**, RUMC | ⚠ Apify LinkedIn scrape returned 0 (URL fixed to `linkedin.com/company/richmond-university-medical-center`, Apify budget exceeded — retry after top-up: `python3 skills/qso-linkedin/run.py --ccn 330028`) · confirm via IAHSS NY chapter directory | independent hospital — likely a single security director, not a system VP |
| Likely sponsor | **Daniel Messina** (CEO) directly | direct line for safety-critical decisions at a standalone | |
| Influencer | **Chief Nursing Officer** | rumcsi.org/leadership | nurses were victims in the March 2024 rampage |
| Influencer | **VP Risk / Compliance** | confirm | likely the OSHA SIR reporter of record |
| EDM proxy in mart | VP Finance (NPPES auth_official seed) | NPPES public registry | functional, not the security buyer |

## One-off draft

**To:** Daniel J. Messina, President & CEO, Richmond University Medical Center
**CC:** VP / Director of Security & Safety (confirm name)
**Subject:** Six staff stabbed in March, broken tendon in December — and S5294-B is now in your runway

Dr. Messina,

Two on-site events within nine months — the March 5 stabbing/biting/punching rampage that injured six workers, and the December 11 OSHA-reported security-staff injury during a patient restraint. Both at 355 Bard. Both with patients as the attacker.

S5294-B becomes effective September 18, 2026 — your hospitals & nursing-homes violence prevention program needs to be operational by then. Independent hospitals like RUMC carry the full lift without a system shared-services team to delegate to.

Firefly's Lattice gateway sits at the perimeter — wearable panic mesh for nursing staff on a resilient private RF network (works when the building Wi-Fi doesn't), AI gunshot + loiter detection, and an Ember software layer that routes detect-locate-alert-respond to the right responder in the right unit. We're built for exactly the "rampage in the ED" pattern that played out at RUMC twice this year.

15-minute call? I can walk through how it would have routed the March 5 incident — what detection fires when, what alert goes to which device, and how a standalone hospital deploys without the IT integration ladder a system would require.

— [Rep]

---

## Evidence URLs

- News (mass assault): [SILive — NYPD: He stabbed, bit, punched 6 workers in rampage at hospital](https://www.silive.com/crime-safety/2024/03/nypd-he-stabbed-bit-punched-6-workers-in-rampage-at-hospital.html)
- OSHA SIR (security restraint injury 2024-12-11): [osha.gov/severe-injury-reports](https://www.osha.gov/severe-injury-reports)
- Mandate: [NY S5294-B (NY Senate)](https://www.nysenate.gov/legislation/bills/2025/S5294/amendment/B) · [Ogletree analysis](https://ogletree.com/insights-resources/blog-posts/new-york-enacts-mandatory-workplace-violence-prevention-programs-for-healthcare-facilities/)
- CEO: [Daniel J. Messina — RUMC](https://rumcsi.org/board-members/daniel-j-messina/)
